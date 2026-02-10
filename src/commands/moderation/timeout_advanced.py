"""
Sistema de Timeout - Sistema de Timeout/Mute Temporário Avançado
Sistema completo de timeout com duração variável e gerenciamento
"""

import json
from datetime import datetime, timedelta
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands, tasks


class TimeoutModal(discord.ui.Modal):
    """Modal para especificar detalhes do timeout"""

    def __init__(self, target: discord.Member, duration: timedelta):
        super().__init__(title=f"⏰ Timeout - {target.display_name}", timeout=300)
        self.target = target
        self.duration = duration

        # Campo para motivo
        self.reason_field = discord.ui.TextInput(
            label="Motivo do Timeout",
            placeholder="Por que este usuário está sendo colocado em timeout?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500,
        )

        # Campo para mensagem opcional
        self.dm_message = discord.ui.TextInput(
            label="Mensagem Adicional (Opcional)",
            placeholder="Mensagem que será enviada ao usuário...",
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

            # Enviar DM antes do timeout
            dm_sent = False
            try:
                dm_embed = discord.Embed(
                    title="⏰ **VOCÊ FOI COLOCADO EM TIMEOUT**",
                    description=f"Servidor: **{interaction.guild.name}**",
                    color=0xFFA500,
                    timestamp=datetime.now(),
                )

                dm_embed.add_field(name="📋 Motivo", value=reason, inline=False)

                dm_embed.add_field(
                    name="⏰ Duração", value=self.format_duration(self.duration), inline=True
                )

                dm_embed.add_field(
                    name="⏰ Liberdade em",
                    value=f"<t:{int((datetime.now() + self.duration).timestamp())}:R>",
                    inline=True,
                )

                if dm_message:
                    dm_embed.add_field(
                        name="💬 Mensagem do Moderador", value=dm_message, inline=False
                    )

                dm_embed.add_field(
                    name="ℹ️ Durante o Timeout",
                    value="• Você não pode enviar mensagens\n"
                    "• Você não pode reagir a mensagens\n"
                    "• Você não pode entrar em calls\n"
                    "• Você pode ver mensagens normalmente",
                    inline=False,
                )

                dm_embed.set_footer(
                    text=f"Moderador: {interaction.user}",
                    icon_url=interaction.user.display_avatar.url,
                )

                await self.target.send(embed=dm_embed)
                dm_sent = True

            except:
                dm_sent = False

            # Aplicar timeout
            await self.target.timeout(
                datetime.now() + self.duration, reason=f"[{interaction.user}] {reason}"
            )

            # Salvar no banco de dados
            try:
                from ...utils.database import database

                timeout_data = {
                    "guild_id": str(interaction.guild.id),
                    "user_id": str(self.target.id),
                    "moderator_id": str(interaction.user.id),
                    "reason": reason,
                    "dm_message": dm_message,
                    "dm_sent": dm_sent,
                    "duration_seconds": int(self.duration.total_seconds()),
                    "ends_at": (datetime.now() + self.duration).isoformat(),
                    "created_at": datetime.now().isoformat(),
                }

                await database.execute(
                    """INSERT INTO moderation_logs 
                    (guild_id, user_id, moderator_id, action_type, reason, action_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        timeout_data["guild_id"],
                        timeout_data["user_id"],
                        timeout_data["moderator_id"],
                        "timeout",
                        timeout_data["reason"],
                        json.dumps(timeout_data),
                        timeout_data["created_at"],
                    ),
                )

            except Exception as e:
                print(f"❌ Erro ao salvar timeout: {e}")

            # Embed de confirmação
            success_embed = discord.Embed(
                title="⏰ **TIMEOUT APLICADO**",
                description=f"**{self.target.mention}** foi colocado em timeout.",
                color=0xFFA500,
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

            success_embed.add_field(
                name="⏰ Duração", value=self.format_duration(self.duration), inline=True
            )

            success_embed.add_field(
                name="🕐 Termina em",
                value=f"<t:{int((datetime.now() + self.duration).timestamp())}:R>",
                inline=True,
            )

            success_embed.add_field(name="📋 Motivo", value=reason, inline=False)

            success_embed.add_field(
                name="💬 DM Enviada", value="✅ Sim" if dm_sent else "❌ Falhou", inline=True
            )

            success_embed.set_thumbnail(url=self.target.display_avatar.url)
            success_embed.set_footer(
                text=f"Aplicado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

            # Enviar para canal de logs
            try:
                log_config = await database.get(
                    "SELECT channel_id FROM logs WHERE guild_id = ? AND log_type = 'moderation'",
                    (str(interaction.guild.id),),
                )

                if log_config:
                    log_channel = interaction.guild.get_channel(int(log_config["channel_id"]))
                    if log_channel:
                        public_embed = success_embed.copy()
                        public_embed.remove_field(5)  # Remover campo DM para log público
                        await log_channel.send(embed=public_embed)
            except:
                pass

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ **Sem permissão**\nNão posso aplicar timeout neste usuário.\n"
                "Verifique se minha role está acima da role dele.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            if "Cannot timeout" in str(e):
                await interaction.followup.send(
                    "❌ **Não é possível aplicar timeout**\n"
                    "Este usuário não pode receber timeout (pode ser moderador ou owner).",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"❌ **Erro HTTP**\nErro ao aplicar timeout: {e!s}", ephemeral=True
                )
        except Exception as e:
            print(f"❌ Erro no timeout modal: {e}")
            await interaction.followup.send(
                "❌ Erro inesperado ao aplicar timeout.", ephemeral=True
            )

    def format_duration(self, duration: timedelta) -> str:
        """Formatar duração para exibição"""
        total_seconds = int(duration.total_seconds())

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days} dia{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hora{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minuto{'s' if minutes != 1 else ''}")
        if seconds > 0 and not parts:  # Só mostrar segundos se não há outras unidades
            parts.append(f"{seconds} segundo{'s' if seconds != 1 else ''}")

        return ", ".join(parts) if parts else "Instantâneo"


class TimeoutSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timeout_check.start()

    def cog_unload(self):
        self.timeout_check.cancel()

    @app_commands.command(name="timeout", description="⏰ Colocar usuário em timeout")
    @app_commands.describe(
        usuario="Usuário para colocar em timeout",
        duracao="Duração do timeout",
        unidade="Unidade de tempo",
    )
    async def timeout_user(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        duracao: int,
        unidade: Literal["minutos", "horas", "dias"] = "minutos",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para aplicar timeout. **Necessário**: Moderar Membros",
                    ephemeral=True,
                )
                return

            # Verificar hierarquia
            if (
                usuario.top_role >= interaction.user.top_role
                and interaction.user.id != interaction.guild.owner_id
            ):
                await interaction.response.send_message(
                    "❌ Você não pode aplicar timeout neste usuário pois ele tem uma role igual ou superior à sua.",
                    ephemeral=True,
                )
                return

            if usuario.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "❌ Não posso aplicar timeout neste usuário pois ele tem uma role igual ou superior à minha.",
                    ephemeral=True,
                )
                return

            # Verificar se não é owner ou o próprio usuário
            if usuario.id == interaction.guild.owner_id:
                await interaction.response.send_message(
                    "❌ Não posso aplicar timeout no dono do servidor.", ephemeral=True
                )
                return

            if usuario.id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ Você não pode aplicar timeout em si mesmo.", ephemeral=True
                )
                return

            if usuario.id == self.bot.user.id:
                await interaction.response.send_message(
                    "❌ Não posso aplicar timeout em mim mesmo.", ephemeral=True
                )
                return

            # Validar duração
            if duracao <= 0:
                await interaction.response.send_message(
                    "❌ A duração deve ser um número positivo.", ephemeral=True
                )
                return

            # Calcular duração em segundos
            if unidade == "minutos":
                if duracao > 40320:  # 28 dias em minutos
                    await interaction.response.send_message(
                        "❌ Duração máxima: 40320 minutos (28 dias).", ephemeral=True
                    )
                    return
                duration = timedelta(minutes=duracao)
            elif unidade == "horas":
                if duracao > 672:  # 28 dias em horas
                    await interaction.response.send_message(
                        "❌ Duração máxima: 672 horas (28 dias).", ephemeral=True
                    )
                    return
                duration = timedelta(hours=duracao)
            elif unidade == "dias":
                if duracao > 28:
                    await interaction.response.send_message(
                        "❌ Duração máxima: 28 dias.", ephemeral=True
                    )
                    return
                duration = timedelta(days=duracao)

            # Verificar se já está em timeout
            if usuario.is_timed_out():
                current_timeout = usuario.timed_out_until
                await interaction.response.send_message(
                    f"⚠️ **Usuário já está em timeout**\n"
                    f"Timeout atual termina <t:{int(current_timeout.timestamp())}:R>\n"
                    f"Use `/untimeout` para remover o timeout atual primeiro.",
                    ephemeral=True,
                )
                return

            # Abrir modal para detalhes
            modal = TimeoutModal(usuario, duration)
            await interaction.response.send_modal(modal)

        except Exception as e:
            print(f"❌ Erro no comando timeout: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao processar comando de timeout.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="untimeout", description="🔓 Remover timeout de um usuário")
    @app_commands.describe(
        usuario="Usuário para remover timeout", motivo="Motivo da remoção do timeout"
    )
    async def untimeout_user(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        motivo: str | None = "Não especificado",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para remover timeout.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Verificar se está em timeout
            if not usuario.is_timed_out():
                await interaction.followup.send(
                    "❌ Este usuário não está em timeout.", ephemeral=True
                )
                return

            # Salvar informação do timeout atual
            current_timeout = usuario.timed_out_until

            # Remover timeout
            await usuario.timeout(None, reason=f"[{interaction.user}] {motivo}")

            # Salvar log
            try:
                from ...utils.database import database

                await database.execute(
                    """INSERT INTO moderation_logs 
                    (guild_id, user_id, moderator_id, action_type, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        str(interaction.guild.id),
                        str(usuario.id),
                        str(interaction.user.id),
                        "untimeout",
                        motivo,
                        datetime.now().isoformat(),
                    ),
                )
            except:
                pass

            # Enviar DM ao usuário
            try:
                dm_embed = discord.Embed(
                    title="🔓 **SEU TIMEOUT FOI REMOVIDO**",
                    description=f"Servidor: **{interaction.guild.name}**",
                    color=0x00FF00,
                    timestamp=datetime.now(),
                )

                dm_embed.add_field(name="📋 Motivo", value=motivo, inline=False)

                dm_embed.add_field(
                    name="👮 Removido por", value=interaction.user.mention, inline=True
                )

                dm_embed.add_field(
                    name="⏰ Timeout Original",
                    value=f"Terminaria <t:{int(current_timeout.timestamp())}:R>",
                    inline=True,
                )

                dm_embed.add_field(
                    name="✅ Agora você pode:",
                    value="• Enviar mensagens\n• Reagir a mensagens\n• Entrar em calls",
                    inline=False,
                )

                await usuario.send(embed=dm_embed)
                dm_sent = True
            except:
                dm_sent = False

            # Embed de confirmação
            success_embed = discord.Embed(
                title="🔓 **TIMEOUT REMOVIDO**",
                description=f"O timeout de **{usuario.mention}** foi removido.",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="👤 Usuário", value=f"{usuario.mention}\n`{usuario.id}`", inline=True
            )

            success_embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            success_embed.add_field(
                name="⏰ Timeout Original",
                value=f"Terminaria <t:{int(current_timeout.timestamp())}:R>",
                inline=True,
            )

            success_embed.add_field(name="📋 Motivo", value=motivo, inline=False)

            success_embed.add_field(
                name="💬 DM Enviada", value="✅ Sim" if dm_sent else "❌ Falhou", inline=True
            )

            success_embed.set_thumbnail(url=usuario.display_avatar.url)
            success_embed.set_footer(
                text=f"Removido por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

            # Canal de logs
            try:
                log_config = await database.get(
                    "SELECT channel_id FROM logs WHERE guild_id = ? AND log_type = 'moderation'",
                    (str(interaction.guild.id),),
                )

                if log_config:
                    log_channel = interaction.guild.get_channel(int(log_config["channel_id"]))
                    if log_channel:
                        public_embed = success_embed.copy()
                        public_embed.remove_field(4)  # Remover campo DM
                        await log_channel.send(embed=public_embed)
            except:
                pass

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Sem permissão para remover timeout deste usuário.", ephemeral=True
            )
        except Exception as e:
            print(f"❌ Erro no comando untimeout: {e}")
            try:
                await interaction.followup.send("❌ Erro ao remover timeout.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="timeouts", description="📋 Ver usuários em timeout")
    async def list_timeouts(self, interaction: discord.Interaction):
        try:
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para ver timeouts.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar membros em timeout
            timed_out_members = [
                member for member in interaction.guild.members if member.is_timed_out()
            ]

            if not timed_out_members:
                empty_embed = discord.Embed(
                    title="📋 **USUÁRIOS EM TIMEOUT**",
                    description="✅ Não há usuários em timeout no momento.",
                    color=0x00FF00,
                    timestamp=datetime.now(),
                )

                await interaction.followup.send(embed=empty_embed, ephemeral=True)
                return

            # Ordenar por tempo restante
            timed_out_members.sort(key=lambda m: m.timed_out_until)

            list_embed = discord.Embed(
                title="⏰ **USUÁRIOS EM TIMEOUT**",
                description=f"Total: {len(timed_out_members)} usuário{'s' if len(timed_out_members) != 1 else ''} em timeout",
                color=0xFFA500,
                timestamp=datetime.now(),
            )

            for i, member in enumerate(timed_out_members[:10], 1):  # Máximo 10
                timeout_end = member.timed_out_until

                member_info = f"**ID:** `{member.id}`\n"
                member_info += f"**Termina:** <t:{int(timeout_end.timestamp())}:R>\n"
                member_info += f"**Data:** <t:{int(timeout_end.timestamp())}:f>"

                list_embed.add_field(
                    name=f"⏰ {member.display_name}", value=member_info, inline=True
                )

            if len(timed_out_members) > 10:
                list_embed.add_field(
                    name="➕ Mais Timeouts",
                    value=f"... e mais {len(timed_out_members) - 10} usuários em timeout.",
                    inline=False,
                )

            list_embed.add_field(
                name="💡 Comandos Úteis",
                value="`/untimeout @usuário` - Remover timeout\n"
                "`/timeout @usuário <tempo>` - Aplicar timeout",
                inline=False,
            )

            list_embed.set_footer(
                text=f"Consultado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=list_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando timeouts: {e}")
            try:
                await interaction.followup.send("❌ Erro ao consultar timeouts.", ephemeral=True)
            except:
                pass

    @tasks.loop(minutes=5)
    async def timeout_check(self):
        """Verifica timeouts que expiraram para logs"""
        try:
            # Esta task roda a cada 5 minutos para verificar timeouts expirados
            # e fazer limpeza se necessário
            pass
        except Exception as e:
            print(f"❌ Erro na task de timeout: {e}")


async def setup(bot):
    await bot.add_cog(TimeoutSystem(bot))
