"""
Sistema de Música - Comando Skip
Pula para a próxima música na fila
"""

import discord
from discord import app_commands
from discord.ext import commands


class MusicSkip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="skip", description="⏭️ Pula para a próxima música na fila")
    async def skip_music(self, interaction: discord.Interaction):
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

            # 🔍 VERIFICAR SE ESTÁ TOCANDO
            if not voice_client.is_playing() and not voice_client.is_paused():
                await interaction.response.send_message(
                    "❌ Não há música tocando no momento!", ephemeral=True
                )
                return

            # 🎵 VERIFICAR FILA
            guild_id = str(interaction.guild.id)
            music_queue = getattr(self.bot, "music_queues", {}).get(guild_id, [])

            # ⏭️ PULAR MÚSICA
            voice_client.stop()  # Isso fará o after callback tocar a próxima música

            if len(music_queue) > 0:
                # ✅ HÁ PRÓXIMA MÚSICA
                next_song = music_queue[0]
                embed = discord.Embed(
                    title="⏭️ Música Pulada",
                    description=f"Pulando para: **{next_song.get('title', 'Próxima música')}**",
                    color=0x00FF00,
                    timestamp=interaction.created_at,
                )

                embed.add_field(name="👤 Pulado por", value=interaction.user.mention, inline=True)

                embed.add_field(
                    name="🎵 Fila Restante", value=f"{len(music_queue)} música(s)", inline=True
                )

                if "thumbnail" in next_song:
                    embed.set_thumbnail(url=next_song["thumbnail"])

            else:
                # ❌ NÃO HÁ PRÓXIMA MÚSICA
                embed = discord.Embed(
                    title="⏭️ Música Pulada",
                    description="Não há mais músicas na fila. A reprodução será encerrada.",
                    color=0xFFAA00,
                    timestamp=interaction.created_at,
                )

                embed.add_field(name="👤 Pulado por", value=interaction.user.mention, inline=True)

                embed.add_field(
                    name="💡 Dica",
                    value="Use `/play <música>` para adicionar mais músicas",
                    inline=False,
                )

            embed.set_footer(text="Sistema de Música", icon_url=interaction.user.display_avatar.url)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando skip: {e}")
            await interaction.response.send_message(
                "❌ Erro ao pular música. Tente novamente.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(MusicSkip(bot))
