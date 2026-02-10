"""
Comando Music Play - Music
Sistema básico de música para Discord
"""

import asyncio

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands


class MusicPlayer:
    """Classe para gerenciar a reprodução de música"""

    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.queue = []
        self.current = None
        self.voice_client = None
        self.is_playing = False
        self.is_paused = False
        self.loop_mode = "off"  # off, single, queue

    def add_to_queue(self, track):
        """Adicionar música à fila"""
        self.queue.append(track)

    def get_next_track(self):
        """Obter próxima música"""
        if self.loop_mode == "single" and self.current:
            return self.current
        if self.queue:
            return self.queue.pop(0)
        return None

    def clear_queue(self):
        """Limpar a fila"""
        self.queue.clear()


class MusicCommand(commands.Cog):
    """Sistema de música do bot"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, MusicPlayer] = {}

        # Configurações do yt-dlp
        self.ytdl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "extractaudio": True,
            "audioformat": "mp3",
            "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
            "restrictfilenames": True,
            "logtostderr": False,
            "ignoreerrors": False,
            "default_search": "ytsearch",
            "source_address": "0.0.0.0",
        }

        self.ytdl = yt_dlp.YoutubeDL(self.ytdl_opts)

    def get_player(self, guild_id: int) -> MusicPlayer:
        """Obter ou criar player para o servidor"""
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(guild_id)
        return self.players[guild_id]

    async def search_youtube(self, query: str):
        """Buscar música no YouTube"""
        try:
            # Buscar informações da música
            data = await self.bot.loop.run_in_executor(
                None, lambda: self.ytdl.extract_info(f"ytsearch:{query}", download=False)
            )

            if not data or "entries" not in data or not data["entries"]:
                return None

            entry = data["entries"][0]

            return {
                "title": entry.get("title", "Título Desconhecido"),
                "url": entry.get("webpage_url", entry.get("url")),
                "duration": entry.get("duration", 0),
                "uploader": entry.get("uploader", "Desconhecido"),
                "thumbnail": entry.get("thumbnail"),
                "stream_url": entry.get("url"),
            }

        except Exception as e:
            print(f"Erro na busca: {e}")
            return None

    async def play_next(self, guild_id: int):
        """Tocar próxima música"""
        player = self.get_player(guild_id)

        if not player.voice_client or not player.voice_client.is_connected():
            return

        next_track = player.get_next_track()
        if not next_track:
            player.is_playing = False
            return

        try:
            # Obter URL de stream atualizada
            data = await self.bot.loop.run_in_executor(
                None, lambda: self.ytdl.extract_info(next_track["url"], download=False)
            )

            stream_url = data["url"]

            # Criar fonte de áudio
            source = discord.FFmpegPCMAudio(
                stream_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            )

            player.current = next_track
            player.is_playing = True

            # Tocar música
            player.voice_client.play(
                source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(guild_id), self.bot.loop
                ),
            )

        except Exception as e:
            print(f"Erro ao tocar música: {e}")
            await self.play_next(guild_id)  # Tentar próxima

    @app_commands.command(name="play", description="Toca uma música do YouTube")
    @app_commands.describe(consulta="Nome da música ou URL do YouTube")
    async def play(self, interaction: discord.Interaction, consulta: str):
        """Tocar música"""

        # Verificar se o usuário está em um canal de voz
        if not interaction.user.voice:
            await interaction.response.send_message(
                "❌ Você precisa estar em um canal de voz!", ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel
        player = self.get_player(interaction.guild.id)

        await interaction.response.defer()

        try:
            # Conectar ao canal de voz se necessário
            if not player.voice_client or not player.voice_client.is_connected():
                try:
                    player.voice_client = await voice_channel.connect()
                except Exception as e:
                    await interaction.followup.send(
                        f"❌ Erro ao conectar no canal de voz: `{e!s}`"
                    )
                    return

            # Buscar a música
            track_info = await self.search_youtube(consulta)

            if not track_info:
                await interaction.followup.send("❌ Não foi possível encontrar esta música!")
                return

            # Adicionar à fila
            player.add_to_queue(track_info)

            # Se não estiver tocando, iniciar reprodução
            if not player.is_playing:
                await self.play_next(interaction.guild.id)

                # Embed para música atual
                embed = discord.Embed(
                    title="🎵 Tocando Agora",
                    description=f"**[{track_info['title']}]({track_info['url']})**",
                    color=0x00FF00,
                    timestamp=discord.utils.utcnow(),
                )

                embed.add_field(name="👤 Canal", value=track_info["uploader"], inline=True)

                if track_info["duration"]:
                    duration = f"{track_info['duration'] // 60}:{track_info['duration'] % 60:02d}"
                    embed.add_field(name="⏱️ Duração", value=duration, inline=True)

                embed.add_field(
                    name="🎤 Solicitado por", value=interaction.user.mention, inline=True
                )

                if track_info["thumbnail"]:
                    embed.set_thumbnail(url=track_info["thumbnail"])

                await interaction.followup.send(embed=embed)

            else:
                # Embed para música adicionada à fila
                queue_position = len(player.queue)

                embed = discord.Embed(
                    title="➕ Adicionado à Fila",
                    description=f"**[{track_info['title']}]({track_info['url']})**",
                    color=0x0099FF,
                    timestamp=discord.utils.utcnow(),
                )

                embed.add_field(name="📍 Posição na Fila", value=f"#{queue_position}", inline=True)

                embed.add_field(name="👤 Canal", value=track_info["uploader"], inline=True)

                embed.add_field(
                    name="🎤 Solicitado por", value=interaction.user.mention, inline=True
                )

                if track_info["thumbnail"]:
                    embed.set_thumbnail(url=track_info["thumbnail"])

                await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao processar música: `{e!s}`")

    @app_commands.command(name="stop", description="Para a música e limpa a fila")
    async def stop(self, interaction: discord.Interaction):
        """Parar música"""

        player = self.get_player(interaction.guild.id)

        if not player.voice_client:
            await interaction.response.send_message(
                "❌ Não estou conectado em nenhum canal de voz!", ephemeral=True
            )
            return

        player.clear_queue()
        player.current = None
        player.is_playing = False

        if player.voice_client.is_playing():
            player.voice_client.stop()

        await player.voice_client.disconnect()
        player.voice_client = None

        embed = discord.Embed(
            title="⏹️ Música Parada",
            description="Reprodução parada e fila limpa.",
            color=0xFF0000,
            timestamp=discord.utils.utcnow(),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="Pula para a próxima música")
    async def skip(self, interaction: discord.Interaction):
        """Pular música"""

        player = self.get_player(interaction.guild.id)

        if not player.voice_client or not player.is_playing:
            await interaction.response.send_message(
                "❌ Nenhuma música está tocando!", ephemeral=True
            )
            return

        player.voice_client.stop()  # Isso vai trigger o play_next automaticamente

        embed = discord.Embed(
            title="⏭️ Música Pulada",
            description="Pulando para a próxima música...",
            color=0x00FF00,
            timestamp=discord.utils.utcnow(),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="queue", description="Mostra a fila de música")
    async def queue(self, interaction: discord.Interaction):
        """Mostrar fila"""

        player = self.get_player(interaction.guild.id)

        embed = discord.Embed(
            title="🎵 Fila de Música", color=0x0099FF, timestamp=discord.utils.utcnow()
        )

        if player.current:
            embed.add_field(
                name="🎵 Tocando Agora",
                value=f"**[{player.current['title']}]({player.current['url']})**",
                inline=False,
            )

        if not player.queue:
            embed.add_field(name="📝 Fila", value="A fila está vazia", inline=False)
        else:
            queue_text = []
            for i, track in enumerate(player.queue[:10], 1):  # Mostrar apenas 10
                queue_text.append(f"`{i}.` **[{track['title'][:50]}...]({track['url']})**")

            if len(player.queue) > 10:
                queue_text.append(f"... e mais {len(player.queue) - 10} músicas")

            embed.add_field(name="📝 Próximas na Fila", value="\n".join(queue_text), inline=False)

            embed.add_field(
                name="📊 Total", value=f"{len(player.queue)} música(s) na fila", inline=True
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="now", description="Mostra a música atual")
    async def now_playing(self, interaction: discord.Interaction):
        """Mostrar música atual"""

        player = self.get_player(interaction.guild.id)

        if not player.current or not player.is_playing:
            await interaction.response.send_message(
                "❌ Nenhuma música está tocando!", ephemeral=True
            )
            return

        track = player.current

        embed = discord.Embed(
            title="🎵 Tocando Agora",
            description=f"**[{track['title']}]({track['url']})**",
            color=0x00FF00,
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(name="👤 Canal", value=track["uploader"], inline=True)

        if track["duration"]:
            duration = f"{track['duration'] // 60}:{track['duration'] % 60:02d}"
            embed.add_field(name="⏱️ Duração", value=duration, inline=True)

        embed.add_field(
            name="📊 Status",
            value="▶️ Tocando" if not player.is_paused else "⏸️ Pausado",
            inline=True,
        )

        if track["thumbnail"]:
            embed.set_thumbnail(url=track["thumbnail"])

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(MusicCommand(bot))
