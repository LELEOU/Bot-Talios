"""
Sticky Message Handler - Gerencia mensagens fixas
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class StickyMessageHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sticky_cache = {}  # Cache de mensagens sticky por canal

    @commands.Cog.listener()
    async def on_message(self, message):
        """Repostar mensagem sticky quando alguém fala no canal"""
        if message.author.bot:
            return

        try:
            channel_id = message.channel.id

            # Verificar se canal tem sticky message
            sticky_config = await self.get_sticky_config(channel_id)
            if not sticky_config:
                return

            # Verificar se deve repostar
            if await self.should_repost_sticky(channel_id, sticky_config):
                await self.repost_sticky_message(message.channel, sticky_config)

        except Exception as e:
            print(f"❌ Erro no sticky message handler: {e}")

    async def get_sticky_config(self, channel_id: int) -> dict:
        """Buscar configuração de sticky message do canal"""
        try:
            # Verificar cache primeiro
            if channel_id in self.sticky_cache:
                return self.sticky_cache[channel_id]

            result = await database.fetchone(
                "SELECT * FROM sticky_messages WHERE channel_id = ? AND enabled = 1",
                (str(channel_id),),
            )

            if result:
                config = {
                    "id": result["id"],
                    "channel_id": result["channel_id"],
                    "content": result["content"],
                    "embed_data": result.get("embed_data"),
                    "last_message_id": result.get("last_message_id"),
                    "message_threshold": result.get("message_threshold", 5),
                    "time_threshold": result.get("time_threshold", 300),  # 5 minutos
                    "last_posted": result.get("last_posted"),
                }

                # Atualizar cache
                self.sticky_cache[channel_id] = config
                return config

            return None

        except Exception as e:
            print(f"❌ Erro buscando sticky config: {e}")
            return None

    async def should_repost_sticky(self, channel_id: int, config: dict) -> bool:
        """Verificar se deve repostar mensagem sticky"""
        try:
            # Verificar se já existe mensagem sticky ativa
            last_message_id = config.get("last_message_id")
            if last_message_id:
                try:
                    channel = self.bot.get_channel(channel_id)
                    last_message = await channel.fetch_message(int(last_message_id))

                    # Se mensagem ainda existe e está próxima do final, não repostar
                    recent_messages = [msg async for msg in channel.history(limit=5)]
                    if last_message in recent_messages:
                        return False

                except discord.NotFound:
                    # Mensagem foi deletada, pode repostar
                    pass

            # Verificar threshold de mensagens
            threshold = config.get("message_threshold", 5)
            if last_message_id:
                try:
                    channel = self.bot.get_channel(channel_id)
                    messages_since = []
                    async for msg in channel.history(limit=50):
                        if msg.id == int(last_message_id):
                            break
                        if not msg.author.bot:  # Contar apenas mensagens de usuários
                            messages_since.append(msg)

                    if len(messages_since) < threshold:
                        return False

                except:
                    pass

            return True

        except Exception as e:
            print(f"❌ Erro verificando repost sticky: {e}")
            return False

    async def repost_sticky_message(self, channel: discord.TextChannel, config: dict):
        """Repostar mensagem sticky"""
        try:
            # Deletar mensagem anterior se existir
            last_message_id = config.get("last_message_id")
            if last_message_id:
                try:
                    old_message = await channel.fetch_message(int(last_message_id))
                    await old_message.delete()
                except:
                    pass  # Mensagem já foi deletada ou não existe

            # Preparar conteúdo da mensagem
            content = config.get("content", "")
            embed = None

            # Processar embed se houver
            embed_data = config.get("embed_data")
            if embed_data:
                try:
                    import json

                    embed_dict = json.loads(embed_data)
                    embed = discord.Embed.from_dict(embed_dict)
                except:
                    pass

            # Enviar nova mensagem sticky
            if content or embed:
                new_message = await channel.send(content=content or None, embed=embed)

                # Atualizar ID da mensagem no banco
                await database.run(
                    "UPDATE sticky_messages SET last_message_id = ?, last_posted = ? WHERE id = ?",
                    (str(new_message.id), discord.utils.utcnow().isoformat(), config["id"]),
                )

                # Atualizar cache
                config["last_message_id"] = str(new_message.id)
                config["last_posted"] = discord.utils.utcnow().isoformat()
                self.sticky_cache[channel.id] = config

        except Exception as e:
            print(f"❌ Erro repostando sticky message: {e}")

    async def create_sticky_message(
        self,
        channel_id: int,
        content: str = None,
        embed: discord.Embed = None,
        message_threshold: int = 5,
    ) -> bool:
        """Criar nova mensagem sticky"""
        try:
            # Preparar dados do embed
            embed_data = None
            if embed:
                embed_data = embed.to_dict()
                import json

                embed_data = json.dumps(embed_data)

            # Inserir no banco
            await database.run(
                """INSERT OR REPLACE INTO sticky_messages 
                   (channel_id, content, embed_data, message_threshold, enabled, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(channel_id),
                    content,
                    embed_data,
                    message_threshold,
                    1,
                    discord.utils.utcnow().isoformat(),
                ),
            )

            # Limpar cache
            if channel_id in self.sticky_cache:
                del self.sticky_cache[channel_id]

            # Postar mensagem inicial
            channel = self.bot.get_channel(channel_id)
            if channel:
                new_config = await self.get_sticky_config(channel_id)
                if new_config:
                    await self.repost_sticky_message(channel, new_config)

            return True

        except Exception as e:
            print(f"❌ Erro criando sticky message: {e}")
            return False

    async def remove_sticky_message(self, channel_id: int) -> bool:
        """Remover mensagem sticky do canal"""
        try:
            # Buscar configuração atual
            config = await self.get_sticky_config(channel_id)

            # Deletar mensagem ativa se houver
            if config and config.get("last_message_id"):
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        message = await channel.fetch_message(int(config["last_message_id"]))
                        await message.delete()
                except:
                    pass

            # Remover do banco
            await database.run(
                "DELETE FROM sticky_messages WHERE channel_id = ?", (str(channel_id),)
            )

            # Limpar cache
            if channel_id in self.sticky_cache:
                del self.sticky_cache[channel_id]

            return True

        except Exception as e:
            print(f"❌ Erro removendo sticky message: {e}")
            return False

    async def update_sticky_message(
        self, channel_id: int, content: str = None, embed: discord.Embed = None
    ) -> bool:
        """Atualizar conteúdo de mensagem sticky"""
        try:
            # Preparar dados do embed
            embed_data = None
            if embed:
                embed_data = embed.to_dict()
                import json

                embed_data = json.dumps(embed_data)

            # Atualizar no banco
            await database.run(
                "UPDATE sticky_messages SET content = ?, embed_data = ? WHERE channel_id = ?",
                (content, embed_data, str(channel_id)),
            )

            # Limpar cache para forçar reload
            if channel_id in self.sticky_cache:
                del self.sticky_cache[channel_id]

            # Repostar com novo conteúdo
            channel = self.bot.get_channel(channel_id)
            if channel:
                new_config = await self.get_sticky_config(channel_id)
                if new_config:
                    await self.repost_sticky_message(channel, new_config)

            return True

        except Exception as e:
            print(f"❌ Erro atualizando sticky message: {e}")
            return False


async def setup(bot):
    await bot.add_cog(StickyMessageHandler(bot))
