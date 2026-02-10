"""
Sistema de Banimento Avançado
Comando para banir usuários com confirmação e logs automáticos
"""

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="🔨 Banir um usuário do servidor")
    @app_commands.describe(
        usuario="Usuário para banir",
        motivo="Motivo do banimento",
        deletar_mensagens="Quantos dias de mensagens deletar (0-7 dias)",
    )
    async def ban_user(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        motivo: str,
        deletar_mensagens: int | None = 0,
    ):
        try:
            # 🛡️ VERIFICAÇÃO DE PERMISSÕES
            if not interaction.user.guild_permissions.ban_members:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para banir membros. **Necessário**: Banir Membros",
                    ephemeral=True,
                )
                return

            # 🛡️ VERIFICAÇÕES DE SEGURANÇA
            if usuario.id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ Você não pode banir a si mesmo! 🤔", ephemeral=True
                )
                return

            if usuario.id == self.bot.user.id:
                await interaction.response.send_message(
                    "❌ Não posso banir a mim mesmo! Isso seria suicídio digital 🤖💀",
                    ephemeral=True,
                )
                return

            if usuario.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Não posso banir um administrador do servidor!", ephemeral=True
                )
                return

            # 🛡️ VERIFICAR HIERARQUIA DE CARGOS
            if usuario.top_role >= interaction.user.top_role:
                await interaction.response.send_message(
                    "❌ Você não pode banir alguém com cargo igual ou superior ao seu!",
                    ephemeral=True,
                )
                return

            if usuario.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "❌ Não posso banir alguém com cargo igual ou superior ao meu!", ephemeral=True
                )
                return

            # 🛡️ VALIDAR DIAS DE MENSAGENS
            if deletar_mensagens < 0 or deletar_mensagens > 7:
                deletar_mensagens = 0

            # 📝 CRIAR VIEW DE CONFIRMAÇÃO
            view = BanConfirmView(usuario, motivo, deletar_mensagens, interaction.user)

            # 🎨 EMBED DE CONFIRMAÇÃO
            embed = discord.Embed(
                title="⚠️ Confirmação de Banimento",
                description=f"Tem certeza que deseja banir **{usuario.display_name}**?",
                color=0xFF0000,
                timestamp=datetime.now(),
            )

            embed.add_field(
                name="👤 Usuário",
                value=f"{usuario.mention}\n`{usuario}` (ID: {usuario.id})",
                inline=True,
            )

            embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user}`",
                inline=True,
            )

            embed.add_field(name="📝 Motivo", value=f"```{motivo}```", inline=False)

            embed.add_field(
                name="🗑️ Deletar Mensagens",
                value=f"{deletar_mensagens} dias" if deletar_mensagens > 0 else "Não deletar",
                inline=True,
            )

            embed.add_field(name="⚡ Status", value="⏳ **Aguardando Confirmação**", inline=True)

            embed.set_thumbnail(url=usuario.display_avatar.url)
            embed.set_footer(text="⚠️ Esta ação não pode ser desfeita facilmente!")

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para banir este usuário!", ephemeral=True
            )
        except Exception as e:
            print(f"❌ Erro no comando ban: {e}")
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao tentar banir o usuário. Tente novamente.", ephemeral=True
            )


class BanConfirmView(discord.ui.View):
    def __init__(
        self, user: discord.Member, reason: str, delete_days: int, moderator: discord.Member
    ):
        super().__init__(timeout=60.0)
        self.user = user
        self.reason = reason
        self.delete_days = delete_days
        self.moderator = moderator

    @discord.ui.button(label="🔨 Confirmar Ban", style=discord.ButtonStyle.danger)
    async def confirm_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.moderator.id:
            await interaction.response.send_message(
                "❌ Apenas o moderador que iniciou pode confirmar!", ephemeral=True
            )
            return

        try:
            # 🔨 EXECUTAR BANIMENTO
            await self.user.ban(
                reason=f"Banido por {self.moderator} - {self.reason}",
                delete_message_days=self.delete_days,
            )

            # 📊 REGISTRAR NO BANCO (se disponível)
            try:
                from ...utils.database import database

                await database.add_moderation_case(
                    str(interaction.guild.id),
                    str(self.user.id),
                    str(self.moderator.id),
                    "BAN",
                    self.reason,
                )
            except:
                pass  # Banco pode não estar disponível

            # ✅ EMBED DE SUCESSO
            success_embed = discord.Embed(
                title="✅ Usuário Banido com Sucesso",
                description=f"**{self.user.display_name}** foi banido do servidor!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="👤 Usuário Banido", value=f"{self.user.mention} (`{self.user}`)", inline=True
            )

            success_embed.add_field(
                name="👮 Banido por", value=f"{self.moderator.mention}", inline=True
            )

            success_embed.add_field(name="📝 Motivo", value=f"```{self.reason}```", inline=False)

            if self.delete_days > 0:
                success_embed.add_field(
                    name="🗑️ Mensagens Deletadas",
                    value=f"Últimos {self.delete_days} dias",
                    inline=True,
                )

            success_embed.set_thumbnail(url=self.user.display_avatar.url)
            success_embed.set_footer(text=f"Ban ID: {interaction.id}")

            # Desabilitar botões
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=success_embed, view=self)

            # 📢 LOG NO CANAL DE MODERAÇÃO
            await self._log_ban_action(interaction)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para banir este usuário!", ephemeral=True
            )
        except Exception as e:
            print(f"❌ Erro ao executar banimento: {e}")
            await interaction.response.send_message(
                "❌ Erro ao executar o banimento. Tente novamente.", ephemeral=True
            )

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.moderator.id:
            await interaction.response.send_message(
                "❌ Apenas o moderador que iniciou pode cancelar!", ephemeral=True
            )
            return

        # 🚫 EMBED DE CANCELAMENTO
        cancel_embed = discord.Embed(
            title="❌ Banimento Cancelado",
            description=f"O banimento de **{self.user.display_name}** foi cancelado.",
            color=0x808080,
            timestamp=datetime.now(),
        )

        cancel_embed.set_footer(text="Operação cancelada pelo moderador")

        # Desabilitar botões
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=cancel_embed, view=self)

    async def on_timeout(self):
        """Timeout da confirmação"""
        for item in self.children:
            item.disabled = True

    async def _log_ban_action(self, interaction):
        """Log da ação no canal de moderação"""
        try:
            # Procurar canal de logs
            log_channel = None
            for channel in interaction.guild.text_channels:
                if channel.name.lower() in ["mod-logs", "logs", "moderation", "moderacao"]:
                    log_channel = channel
                    break

            if (
                not log_channel
                or not log_channel.permissions_for(interaction.guild.me).send_messages
            ):
                return

            # Embed de log
            log_embed = discord.Embed(
                title="🔨 Usuário Banido", color=0xFF0000, timestamp=datetime.now()
            )

            log_embed.add_field(
                name="👤 Usuário",
                value=f"{self.user.mention}\n`{self.user}`\nID: `{self.user.id}`",
                inline=True,
            )

            log_embed.add_field(
                name="👮 Moderador",
                value=f"{self.moderator.mention}\n`{self.moderator}`",
                inline=True,
            )

            log_embed.add_field(name="📝 Motivo", value=f"```{self.reason}```", inline=False)

            if self.delete_days > 0:
                log_embed.add_field(
                    name="🗑️ Mensagens", value=f"Deletadas: {self.delete_days} dias", inline=True
                )

            log_embed.add_field(name="🏛️ Servidor", value=interaction.guild.name, inline=True)

            log_embed.add_field(
                name="🕐 Data/Hora", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True
            )

            log_embed.set_thumbnail(url=self.user.display_avatar.url)
            log_embed.set_footer(text=f"Ban ID: {interaction.id}")

            await log_channel.send(embed=log_embed)

        except Exception as e:
            print(f"❌ Erro ao registrar log do ban: {e}")


async def setup(bot):
    await bot.add_cog(Ban(bot))
