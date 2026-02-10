"""
Sistema de Controles de Voz Avançado
Gerenciamento completo de usuários em canais de voz
"""

import os
import sqlite3
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class VoiceSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.join("src", "data", "voice.db")
        self.init_database()

    def init_database(self):
        """Inicializar banco de dados de ações de voz"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voice_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                moderator_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                channel_id TEXT,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voice_settings (
                guild_id TEXT PRIMARY KEY,
                log_voice_actions BOOLEAN DEFAULT 1,
                auto_move_timeout INTEGER DEFAULT 300,
                max_voice_actions_per_hour INTEGER DEFAULT 20
            )
        """)

        conn.commit()
        conn.close()

    async def log_voice_action(
        self,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        action_type: str,
        channel_id: int = None,
        reason: str = None,
    ):
        """Registrar ação de voz no banco de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO voice_actions 
                (guild_id, user_id, moderator_id, action_type, channel_id, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    str(guild_id),
                    str(user_id),
                    str(moderator_id),
                    action_type,
                    str(channel_id) if channel_id else None,
                    reason,
                ),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao registrar ação de voz: {e}")

    @app_commands.command(name="voice-mute", description="🔇 Mutar usuário no chat de voz")
    @app_commands.describe(user="Usuário para mutar no voice", motivo="Motivo da ação")
    @app_commands.default_permissions(mute_members=True)
    async def voice_mute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str | None = "Não especificado",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.mute_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para mutar membros em voz.",
                    ephemeral=True,
                )
                return

            # Verificar se está em canal de voz
            if not user.voice or not user.voice.channel:
                await interaction.response.send_message(
                    "❌ **Usuário Não Conectado**\nO usuário não está em um canal de voz.",
                    ephemeral=True,
                )
                return

            # Verificar hierarquia
            if user.top_role >= interaction.user.top_role:
                await interaction.response.send_message(
                    "❌ **Hierarquia Insuficiente**\n"
                    "Você não pode mutar alguém com cargo igual ou superior ao seu.",
                    ephemeral=True,
                )
                return

            # Verificar se já está mutado
            if user.voice.mute or user.voice.self_mute:
                await interaction.response.send_message(
                    f"❌ **Usuário Já Mutado**\n{user.mention} já está mutado no voice.",
                    ephemeral=True,
                )
                return

            # Mutar usuário
            await user.edit(mute=True, reason=f"{motivo} - Por: {interaction.user}")

            # Registrar ação
            await self.log_voice_action(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                "mute",
                user.voice.channel.id,
                motivo,
            )

            # Criar embed
            embed = discord.Embed(
                title="🔇 **USUÁRIO MUTADO NO VOICE**", color=0xFF6600, timestamp=datetime.now()
            )

            embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)

            embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            embed.add_field(name="🎧 Canal", value=f"{user.voice.channel.mention}", inline=True)

            embed.add_field(
                name="📝 Motivo",
                value=motivo[:200] + ("..." if len(motivo) > 200 else ""),
                inline=False,
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.set_footer(
                text="Mute aplicado com sucesso", icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ **Erro de Permissão**\nNão tenho permissão para mutar este usuário.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Erro no comando voice-mute: {e}")
            try:
                await interaction.response.send_message("❌ Erro ao mutar usuário.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="voice-unmute", description="🔊 Desmutar usuário no chat de voz")
    @app_commands.describe(user="Usuário para desmutar no voice", motivo="Motivo da ação")
    @app_commands.default_permissions(mute_members=True)
    async def voice_unmute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str | None = "Mute removido",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.mute_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para gerenciar mutes em voz.",
                    ephemeral=True,
                )
                return

            # Verificar se está em canal de voz
            if not user.voice or not user.voice.channel:
                await interaction.response.send_message(
                    "❌ **Usuário Não Conectado**\nO usuário não está em um canal de voz.",
                    ephemeral=True,
                )
                return

            # Verificar se está mutado
            if not user.voice.mute:
                await interaction.response.send_message(
                    f"❌ **Usuário Não Mutado**\n{user.mention} não está mutado no voice.",
                    ephemeral=True,
                )
                return

            # Desmutar usuário
            await user.edit(mute=False, reason=f"{motivo} - Por: {interaction.user}")

            # Registrar ação
            await self.log_voice_action(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                "unmute",
                user.voice.channel.id,
                motivo,
            )

            # Criar embed
            embed = discord.Embed(
                title="🔊 **USUÁRIO DESMUTADO NO VOICE**", color=0x00FF00, timestamp=datetime.now()
            )

            embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)

            embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            embed.add_field(name="🎧 Canal", value=f"{user.voice.channel.mention}", inline=True)

            embed.add_field(
                name="📝 Motivo",
                value=motivo[:200] + ("..." if len(motivo) > 200 else ""),
                inline=False,
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.set_footer(
                text="Mute removido com sucesso", icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ **Erro de Permissão**\nNão tenho permissão para desmutar este usuário.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Erro no comando voice-unmute: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao desmutar usuário.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="voice-deafen", description="🔇 Ensurdecer usuário no chat de voz")
    @app_commands.describe(user="Usuário para ensurdecer", motivo="Motivo da ação")
    @app_commands.default_permissions(deafen_members=True)
    async def voice_deafen(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str | None = "Não especificado",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.deafen_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para ensurdecer membros.",
                    ephemeral=True,
                )
                return

            # Verificar se está em canal de voz
            if not user.voice or not user.voice.channel:
                await interaction.response.send_message(
                    "❌ **Usuário Não Conectado**\nO usuário não está em um canal de voz.",
                    ephemeral=True,
                )
                return

            # Verificar hierarquia
            if user.top_role >= interaction.user.top_role:
                await interaction.response.send_message(
                    "❌ **Hierarquia Insuficiente**\n"
                    "Você não pode ensurdecer alguém com cargo igual ou superior ao seu.",
                    ephemeral=True,
                )
                return

            # Verificar se já está ensurdecido
            if user.voice.deaf or user.voice.self_deaf:
                await interaction.response.send_message(
                    f"❌ **Usuário Já Ensurdecido**\n{user.mention} já está ensurdecido.",
                    ephemeral=True,
                )
                return

            # Ensurdecer usuário (e mutar também)
            await user.edit(deafen=True, mute=True, reason=f"{motivo} - Por: {interaction.user}")

            # Registrar ação
            await self.log_voice_action(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                "deafen",
                user.voice.channel.id,
                motivo,
            )

            # Criar embed
            embed = discord.Embed(
                title="🔇 **USUÁRIO ENSURDECIDO**",
                description="O usuário foi ensurdecido e mutado no canal de voz",
                color=0xFF0000,
                timestamp=datetime.now(),
            )

            embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)

            embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            embed.add_field(name="🎧 Canal", value=f"{user.voice.channel.mention}", inline=True)

            embed.add_field(
                name="⚠️ Efeitos",
                value="• Não pode falar\n• Não pode ouvir\n• Isolado completamente",
                inline=True,
            )

            embed.add_field(
                name="📝 Motivo",
                value=motivo[:200] + ("..." if len(motivo) > 200 else ""),
                inline=False,
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.set_footer(
                text="Ação aplicada com sucesso", icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ **Erro de Permissão**\nNão tenho permissão para ensurdecer este usuário.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Erro no comando voice-deafen: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao ensurdecer usuário.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="voice-undeafen", description="🔊 Remover surdez do usuário")
    @app_commands.describe(user="Usuário para remover surdez", motivo="Motivo da ação")
    @app_commands.default_permissions(deafen_members=True)
    async def voice_undeafen(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str | None = "Surdez removida",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.deafen_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para gerenciar surdez.",
                    ephemeral=True,
                )
                return

            # Verificar se está em canal de voz
            if not user.voice or not user.voice.channel:
                await interaction.response.send_message(
                    "❌ **Usuário Não Conectado**\nO usuário não está em um canal de voz.",
                    ephemeral=True,
                )
                return

            # Verificar se está ensurdecido
            if not user.voice.deaf:
                await interaction.response.send_message(
                    f"❌ **Usuário Não Ensurdecido**\n{user.mention} não está ensurdecido.",
                    ephemeral=True,
                )
                return

            # Remover surdez (e mute se foi aplicado junto)
            await user.edit(deafen=False, mute=False, reason=f"{motivo} - Por: {interaction.user}")

            # Registrar ação
            await self.log_voice_action(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                "undeafen",
                user.voice.channel.id,
                motivo,
            )

            # Criar embed
            embed = discord.Embed(
                title="🔊 **SURDEZ REMOVIDA**",
                description="O usuário pode novamente ouvir e falar no canal de voz",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)

            embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            embed.add_field(name="🎧 Canal", value=f"{user.voice.channel.mention}", inline=True)

            embed.add_field(
                name="📝 Motivo",
                value=motivo[:200] + ("..." if len(motivo) > 200 else ""),
                inline=False,
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.set_footer(
                text="Surdez removida com sucesso", icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ **Erro de Permissão**\nNão tenho permissão para remover surdez deste usuário.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Erro no comando voice-undeafen: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao remover surdez.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="voice-move", description="🔄 Mover usuário para outro canal de voz")
    @app_commands.describe(
        user="Usuário para mover", canal="Canal de destino", motivo="Motivo da ação"
    )
    @app_commands.default_permissions(move_members=True)
    async def voice_move(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        canal: discord.VoiceChannel,
        motivo: str | None = "Movido por moderador",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.move_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para mover membros.",
                    ephemeral=True,
                )
                return

            # Verificar se está em canal de voz
            if not user.voice or not user.voice.channel:
                await interaction.response.send_message(
                    "❌ **Usuário Não Conectado**\nO usuário não está em um canal de voz.",
                    ephemeral=True,
                )
                return

            # Verificar se já está no canal de destino
            if user.voice.channel.id == canal.id:
                await interaction.response.send_message(
                    f"❌ **Mesmo Canal**\n{user.mention} já está em {canal.mention}.",
                    ephemeral=True,
                )
                return

            canal_origem = user.voice.channel

            # Mover usuário
            await user.move_to(canal, reason=f"{motivo} - Por: {interaction.user}")

            # Registrar ação
            await self.log_voice_action(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                "move",
                canal.id,
                f"De {canal_origem.name} para {canal.name}: {motivo}",
            )

            # Criar embed
            embed = discord.Embed(
                title="🔄 **USUÁRIO MOVIDO**", color=0x00BFFF, timestamp=datetime.now()
            )

            embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)

            embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            embed.add_field(
                name="🔄 Movimento",
                value=f"**De:** {canal_origem.mention}\n**Para:** {canal.mention}",
                inline=False,
            )

            embed.add_field(
                name="📝 Motivo",
                value=motivo[:200] + ("..." if len(motivo) > 200 else ""),
                inline=False,
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.set_footer(
                text="Usuário movido com sucesso", icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ **Erro de Permissão**\n"
                "Não tenho permissão para mover este usuário ou acessar o canal de destino.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Erro no comando voice-move: {e}")
            try:
                await interaction.response.send_message("❌ Erro ao mover usuário.", ephemeral=True)
            except:
                pass

    @app_commands.command(
        name="voice-disconnect", description="📤 Desconectar usuário do chat de voz"
    )
    @app_commands.describe(user="Usuário para desconectar", motivo="Motivo da ação")
    @app_commands.default_permissions(move_members=True)
    async def voice_disconnect(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str | None = "Desconectado por moderador",
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.move_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para desconectar membros.",
                    ephemeral=True,
                )
                return

            # Verificar se está em canal de voz
            if not user.voice or not user.voice.channel:
                await interaction.response.send_message(
                    "❌ **Usuário Não Conectado**\nO usuário não está em um canal de voz.",
                    ephemeral=True,
                )
                return

            # Verificar hierarquia
            if user.top_role >= interaction.user.top_role:
                await interaction.response.send_message(
                    "❌ **Hierarquia Insuficiente**\n"
                    "Você não pode desconectar alguém com cargo igual ou superior ao seu.",
                    ephemeral=True,
                )
                return

            canal_origem = user.voice.channel

            # Desconectar usuário
            await user.move_to(None, reason=f"{motivo} - Por: {interaction.user}")

            # Registrar ação
            await self.log_voice_action(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                "disconnect",
                canal_origem.id,
                motivo,
            )

            # Criar embed
            embed = discord.Embed(
                title="📤 **USUÁRIO DESCONECTADO**", color=0xFF3300, timestamp=datetime.now()
            )

            embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)

            embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            embed.add_field(name="🎧 Canal Anterior", value=f"{canal_origem.mention}", inline=True)

            embed.add_field(
                name="📝 Motivo",
                value=motivo[:200] + ("..." if len(motivo) > 200 else ""),
                inline=False,
            )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.set_footer(
                text="Usuário desconectado com sucesso",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ **Erro de Permissão**\nNão tenho permissão para desconectar este usuário.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Erro no comando voice-disconnect: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao desconectar usuário.", ephemeral=True
                )
            except:
                pass


async def setup(bot):
    await bot.add_cog(VoiceSystem(bot))
