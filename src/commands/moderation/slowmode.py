"""
Comando Slowmode - Moderation
Sistema de controle de slowmode em canais
"""


import discord
from discord import app_commands
from discord.ext import commands


class SlowmodeCommand(commands.Cog):
    """Sistema de slowmode para moderação"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def format_time(self, seconds: int) -> str:
        """Formatar tempo em formato legível"""
        if seconds == 0:
            return "Removido"
        if seconds < 60:
            return f"{seconds} segundos"
        if seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds > 0:
                return f"{minutes}m {remaining_seconds}s"
            return f"{minutes} minutos"
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}m"
        return f"{hours} horas"

    @app_commands.command(name="slowmode", description="Modifica o slowmode de um canal")
    @app_commands.describe(
        tempo="Tempo em segundos (0-21600, 0 = desativar)",
        canal="Canal para modificar (padrão: canal atual)",
        motivo="Motivo da alteração",
    )
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(
        self,
        interaction: discord.Interaction,
        tempo: app_commands.Range[int, 0, 21600],
        canal: discord.TextChannel | None = None,
        motivo: str = "Não especificado",
    ):
        """Definir slowmode em um canal"""

        # Verificar permissões do usuário
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ Você não tem permissão para gerenciar canais.", ephemeral=True
            )
            return

        # Usar canal atual se não especificado
        target_channel = canal or interaction.channel

        # Verificar se é um canal de texto
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em canais de texto.", ephemeral=True
            )
            return

        # Verificar permissões do bot no canal
        bot_perms = target_channel.permissions_for(interaction.guild.me)
        if not bot_perms.manage_channels:
            await interaction.response.send_message(
                "❌ Não tenho permissão para gerenciar este canal.", ephemeral=True
            )
            return

        try:
            # Obter slowmode atual para comparação
            old_slowmode = target_channel.slowmode_delay

            # Aplicar novo slowmode
            reason = f"{motivo} - Por: {interaction.user}"
            await target_channel.edit(slowmode_delay=tempo, reason=reason)

            # Formatar tempos para exibição
            new_time_display = self.format_time(tempo)
            old_time_display = self.format_time(old_slowmode)

            # Criar embed de confirmação
            embed = discord.Embed(
                title="⏱️ Slowmode Alterado",
                description=f"Slowmode do canal {target_channel.mention} foi alterado com sucesso.",
                color=0x00FF00 if tempo == 0 else 0xFF9900,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(name="⏱️ Slowmode Anterior", value=old_time_display, inline=True)

            embed.add_field(name="⏰ Novo Slowmode", value=new_time_display, inline=True)

            embed.add_field(name="👮 Moderador", value=interaction.user.mention, inline=True)

            embed.add_field(name="📍 Canal", value=target_channel.mention, inline=True)

            embed.add_field(name="📝 Motivo", value=motivo, inline=False)

            # Adicionar informações úteis
            if tempo > 0:
                embed.add_field(
                    name="ℹ️ Informação",
                    value=f"Membros poderão enviar mensagens a cada **{new_time_display}**",
                    inline=False,
                )

                # Avisos baseados no tempo
                if tempo >= 3600:  # 1 hora ou mais
                    embed.add_field(
                        name="⚠️ Aviso",
                        value="Slowmode muito alto pode prejudicar conversas normais.",
                        inline=False,
                    )
            else:
                embed.add_field(
                    name="✅ Status",
                    value="Slowmode removido - mensagens sem limitação de tempo",
                    inline=False,
                )

            embed.set_footer(
                text=f"Executado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed)

            # Log no canal de moderação
            log_channels = ["mod-logs", "logs", "moderation", "moderacao"]
            log_channel = None

            for channel_name in log_channels:
                log_channel = discord.utils.get(interaction.guild.channels, name=channel_name)
                if log_channel and log_channel != target_channel:
                    break

            if log_channel and isinstance(log_channel, discord.TextChannel):
                log_embed = discord.Embed(
                    title="⏱️ Slowmode Alterado", color=0x0099FF, timestamp=discord.utils.utcnow()
                )

                log_embed.add_field(name="📍 Canal", value=target_channel.mention, inline=True)

                log_embed.add_field(name="👮 Moderador", value=str(interaction.user), inline=True)

                log_embed.add_field(
                    name="⏰ Alteração",
                    value=f"{old_time_display} → {new_time_display}",
                    inline=True,
                )

                log_embed.add_field(name="📝 Motivo", value=motivo, inline=False)

                await log_channel.send(embed=log_embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para alterar o slowmode deste canal.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao definir slowmode: `{e!s}`", ephemeral=True
            )

    @app_commands.command(name="slowmode-info", description="Mostra informações do slowmode atual")
    @app_commands.describe(canal="Canal para verificar (padrão: canal atual)")
    async def slowmode_info(
        self, interaction: discord.Interaction, canal: discord.TextChannel | None = None
    ):
        """Mostrar informações do slowmode atual"""

        target_channel = canal or interaction.channel

        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em canais de texto.", ephemeral=True
            )
            return

        slowmode = target_channel.slowmode_delay
        time_display = self.format_time(slowmode)

        embed = discord.Embed(
            title="ℹ️ Informações do Slowmode",
            description=f"Informações do slowmode do canal {target_channel.mention}",
            color=0x0099FF if slowmode > 0 else 0x00FF00,
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(name="⏰ Tempo Atual", value=time_display, inline=True)

        embed.add_field(name="📊 Valor em Segundos", value=str(slowmode), inline=True)

        embed.add_field(name="🔢 Limite Máximo", value="6 horas (21600s)", inline=True)

        if slowmode > 0:
            embed.add_field(
                name="📝 Descrição",
                value=f"Membros podem enviar mensagens a cada **{time_display}**",
                inline=False,
            )
        else:
            embed.add_field(
                name="📝 Descrição",
                value="Nenhuma limitação de tempo entre mensagens",
                inline=False,
            )

        # Sugestões baseadas no slowmode atual
        suggestions = []
        if slowmode == 0:
            suggestions.append("• Use `/slowmode tempo:5` para slowmode leve")
            suggestions.append("• Use `/slowmode tempo:30` para conversas controladas")
        elif slowmode < 10:
            suggestions.append("• Slowmode baixo - adequado para canais ativos")
        elif slowmode < 60:
            suggestions.append("• Slowmode moderado - bom para controle básico")
        elif slowmode < 300:
            suggestions.append("• Slowmode alto - conversas mais lentas")
        else:
            suggestions.append("• Slowmode muito alto - apenas mensagens importantes")

        if suggestions:
            embed.add_field(name="💡 Sugestões", value="\n".join(suggestions), inline=False)

        embed.set_footer(
            text=f"Consultado por {interaction.user}", icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(SlowmodeCommand(bot))
