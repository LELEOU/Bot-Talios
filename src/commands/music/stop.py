"""
Sistema de Música - Comando Stop
Para parar a reprodução atual e limpar fila
"""

import discord
from discord import app_commands
from discord.ext import commands


class MusicStop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stop", description="⏹️ Para a reprodução de música e limpa a fila")
    async def stop_music(self, interaction: discord.Interaction):
        try:
            # 🔍 VERIFICAR SE USUÁRIO ESTÁ EM CANAL DE VOZ
            if not interaction.user.voice:
                await interaction.response.send_message(
                    "❌ Você precisa estar em um canal de voz para usar este comando!",
                    ephemeral=True,
                )
                return

            voice_channel = interaction.user.voice.channel

            # 🔍 VERIFICAR SE BOT ESTÁ CONECTADO
            voice_client = interaction.guild.voice_client
            if not voice_client:
                await interaction.response.send_message(
                    "❌ Não estou tocando música no momento!", ephemeral=True
                )
                return

            # 🔍 VERIFICAR SE ESTÃO NO MESMO CANAL
            if voice_client.channel != voice_channel:
                await interaction.response.send_message(
                    f"❌ Você precisa estar no canal {voice_client.channel.mention} para controlar a música!",
                    ephemeral=True,
                )
                return

            # ⏹️ PARAR MÚSICA E DESCONECTAR
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()

            await voice_client.disconnect()

            # 🧹 LIMPAR FILA (se implementada)
            guild_id = str(interaction.guild.id)
            if hasattr(self.bot, "music_queues"):
                self.bot.music_queues.pop(guild_id, None)

            # ✅ EMBED DE CONFIRMAÇÃO
            embed = discord.Embed(
                title="⏹️ Música Parada",
                description="A reprodução foi interrompida e a fila foi limpa.",
                color=0xFF0000,
                timestamp=interaction.created_at,
            )

            embed.add_field(name="👤 Parado por", value=interaction.user.mention, inline=True)

            embed.add_field(name="📍 Canal", value=voice_channel.mention, inline=True)

            embed.set_footer(
                text="Use /play para tocar música novamente",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando stop: {e}")
            await interaction.response.send_message(
                "❌ Erro ao parar a música. Tente novamente.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(MusicStop(bot))
