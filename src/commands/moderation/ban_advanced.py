"""
Sistema de Banimento - Banimento Avançado e Softban
Sistema completo de banimento com múltiplas opções e logs
"""

from datetime import datetime
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands


class BanReasonModal(discord.ui.Modal):
    """Modal para especificar motivo do banimento"""

    def __init__(self, target: discord.Member, ban_type: str, days: int = 0):
        super().__init__(title=f"🔨 {ban_type} - {target.display_name}", timeout=300)
        self.target = target
        self.ban_type = ban_type
        self.days = days

        # Campo para motivo
        self.reason_field = discord.ui.TextInput(
            label="Motivo do Banimento",
            placeholder="Descreva o motivo do banimento...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500,
        )

        # Campo para mensagens DM
        self.dm_message = discord.ui.TextInput(
            label="Mensagem para o Usuário (Opcional)",
            placeholder="Mensagem adicional que será enviada ao usuário...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
        )

        self.add_item(self.reason_field)
        self.add_item(self.dm_message)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            reason = self.reason_field.value
            dm_message = self.dm_message.value

            # Tentar enviar DM antes do banimento
            dm_sent = False
            if dm_message or reason:
                try:
                    dm_embed = discord.Embed(
                        title=f"🔨 **VOCÊ FOI {'BANIDO' if self.ban_type != 'Softban' else 'EXPULSO (SOFTBAN)'}**",
                        description=f"Servidor: **{interaction.guild.name}**",
                        color=0x8B0000 if self.ban_type != "Softban" else 0xFF4500,
                        timestamp=datetime.now(),
                    )

                    dm_embed.add_field(name="📋 Motivo", value=reason, inline=False)

                    if dm_message:
                        dm_embed.add_field(
                            name="💬 Mensagem do Moderador", value=dm_message, inline=False
                        )

                    dm_embed.add_field(
                        name="👮 Moderador", value=interaction.user.mention, inline=True
                    )

                    if self.ban_type == "Softban":
                        dm_embed.add_field(
                            name="ℹ️ Softban",
                            value="Suas mensagens foram removidas, mas você pode voltar ao servidor.",
                            inline=False,
                        )
                    else:
                        dm_embed.add_field(
                            name="⏰ Duração",
                            value="Permanente" if self.days == 0 else f"{self.days} dias",
                            inline=True,
                        )

                    dm_embed.set_footer(
                        text=f"Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
                        icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
                    )

                    await self.target.send(embed=dm_embed)
                    dm_sent = True

                except:
                    dm_sent = False

            # Executar banimento
            if self.ban_type == "Softban":
                # Softban: banir e imediatamente desbanir
                await self.target.ban(reason=f"[SOFTBAN] {reason}", delete_message_days=7)
                await interaction.guild.unban(self.target, reason="Softban - remoção automática")
                action_text = "foi expulso (softban) e suas mensagens foram removidas"
                log_color = 0xFF4500
            else:
                # Ban normal
                delete_days = min(7, max(0, self.days)) if self.days > 0 else 7
                await self.target.ban(reason=reason, delete_message_days=delete_days)
                action_text = (
                    "foi banido permanentemente"
                    if self.days == 0
                    else f"foi banido por {self.days} dias"
                )
                log_color = 0x8B0000

            # Salvar no banco para logs
            try:
                from ...utils.database import database

                ban_data = {
                    "guild_id": str(interaction.guild.id),
                    "user_id": str(self.target.id),
                    "moderator_id": str(interaction.user.id),
                    "action_type": self.ban_type.lower(),
                    "reason": reason,
                    "dm_message": dm_message,
                    "dm_sent": dm_sent,
                    "duration_days": self.days,
                    "created_at": datetime.now().isoformat(),
                }

                await database.execute(
                    """INSERT INTO moderation_logs 
                    (guild_id, user_id, moderator_id, action_type, reason, action_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        ban_data["guild_id"],
                        ban_data["user_id"],
                        ban_data["moderator_id"],
                        ban_data["action_type"],
                        ban_data["reason"],
                        str(ban_data),
                        ban_data["created_at"],
                    ),
                )
            except Exception as e:
                print(f"❌ Erro ao salvar log: {e}")

            # Embed de confirmação
            success_embed = discord.Embed(
                title=f"✅ **{self.ban_type.upper()} EXECUTADO**",
                description=f"**{self.target.mention}** {action_text}.",
                color=log_color,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="👤 Usuário", value=f"{self.target.mention}\n`{self.target.id}`", inline=True
            )

            success_embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            success_embed.add_field(name="📋 Motivo", value=reason, inline=False)

            if self.days > 0 and self.ban_type != "Softban":
                success_embed.add_field(name="⏰ Duração", value=f"{self.days} dias", inline=True)

            success_embed.add_field(
                name="💬 DM Enviada",
                value="✅ Sim" if dm_sent else "❌ Não foi possível",
                inline=True,
            )

            if self.ban_type == "Softban":
                success_embed.add_field(
                    name="🧹 Mensagens Removidas", value="✅ Últimas 7 dias", inline=True
                )

            success_embed.set_thumbnail(url=self.target.display_avatar.url)
            success_embed.set_footer(
                text=f"Executado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

            # Enviar para canal de logs se configurado
            try:
                log_config = await database.get(
                    "SELECT channel_id FROM logs WHERE guild_id = ? AND log_type = 'moderation'",
                    (str(interaction.guild.id),),
                )

                if log_config:
                    log_channel = interaction.guild.get_channel(int(log_config["channel_id"]))
                    if log_channel:
                        await log_channel.send(embed=success_embed)
            except:
                pass

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ **Sem permissão**\nNão tenho permissão para banir este usuário.\n"
                "Verifique se minha role está acima da role dele e se tenho a permissão 'Banir Membros'.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ **Erro HTTP**\nErro ao executar banimento: {e!s}", ephemeral=True
            )
        except Exception as e:
            print(f"❌ Erro no modal de ban: {e}")
            await interaction.followup.send(
                "❌ Erro inesperado ao executar banimento.", ephemeral=True
            )


class AdvancedBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="🔨 Banir um usuário do servidor")
    @app_commands.describe(usuario="Usuário para banir", tipo="Tipo de banimento")
    async def ban_user(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        tipo: Literal["Normal", "Softban"] = "Normal",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.ban_members:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para banir membros. **Necessário**: Banir Membros",
                    ephemeral=True,
                )
                return

            # Verificar se o bot tem permissão
            if not interaction.guild.me.guild_permissions.ban_members:
                await interaction.response.send_message(
                    "❌ Eu não tenho permissão para banir membros.", ephemeral=True
                )
                return

            # Verificar hierarquia
            if (
                usuario.top_role >= interaction.user.top_role
                and interaction.user.id != interaction.guild.owner_id
            ):
                await interaction.response.send_message(
                    "❌ Você não pode banir este usuário pois ele tem uma role igual ou superior à sua.",
                    ephemeral=True,
                )
                return

            if usuario.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "❌ Não posso banir este usuário pois ele tem uma role igual ou superior à minha.",
                    ephemeral=True,
                )
                return

            # Verificar se não é owner
            if usuario.id == interaction.guild.owner_id:
                await interaction.response.send_message(
                    "❌ Não posso banir o dono do servidor.", ephemeral=True
                )
                return

            # Verificar se não é o próprio usuário
            if usuario.id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ Você não pode banir a si mesmo.", ephemeral=True
                )
                return

            # Verificar se não é o bot
            if usuario.id == self.bot.user.id:
                await interaction.response.send_message(
                    "❌ Não posso banir a mim mesmo.", ephemeral=True
                )
                return

            # Abrir modal para motivo
            modal = BanReasonModal(usuario, tipo)
            await interaction.response.send_modal(modal)

        except Exception as e:
            print(f"❌ Erro no comando ban: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao processar comando de banimento.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="unban", description="🔓 Desbanir um usuário")
    @app_commands.describe(user_id="ID do usuário para desbanir", motivo="Motivo do desbanimento")
    async def unban_user(
        self,
        interaction: discord.Interaction,
        user_id: str,
        motivo: str | None = "Não especificado",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.ban_members:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para desbanir membros.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Validar ID
            try:
                user_id_int = int(user_id)
            except:
                await interaction.followup.send(
                    "❌ ID de usuário inválido. Use apenas números.", ephemeral=True
                )
                return

            # Verificar se está banido
            banned_users = [entry async for entry in interaction.guild.bans()]
            banned_user = None

            for ban_entry in banned_users:
                if ban_entry.user.id == user_id_int:
                    banned_user = ban_entry
                    break

            if not banned_user:
                await interaction.followup.send(
                    "❌ Este usuário não está banido ou o ID não foi encontrado.", ephemeral=True
                )
                return

            # Executar unban
            try:
                await interaction.guild.unban(
                    banned_user.user, reason=f"[{interaction.user}] {motivo}"
                )
            except discord.NotFound:
                await interaction.followup.send(
                    "❌ Usuário não encontrado na lista de banidos.", ephemeral=True
                )
                return
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Sem permissão para desbanir usuários.", ephemeral=True
                )
                return

            # Salvar log
            try:
                from ...utils.database import database

                await database.execute(
                    """INSERT INTO moderation_logs 
                    (guild_id, user_id, moderator_id, action_type, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        str(interaction.guild.id),
                        str(user_id_int),
                        str(interaction.user.id),
                        "unban",
                        motivo,
                        datetime.now().isoformat(),
                    ),
                )
            except:
                pass

            # Embed de sucesso
            success_embed = discord.Embed(
                title="🔓 **USUÁRIO DESBANIDO**",
                description=f"**{banned_user.user}** foi desbanido com sucesso.",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="👤 Usuário",
                value=f"{banned_user.user.mention}\n`{banned_user.user.id}`",
                inline=True,
            )

            success_embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            success_embed.add_field(
                name="📋 Motivo Original do Ban",
                value=banned_user.reason or "Não especificado",
                inline=False,
            )

            success_embed.add_field(name="📋 Motivo do Unban", value=motivo, inline=False)

            success_embed.set_thumbnail(url=banned_user.user.display_avatar.url)
            success_embed.set_footer(
                text=f"Desbanido por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

            # Log channel
            try:
                log_config = await database.get(
                    "SELECT channel_id FROM logs WHERE guild_id = ? AND log_type = 'moderation'",
                    (str(interaction.guild.id),),
                )

                if log_config:
                    log_channel = interaction.guild.get_channel(int(log_config["channel_id"]))
                    if log_channel:
                        await log_channel.send(embed=success_embed)
            except:
                pass

        except Exception as e:
            print(f"❌ Erro no comando unban: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao processar desbanimento.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="banlist", description="📋 Ver lista de usuários banidos")
    @app_commands.describe(buscar="Buscar por nome ou ID específico")
    async def ban_list(self, interaction: discord.Interaction, buscar: str | None = None):
        try:
            if not interaction.user.guild_permissions.ban_members:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para ver a lista de banidos.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar banidos
            banned_users = []
            async for ban_entry in interaction.guild.bans():
                banned_users.append(ban_entry)

            if not banned_users:
                empty_embed = discord.Embed(
                    title="📋 **LISTA DE BANIDOS**",
                    description="✅ Não há usuários banidos neste servidor.",
                    color=0x00FF00,
                    timestamp=datetime.now(),
                )

                await interaction.followup.send(embed=empty_embed, ephemeral=True)
                return

            # Filtrar se há busca
            if buscar:
                filtered_bans = []
                search_term = buscar.lower()

                for ban_entry in banned_users:
                    user = ban_entry.user
                    if (
                        search_term in user.name.lower()
                        or search_term in (user.global_name or "").lower()
                        or search_term == str(user.id)
                    ):
                        filtered_bans.append(ban_entry)

                banned_users = filtered_bans

                if not banned_users:
                    await interaction.followup.send(
                        f"❌ Nenhum usuário banido encontrado com: `{buscar}`", ephemeral=True
                    )
                    return

            # Criar embed
            ban_embed = discord.Embed(
                title="📋 **LISTA DE USUÁRIOS BANIDOS**",
                description=f"Total: {len(banned_users)} usuário{'s' if len(banned_users) != 1 else ''} banido{'s' if len(banned_users) != 1 else ''}",
                color=0xFF6B6B,
                timestamp=datetime.now(),
            )

            # Mostrar até 10 banidos por página
            display_count = min(10, len(banned_users))

            for i, ban_entry in enumerate(banned_users[:display_count], 1):
                user = ban_entry.user
                reason = ban_entry.reason or "Motivo não especificado"

                ban_info = f"**ID:** `{user.id}`\n"
                ban_info += f"**Motivo:** {reason[:100]}{'...' if len(reason) > 100 else ''}\n"
                ban_info += f"**Comando Unban:** `/unban {user.id}`"

                ban_embed.add_field(
                    name=f"🔨 {user.name}#{user.discriminator}", value=ban_info, inline=False
                )

            if len(banned_users) > 10:
                ban_embed.add_field(
                    name="➕ Mais Usuários",
                    value=f"... e mais {len(banned_users) - 10} usuários banidos.\n"
                    f"Use `/banlist buscar:<nome_ou_id>` para encontrar específicos.",
                    inline=False,
                )

            ban_embed.set_footer(
                text=f"Consultado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=ban_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando banlist: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao consultar lista de banidos.", ephemeral=True
                )
            except:
                pass


async def setup(bot):
    await bot.add_cog(AdvancedBan(bot))
