"""
Ticket Config Handler - Gerencia configurações de tickets
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class TicketConfigHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Limpar configurações quando canal é deletado"""
        try:
            await self.cleanup_deleted_channel_configs(channel.guild.id, channel.id)
        except Exception as e:
            print(f"❌ Erro limpando configs de canal deletado: {e}")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Atualizar configurações quando role é deletado"""
        try:
            await self.cleanup_deleted_role_configs(role.guild.id, role.id)
        except Exception as e:
            print(f"❌ Erro limpando configs de role deletado: {e}")

    async def cleanup_deleted_channel_configs(self, guild_id: int, channel_id: int):
        """Limpar configurações de canal deletado"""
        try:
            # Atualizar configurações de ticket que referenciam o canal
            await database.run(
                "UPDATE ticket_config SET ticket_channel_id = NULL WHERE guild_id = ? AND ticket_channel_id = ?",
                (str(guild_id), str(channel_id)),
            )

            await database.run(
                "UPDATE ticket_config SET log_channel_id = NULL WHERE guild_id = ? AND log_channel_id = ?",
                (str(guild_id), str(channel_id)),
            )

            await database.run(
                "UPDATE ticket_config SET transcript_channel_id = NULL WHERE guild_id = ? AND transcript_channel_id = ?",
                (str(guild_id), str(channel_id)),
            )

            # Remover categorias de ticket que foram deletadas
            await database.run(
                "UPDATE ticket_categories SET category_id = NULL WHERE guild_id = ? AND category_id = ?",
                (str(guild_id), str(channel_id)),
            )

        except Exception as e:
            print(f"❌ Erro limpando configs de canal: {e}")

    async def cleanup_deleted_role_configs(self, guild_id: int, role_id: int):
        """Limpar configurações de role deletado"""
        try:
            # Atualizar configurações de ticket que referenciam o role
            await database.run(
                "UPDATE ticket_config SET staff_role_id = NULL WHERE guild_id = ? AND staff_role_id = ?",
                (str(guild_id), str(role_id)),
            )

            await database.run(
                "UPDATE ticket_config SET support_role_id = NULL WHERE guild_id = ? AND support_role_id = ?",
                (str(guild_id), str(role_id)),
            )

            # Remover roles de acesso a tickets
            await database.run(
                "DELETE FROM ticket_role_access WHERE guild_id = ? AND role_id = ?",
                (str(guild_id), str(role_id)),
            )

        except Exception as e:
            print(f"❌ Erro limpando configs de role: {e}")

    async def validate_ticket_config(self, guild_id: int) -> dict:
        """Validar configuração de tickets"""
        try:
            # Buscar configuração atual
            config = await database.fetchone(
                "SELECT * FROM ticket_config WHERE guild_id = ?", (str(guild_id),)
            )

            if not config:
                return {"valid": False, "errors": ["Configuração não encontrada"]}

            guild = self.bot.get_guild(guild_id)
            if not guild:
                return {"valid": False, "errors": ["Servidor não encontrado"]}

            errors = []

            # Verificar canais
            if config.get("ticket_channel_id"):
                channel = guild.get_channel(int(config["ticket_channel_id"]))
                if not channel:
                    errors.append("Canal de tickets não existe mais")

            if config.get("log_channel_id"):
                channel = guild.get_channel(int(config["log_channel_id"]))
                if not channel:
                    errors.append("Canal de logs não existe mais")

            if config.get("transcript_channel_id"):
                channel = guild.get_channel(int(config["transcript_channel_id"]))
                if not channel:
                    errors.append("Canal de transcripts não existe mais")

            # Verificar roles
            if config.get("staff_role_id"):
                role = guild.get_role(int(config["staff_role_id"]))
                if not role:
                    errors.append("Role de staff não existe mais")

            if config.get("support_role_id"):
                role = guild.get_role(int(config["support_role_id"]))
                if not role:
                    errors.append("Role de suporte não existe mais")

            # Verificar categorias
            categories = await database.fetchall(
                "SELECT * FROM ticket_categories WHERE guild_id = ?", (str(guild_id),)
            )

            for category in categories:
                if category.get("category_id"):
                    cat = guild.get_channel(int(category["category_id"]))
                    if not cat or not isinstance(cat, discord.CategoryChannel):
                        errors.append(f'Categoria "{category["name"]}" não existe mais')

            return {"valid": len(errors) == 0, "errors": errors, "config": dict(config)}

        except Exception as e:
            print(f"❌ Erro validando config de tickets: {e}")
            return {"valid": False, "errors": [f"Erro interno: {e!s}"]}

    async def auto_fix_ticket_config(self, guild_id: int) -> bool:
        """Corrigir automaticamente problemas de configuração"""
        try:
            validation = await self.validate_ticket_config(guild_id)

            if validation["valid"]:
                return True  # Nada para corrigir

            # Limpar referências inválidas
            await database.run(
                """UPDATE ticket_config SET 
                   ticket_channel_id = NULL, 
                   log_channel_id = NULL, 
                   transcript_channel_id = NULL,
                   staff_role_id = NULL,
                   support_role_id = NULL
                   WHERE guild_id = ?""",
                (str(guild_id),),
            )

            # Limpar categorias inválidas
            await database.run(
                "DELETE FROM ticket_categories WHERE guild_id = ? AND category_id NOT IN (SELECT id FROM channels WHERE guild_id = ?)",
                (str(guild_id), str(guild_id)),
            )

            return True

        except Exception as e:
            print(f"❌ Erro corrigindo config de tickets: {e}")
            return False

    async def reset_ticket_config(self, guild_id: int) -> bool:
        """Resetar configuração de tickets para padrão"""
        try:
            # Remover configuração existente
            await database.run("DELETE FROM ticket_config WHERE guild_id = ?", (str(guild_id),))

            # Remover categorias
            await database.run("DELETE FROM ticket_categories WHERE guild_id = ?", (str(guild_id),))

            # Remover acessos de roles
            await database.run(
                "DELETE FROM ticket_role_access WHERE guild_id = ?", (str(guild_id),)
            )

            # Criar configuração padrão
            await database.run(
                """INSERT INTO ticket_config 
                   (guild_id, enabled, max_tickets_per_user, auto_close_time, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (str(guild_id), 1, 3, 24, discord.utils.utcnow().isoformat()),
            )

            return True

        except Exception as e:
            print(f"❌ Erro resetando config de tickets: {e}")
            return False


async def setup(bot):
    await bot.add_cog(TicketConfigHandler(bot))
