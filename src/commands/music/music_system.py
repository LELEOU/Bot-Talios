"""
Sistema de Música Avançado
Reprodução de músicas do YouTube com controles completos
"""

import asyncio
import os
import sqlite3
from datetime import datetime

import discord
import youtube_dl
from discord import app_commands
from discord.ext import commands


class MusicPlayer:
    """Player de música personalizado para cada servidor"""

    def __init__(self, bot):
        self.bot = bot
        self.voice_client = None
        self.queue = []
        self.current_song = None
        self.is_playing = False
        self.is_paused = False
        self.loop = False
        self.volume = 0.5


class MusicSystem(commands.Cog):
    """Sistema completo de música com fila e controles"""

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.ytdl_format_options = {
            "format": "bestaudio/best",
            "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
            "restrictfilenames": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "logtostderr": False,
            "quiet": True,
            "no_warnings": True,
            "default_search": "auto",
            "source_address": "0.0.0.0",
        }

        self.ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }

        self.ytdl = youtube_dl.YoutubeDL(self.ytdl_format_options)
        self.db_path = os.path.join("src", "data", "music.db")
        self.init_database()

    def init_database(self):
        """Inicializar banco de dados de histórico musical"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS music_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                song_title TEXT NOT NULL,
                song_url TEXT NOT NULL,
                duration TEXT,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS music_settings (
                guild_id TEXT PRIMARY KEY,
                default_volume INTEGER DEFAULT 50,
                auto_leave BOOLEAN DEFAULT 1,
                dj_role_id TEXT,
                max_queue_length INTEGER DEFAULT 50
            )
        """)

        conn.commit()
        conn.close()

    def get_player(self, guild_id):
        """Obter ou criar player para um servidor"""
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(self.bot)
        return self.players[guild_id]

    async def search_youtube(self, query: str):
        """Buscar música no YouTube"""
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, lambda: self.ytdl.extract_info(f"ytsearch:{query}", download=False)
            )

            if data.get("entries"):
                return data["entries"][0]
            return None

        except Exception as e:
            print(f"❌ Erro na busca do YouTube: {e}")
            return None

    @app_commands.command(name="play", description="🎵 Tocar música do YouTube")
    @app_commands.describe(busca="Nome da música ou URL do YouTube")
    async def play(self, interaction: discord.Interaction, busca: str):
        try:
            # Verificar se o usuário está em um canal de voz
            if not interaction.user.voice:
                await interaction.response.send_message(
                    "❌ **Você não está em um canal de voz!**\n"
                    "Entre em um canal de voz para tocar música.",
                    ephemeral=True,
                )
                return

            voice_channel = interaction.user.voice.channel

            # Verificar permissões do bot
            permissions = voice_channel.permissions_for(interaction.guild.me)
            if not permissions.connect or not permissions.speak:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\n"
                    "Preciso de permissão para conectar e falar no canal de voz.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # Buscar música
            song_info = await self.search_youtube(busca)
            if not song_info:
                await interaction.followup.send(
                    "❌ **Música não encontrada!**\nTente uma busca diferente.", ephemeral=True
                )
                return

            player = self.get_player(interaction.guild.id)

            # Conectar ao canal de voz se necessário
            if not player.voice_client or not player.voice_client.is_connected():
                player.voice_client = await voice_channel.connect()

            # Adicionar à fila
            song_data = {
                "title": song_info.get("title", "Título Desconhecido"),
                "url": song_info.get("webpage_url", ""),
                "duration": song_info.get("duration", 0),
                "thumbnail": song_info.get("thumbnail", ""),
                "uploader": song_info.get("uploader", "Canal Desconhecido"),
                "requester": interaction.user,
                "stream_url": song_info.get("url", ""),
            }

            player.queue.append(song_data)

            # Criar embed de confirmação
            embed = discord.Embed(
                title="🎵 **MÚSICA ADICIONADA À FILA**", color=0x00FF00, timestamp=datetime.now()
            )

            embed.add_field(
                name="🎶 Título",
                value=song_data["title"][:100] + ("..." if len(song_data["title"]) > 100 else ""),
                inline=False,
            )

            embed.add_field(
                name="👤 Canal",
                value=song_data["uploader"][:50]
                + ("..." if len(song_data["uploader"]) > 50 else ""),
                inline=True,
            )

            if song_data["duration"]:
                minutes, seconds = divmod(song_data["duration"], 60)
                embed.add_field(name="⏱️ Duração", value=f"{minutes:02d}:{seconds:02d}", inline=True)

            embed.add_field(
                name="📍 Posição na Fila", value=f"**{len(player.queue)}**", inline=True
            )

            embed.add_field(name="🎧 Solicitado por", value=interaction.user.mention, inline=True)

            if song_data["thumbnail"]:
                embed.set_thumbnail(url=song_data["thumbnail"])

            embed.set_footer(
                text="Use /queue para ver a fila completa",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=embed)

            # Iniciar reprodução se não estiver tocando
            if not player.is_playing:
                await self.play_next(player, interaction.guild)

            # Salvar no histórico
            await self.save_to_history(
                interaction.guild.id,
                interaction.user.id,
                song_data["title"],
                song_data["url"],
                f"{minutes:02d}:{seconds:02d}" if song_data["duration"] else "00:00",
            )

        except Exception as e:
            print(f"❌ Erro no comando play: {e}")
            try:
                await interaction.followup.send("❌ Erro ao processar música.", ephemeral=True)
            except:
                pass

    async def play_next(self, player, guild):
        """Tocar próxima música da fila"""
        try:
            if not player.queue:
                player.is_playing = False
                player.current_song = None
                return

            song = player.queue.pop(0)
            player.current_song = song
            player.is_playing = True

            # Criar source de áudio
            source = discord.FFmpegPCMAudio(song["stream_url"], **self.ffmpeg_options)

            source = discord.PCMVolumeTransformer(source, volume=player.volume)

            def after_playing(error):
                if error:
                    print(f"❌ Erro no player: {error}")

                # Agendar próxima música
                coro = self.play_next(player, guild)
                asyncio.create_task(coro)

            player.voice_client.play(source, after=after_playing)

            # Enviar embed "now playing"
            await self.send_now_playing(guild, song)

        except Exception as e:
            print(f"❌ Erro ao tocar música: {e}")
            player.is_playing = False

    async def send_now_playing(self, guild, song):
        """Enviar embed da música atual"""
        try:
            embed = discord.Embed(
                title="🎵 **TOCANDO AGORA**", color=0xFF6B6B, timestamp=datetime.now()
            )

            embed.add_field(
                name="🎶 Música",
                value=song["title"][:100] + ("..." if len(song["title"]) > 100 else ""),
                inline=False,
            )

            embed.add_field(
                name="👤 Canal",
                value=song["uploader"][:50] + ("..." if len(song["uploader"]) > 50 else ""),
                inline=True,
            )

            embed.add_field(name="🎧 Solicitado por", value=song["requester"].mention, inline=True)

            if song["thumbnail"]:
                embed.set_thumbnail(url=song["thumbnail"])

            # Encontrar canal de texto para enviar
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(embed=embed)
                    break

        except Exception as e:
            print(f"❌ Erro ao enviar now playing: {e}")

    async def save_to_history(self, guild_id, user_id, title, url, duration):
        """Salvar música no histórico"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO music_history 
                (guild_id, user_id, song_title, song_url, duration)
                VALUES (?, ?, ?, ?, ?)
            """,
                (str(guild_id), str(user_id), title, url, duration),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao salvar histórico: {e}")

    @app_commands.command(name="stop", description="⏹️ Parar música e limpar fila")
    async def stop(self, interaction: discord.Interaction):
        try:
            player = self.get_player(interaction.guild.id)

            if not player.voice_client or not player.is_playing:
                await interaction.response.send_message(
                    "❌ **Nenhuma música tocando!**", ephemeral=True
                )
                return

            # Parar música e limpar fila
            player.voice_client.stop()
            player.queue.clear()
            player.is_playing = False
            player.current_song = None

            # Desconectar
            await player.voice_client.disconnect()
            player.voice_client = None

            embed = discord.Embed(
                title="⏹️ **MÚSICA PARADA**",
                description="Reprodução parada e fila limpa!",
                color=0xFF0000,
                timestamp=datetime.now(),
            )

            embed.set_footer(
                text=f"Parado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando stop: {e}")
            try:
                await interaction.response.send_message("❌ Erro ao parar música.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="skip", description="⏭️ Pular música atual")
    async def skip(self, interaction: discord.Interaction):
        try:
            player = self.get_player(interaction.guild.id)

            if not player.voice_client or not player.is_playing:
                await interaction.response.send_message(
                    "❌ **Nenhuma música tocando!**", ephemeral=True
                )
                return

            # Pular música
            player.voice_client.stop()  # Isso acionará o callback after_playing

            embed = discord.Embed(
                title="⏭️ **MÚSICA PULADA**",
                description=f"Música **{player.current_song['title'][:50]}{'...' if len(player.current_song['title']) > 50 else ''}** foi pulada!",
                color=0xFFA500,
                timestamp=datetime.now(),
            )

            if player.queue:
                embed.add_field(
                    name="🔄 Próxima",
                    value=f"**{player.queue[0]['title'][:50]}{'...' if len(player.queue[0]['title']) > 50 else ''}**",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="📭 Fila", value="Fila vazia - reprodução será parada.", inline=False
                )

            embed.set_footer(
                text=f"Pulado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando skip: {e}")
            try:
                await interaction.response.send_message("❌ Erro ao pular música.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="queue", description="📋 Ver fila de músicas")
    async def queue(self, interaction: discord.Interaction):
        try:
            player = self.get_player(interaction.guild.id)

            embed = discord.Embed(
                title="📋 **FILA DE MÚSICAS**", color=0x00BFFF, timestamp=datetime.now()
            )

            if player.current_song:
                embed.add_field(
                    name="🎵 Tocando Agora",
                    value=f"**{player.current_song['title'][:60]}{'...' if len(player.current_song['title']) > 60 else ''}**\n"
                    f"Solicitado por {player.current_song['requester'].mention}",
                    inline=False,
                )

            if player.queue:
                queue_text = ""
                for i, song in enumerate(player.queue[:10]):  # Mostrar apenas 10
                    queue_text += f"**{i + 1}.** {song['title'][:40]}{'...' if len(song['title']) > 40 else ''}\n"
                    queue_text += f"      *Solicitado por {song['requester'].display_name}*\n\n"

                embed.add_field(
                    name=f"📍 Próximas ({len(player.queue)} na fila)",
                    value=queue_text[:1000] + ("..." if len(queue_text) > 1000 else ""),
                    inline=False,
                )

                if len(player.queue) > 10:
                    embed.add_field(
                        name="➕ E mais...",
                        value=f"**{len(player.queue) - 10}** músicas adicionais na fila",
                        inline=False,
                    )
            else:
                embed.add_field(
                    name="📭 Fila Vazia", value="Use `/play` para adicionar músicas!", inline=False
                )

            embed.set_footer(
                text=f"Solicitado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando queue: {e}")
            try:
                await interaction.response.send_message("❌ Erro ao mostrar fila.", ephemeral=True)
            except:
                pass


async def setup(bot):
    await bot.add_cog(MusicSystem(bot))
