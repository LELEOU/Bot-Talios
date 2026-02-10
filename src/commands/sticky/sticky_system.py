"""
Sistema de Mensagens Sticky Avançado
Mensagens que permanecem fixas nos canais com repostagem automática
"""

import json
import os
import sqlite3
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class StickySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.join("src", "data", "sticky.db")
        self.sticky_cache = {}  # Cache das mensagens sticky ativas
        self.message_counters = {}  # Contador de mensagens por canal
        self.init_database()

        # Carregar configurações na inicialização (será chamado manualmente)
        # self.bot.loop.create_task(self.load_sticky_cache())

    def init_database(self):
        """Inicializar banco de dados de sticky messages"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sticky_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message_content TEXT NOT NULL,
                embed_data TEXT,
                frequency INTEGER DEFAULT 5,
                last_message_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, channel_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sticky_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                reposts_count INTEGER DEFAULT 0,
                last_repost TIMESTAMP,
                total_views INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    async def load_sticky_cache(self):
        """Carregar configurações sticky no cache"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT guild_id, channel_id, message_content, embed_data, frequency, last_message_id
                FROM sticky_messages 
                WHERE is_active = 1
            """)

            results = cursor.fetchall()
            conn.close()

            for guild_id, channel_id, content, embed_data, frequency, last_msg_id in results:
                key = f"{guild_id}_{channel_id}"
                self.sticky_cache[key] = {
                    "content": content,
                    "embed_data": json.loads(embed_data) if embed_data else None,
                    "frequency": frequency,
                    "last_message_id": last_msg_id,
                }
                self.message_counters[key] = 0

            print(f"✅ Carregadas {len(results)} mensagens sticky")
        except Exception as e:
            print(f"❌ Erro ao carregar sticky cache: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitorar mensagens para repostar sticky quando necessário"""
        if message.author.bot:
            return

        if not message.guild:
            return

        key = f"{message.guild.id}_{message.channel.id}"

        if key not in self.sticky_cache:
            return

        # Incrementar contador
        self.message_counters[key] = self.message_counters.get(key, 0) + 1

        # Verificar se deve repostar
        sticky_data = self.sticky_cache[key]
        if self.message_counters[key] >= sticky_data["frequency"]:
            await self.repost_sticky(message.channel, key)

    async def repost_sticky(self, channel, key):
        """Repostar mensagem sticky"""
        try:
            sticky_data = self.sticky_cache[key]

            # Deletar mensagem sticky anterior
            if sticky_data.get("last_message_id"):
                try:
                    old_message = await channel.fetch_message(sticky_data["last_message_id"])
                    await old_message.delete()
                except:
                    pass

            # Criar nova mensagem
            if sticky_data.get("embed_data"):
                embed_data = sticky_data["embed_data"]
                embed = discord.Embed.from_dict(embed_data)
                new_message = await channel.send(
                    content=sticky_data["content"] or None, embed=embed
                )
            else:
                new_message = await channel.send(sticky_data["content"])

            # Atualizar ID da mensagem no cache e banco
            sticky_data["last_message_id"] = str(new_message.id)
            self.message_counters[key] = 0

            # Atualizar banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            guild_id, channel_id = key.split("_")
            cursor.execute(
                """
                UPDATE sticky_messages 
                SET last_message_id = ?, updated_at = ?
                WHERE guild_id = ? AND channel_id = ?
            """,
                (str(new_message.id), datetime.now(), guild_id, channel_id),
            )

            # Atualizar estatísticas
            cursor.execute(
                """
                INSERT OR REPLACE INTO sticky_stats 
                (guild_id, channel_id, reposts_count, last_repost)
                VALUES (?, ?, COALESCE((SELECT reposts_count FROM sticky_stats WHERE guild_id = ? AND channel_id = ?), 0) + 1, ?)
            """,
                (guild_id, channel_id, guild_id, channel_id, datetime.now()),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao repostar sticky: {e}")

    @app_commands.command(name="sticky", description="📌 Configurar mensagem sticky")
    @app_commands.describe(
        acao="Ação a executar",
        mensagem="Conteúdo da mensagem sticky",
        canal="Canal para a mensagem (padrão: atual)",
        frequencia="Número de mensagens antes de repostar (1-50)",
    )
    @app_commands.choices(
        acao=[
            app_commands.Choice(name="Criar/Atualizar", value="set"),
            app_commands.Choice(name="Remover", value="remove"),
            app_commands.Choice(name="Ver Status", value="view"),
            app_commands.Choice(name="Repostar Agora", value="repost"),
        ]
    )
    @app_commands.default_permissions(manage_messages=True)
    async def sticky_command(
        self,
        interaction: discord.Interaction,
        acao: str,
        mensagem: str | None = None,
        canal: discord.TextChannel | None = None,
        frequencia: int | None = 5,
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\n"
                    "Você não tem permissão para gerenciar mensagens sticky.",
                    ephemeral=True,
                )
                return

            if canal is None:
                canal = interaction.channel

            # Verificar permissões do bot no canal
            permissions = canal.permissions_for(interaction.guild.me)
            if not permissions.send_messages or not permissions.manage_messages:
                await interaction.response.send_message(
                    "❌ **Sem Permissões no Canal**\n"
                    "Preciso de permissões para enviar e gerenciar mensagens neste canal.",
                    ephemeral=True,
                )
                return

            key = f"{interaction.guild.id}_{canal.id}"

            if acao == "view":
                await self.show_sticky_status(interaction, canal, key)
                return

            if acao == "remove":
                await self.remove_sticky(interaction, canal, key)
                return

            if acao == "repost":
                await self.manual_repost(interaction, canal, key)
                return

            if acao == "set":
                if not mensagem:
                    await interaction.response.send_message(
                        "❌ **Mensagem Necessária**\n"
                        "Você deve fornecer o conteúdo da mensagem sticky.",
                        ephemeral=True,
                    )
                    return

                await self.set_sticky(interaction, canal, mensagem, frequencia, key)
                return

        except Exception as e:
            print(f"❌ Erro no comando sticky: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao processar comando sticky.", ephemeral=True
                )
            except:
                pass

    async def show_sticky_status(self, interaction, canal, key):
        """Mostrar status da mensagem sticky"""
        try:
            if key not in self.sticky_cache:
                await interaction.response.send_message(
                    f"❌ **Sticky Não Configurado**\n"
                    f"Nenhuma mensagem sticky configurada para {canal.mention}.",
                    ephemeral=True,
                )
                return

            sticky_data = self.sticky_cache[key]

            # Buscar estatísticas
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT reposts_count, last_repost, total_views
                FROM sticky_stats 
                WHERE guild_id = ? AND channel_id = ?
            """,
                (str(interaction.guild.id), str(canal.id)),
            )

            stats = cursor.fetchone()
            conn.close()

            embed = discord.Embed(
                title="📌 **STATUS MENSAGEM STICKY**", color=0x00BFFF, timestamp=datetime.now()
            )

            embed.add_field(name="📢 Canal", value=f"{canal.mention}", inline=True)

            embed.add_field(
                name="🔄 Frequência",
                value=f"A cada **{sticky_data['frequency']}** mensagens",
                inline=True,
            )

            embed.add_field(
                name="📊 Contador Atual",
                value=f"**{self.message_counters.get(key, 0)}** / {sticky_data['frequency']}",
                inline=True,
            )

            if stats:
                reposts, last_repost, views = stats
                embed.add_field(name="📈 Reposts Totais", value=f"**{reposts or 0}**", inline=True)

                if last_repost:
                    last_repost_timestamp = int(datetime.fromisoformat(last_repost).timestamp())
                    embed.add_field(
                        name="🕒 Último Repost", value=f"<t:{last_repost_timestamp}:R>", inline=True
                    )

            # Prévia da mensagem
            content_preview = sticky_data["content"][:200] + (
                "..." if len(sticky_data["content"]) > 200 else ""
            )
            embed.add_field(
                name="💬 Prévia da Mensagem", value=f"```{content_preview}```", inline=False
            )

            # Status da última mensagem
            if sticky_data.get("last_message_id"):
                try:
                    await canal.fetch_message(sticky_data["last_message_id"])
                    status = "✅ Mensagem ativa no canal"
                except:
                    status = "⚠️ Mensagem não encontrada (pode ter sido deletada)"

                embed.add_field(name="🔍 Status", value=status, inline=False)

            embed.set_footer(
                text="Configurado • Use /sticky acao:repost para repostar agora",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro ao mostrar status sticky: {e}")
            await interaction.response.send_message("❌ Erro ao buscar status.", ephemeral=True)

    async def remove_sticky(self, interaction, canal, key):
        """Remover mensagem sticky"""
        try:
            if key not in self.sticky_cache:
                await interaction.response.send_message(
                    f"❌ **Sticky Não Configurado**\n"
                    f"Nenhuma mensagem sticky configurada para {canal.mention}.",
                    ephemeral=True,
                )
                return

            # Remover mensagem atual se existir
            sticky_data = self.sticky_cache[key]
            if sticky_data.get("last_message_id"):
                try:
                    message = await canal.fetch_message(sticky_data["last_message_id"])
                    await message.delete()
                except:
                    pass

            # Remover do cache
            del self.sticky_cache[key]
            if key in self.message_counters:
                del self.message_counters[key]

            # Remover do banco
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE sticky_messages 
                SET is_active = 0, updated_at = ?
                WHERE guild_id = ? AND channel_id = ?
            """,
                (datetime.now(), str(interaction.guild.id), str(canal.id)),
            )

            conn.commit()
            conn.close()

            embed = discord.Embed(
                title="🗑️ **STICKY REMOVIDO**",
                description=f"Mensagem sticky removida de {canal.mention} com sucesso!",
                color=0xFF6600,
                timestamp=datetime.now(),
            )

            embed.set_footer(
                text=f"Removido por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro ao remover sticky: {e}")
            await interaction.response.send_message("❌ Erro ao remover sticky.", ephemeral=True)

    async def manual_repost(self, interaction, canal, key):
        """Repostar mensagem sticky manualmente"""
        try:
            if key not in self.sticky_cache:
                await interaction.response.send_message(
                    f"❌ **Sticky Não Configurado**\n"
                    f"Nenhuma mensagem sticky configurada para {canal.mention}.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Repostar sticky
            await self.repost_sticky(canal, key)

            embed = discord.Embed(
                title="🔄 **STICKY REPOSTADO**",
                description=f"Mensagem sticky repostada em {canal.mention}!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            embed.set_footer(
                text=f"Repostado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro ao repostar sticky: {e}")
            await interaction.followup.send("❌ Erro ao repostar sticky.", ephemeral=True)

    async def set_sticky(self, interaction, canal, mensagem, frequencia, key):
        """Configurar nova mensagem sticky"""
        try:
            # Validar frequência
            if frequencia < 1 or frequencia > 50:
                await interaction.response.send_message(
                    "❌ **Frequência Inválida**\nA frequência deve ser entre 1 e 50 mensagens.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # Remover mensagem anterior se existir
            if key in self.sticky_cache:
                old_data = self.sticky_cache[key]
                if old_data.get("last_message_id"):
                    try:
                        old_message = await canal.fetch_message(old_data["last_message_id"])
                        await old_message.delete()
                    except:
                        pass

            # Postar primeira vez
            new_message = await canal.send(mensagem)

            # Salvar no banco
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO sticky_messages 
                (guild_id, channel_id, message_content, frequency, last_message_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    str(interaction.guild.id),
                    str(canal.id),
                    mensagem,
                    frequencia,
                    str(new_message.id),
                    datetime.now(),
                ),
            )

            conn.commit()
            conn.close()

            # Atualizar cache
            self.sticky_cache[key] = {
                "content": mensagem,
                "embed_data": None,
                "frequency": frequencia,
                "last_message_id": str(new_message.id),
            }
            self.message_counters[key] = 0

            # Embed de confirmação
            embed = discord.Embed(
                title="📌 **STICKY CONFIGURADO**", color=0x00FF00, timestamp=datetime.now()
            )

            embed.add_field(name="📢 Canal", value=f"{canal.mention}", inline=True)

            embed.add_field(
                name="🔄 Frequência", value=f"A cada **{frequencia}** mensagens", inline=True
            )

            embed.add_field(
                name="📝 Conteúdo",
                value=mensagem[:500] + ("..." if len(mensagem) > 500 else ""),
                inline=False,
            )

            embed.add_field(
                name="ℹ️ Informação",
                value="A mensagem será repostada automaticamente quando atingir a frequência configurada.",
                inline=False,
            )

            embed.set_footer(
                text=f"Configurado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro ao configurar sticky: {e}")
            try:
                await interaction.followup.send("❌ Erro ao configurar sticky.", ephemeral=True)
            except:
                pass


async def setup(bot):
    await bot.add_cog(StickySystem(bot))
