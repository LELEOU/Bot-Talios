"""
Sticky Messages Poster - Sistema automático de postagem de mensagens fixas
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands, tasks

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class StickyMessagesPoster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.post_scheduled_stickies.start()

    def cog_unload(self):
        self.post_scheduled_stickies.cancel()

    @tasks.loop(minutes=5)  # Verificar a cada 5 minutos
    async def post_scheduled_stickies(self):
        """Postar mensagens sticky agendadas"""
        try:
            # Buscar sticky messages que precisam ser repostadas
            stickies_to_post = await database.fetchall(
                """SELECT * FROM sticky_messages 
                   WHERE enabled = 1 AND auto_repost = 1 
                   AND (last_posted IS NULL OR 
                        datetime(last_posted) <= datetime('now', '-' || repost_interval || ' minutes'))"""
            )

            for sticky in stickies_to_post:
                await self.auto_repost_sticky(sticky)

        except Exception as e:
            print(f"❌ Erro postando stickies agendadas: {e}")

    @post_scheduled_stickies.before_loop
    async def before_post_scheduled_stickies(self):
        await self.bot.wait_until_ready()

    async def auto_repost_sticky(self, sticky_data):
        """Repostar mensagem sticky automaticamente"""
        try:
            channel = self.bot.get_channel(int(sticky_data["channel_id"]))
            if not channel:
                # Canal não existe mais, desabilitar sticky
                await database.run(
                    "UPDATE sticky_messages SET enabled = 0 WHERE id = ?", (sticky_data["id"],)
                )
                return

            # Verificar se precisa repostar baseado na atividade do canal
            should_repost = await self.should_auto_repost(channel, sticky_data)

            if not should_repost:
                return

            # Deletar mensagem anterior se existir
            if sticky_data.get("last_message_id"):
                try:
                    old_message = await channel.fetch_message(int(sticky_data["last_message_id"]))
                    await old_message.delete()
                except:
                    pass

            # Preparar conteúdo
            content = sticky_data.get("content", "")
            embed = None

            # Processar embed se houver
            if sticky_data.get("embed_data"):
                try:
                    import json

                    embed_dict = json.loads(sticky_data["embed_data"])
                    embed = discord.Embed.from_dict(embed_dict)
                except:
                    pass

            # Postar nova mensagem
            if content or embed:
                new_message = await channel.send(content=content or None, embed=embed)

                # Atualizar informações
                await database.run(
                    "UPDATE sticky_messages SET last_message_id = ?, last_posted = ? WHERE id = ?",
                    (str(new_message.id), discord.utils.utcnow().isoformat(), sticky_data["id"]),
                )

                print(f"📌 Sticky repostada automaticamente em #{channel.name}")

        except Exception as e:
            print(f"❌ Erro repostando sticky automaticamente: {e}")

    async def should_auto_repost(self, channel, sticky_data) -> bool:
        """Verificar se deve repostar automaticamente"""
        try:
            # Verificar se há atividade suficiente no canal
            min_messages = sticky_data.get("min_messages_to_repost", 10)

            if sticky_data.get("last_posted"):
                # Contar mensagens desde a última postagem
                last_posted = discord.utils.parse_time(sticky_data["last_posted"])

                message_count = 0
                async for message in channel.history(after=last_posted, limit=50):
                    if not message.author.bot:
                        message_count += 1

                return message_count >= min_messages

            return True  # Primeira vez, pode postar

        except Exception as e:
            print(f"❌ Erro verificando repost automático: {e}")
            return False

    async def schedule_sticky_repost(self, channel_id: int, interval_minutes: int = 60):
        """Agendar repostagem automática de sticky"""
        try:
            await database.run(
                "UPDATE sticky_messages SET auto_repost = 1, repost_interval = ? WHERE channel_id = ?",
                (interval_minutes, str(channel_id)),
            )

            return True

        except Exception as e:
            print(f"❌ Erro agendando repost de sticky: {e}")
            return False

    async def disable_auto_repost(self, channel_id: int):
        """Desabilitar repostagem automática"""
        try:
            await database.run(
                "UPDATE sticky_messages SET auto_repost = 0 WHERE channel_id = ?",
                (str(channel_id),),
            )

            return True

        except Exception as e:
            print(f"❌ Erro desabilitando auto repost: {e}")
            return False

    async def force_repost_all_stickies(self, guild_id: int = None):
        """Forçar repostagem de todas as stickies"""
        try:
            query = "SELECT * FROM sticky_messages WHERE enabled = 1"
            params = ()

            if guild_id:
                # Buscar apenas do servidor específico
                channels = await database.fetchall(
                    "SELECT channel_id FROM sticky_messages WHERE channel_id IN (SELECT id FROM channels WHERE guild_id = ?)",
                    (str(guild_id),),
                )
                if channels:
                    channel_ids = [ch["channel_id"] for ch in channels]
                    query += f" AND channel_id IN ({','.join(['?' for _ in channel_ids])})"
                    params = tuple(channel_ids)
                else:
                    return 0  # Nenhum canal encontrado

            stickies = await database.fetchall(query, params)

            reposted_count = 0

            for sticky in stickies:
                try:
                    await self.force_repost_single_sticky(sticky)
                    reposted_count += 1
                except Exception as e:
                    print(f"❌ Erro repostando sticky {sticky['id']}: {e}")
                    continue

            return reposted_count

        except Exception as e:
            print(f"❌ Erro forçando repost de stickies: {e}")
            return 0

    async def force_repost_single_sticky(self, sticky_data):
        """Forçar repostagem de uma sticky específica"""
        try:
            channel = self.bot.get_channel(int(sticky_data["channel_id"]))
            if not channel:
                return False

            # Deletar mensagem anterior
            if sticky_data.get("last_message_id"):
                try:
                    old_message = await channel.fetch_message(int(sticky_data["last_message_id"]))
                    await old_message.delete()
                except:
                    pass

            # Preparar conteúdo
            content = sticky_data.get("content", "")
            embed = None

            if sticky_data.get("embed_data"):
                try:
                    import json

                    embed_dict = json.loads(sticky_data["embed_data"])
                    embed = discord.Embed.from_dict(embed_dict)
                except:
                    pass

            # Postar
            if content or embed:
                new_message = await channel.send(content=content or None, embed=embed)

                # Atualizar
                await database.run(
                    "UPDATE sticky_messages SET last_message_id = ?, last_posted = ? WHERE id = ?",
                    (str(new_message.id), discord.utils.utcnow().isoformat(), sticky_data["id"]),
                )

                return True

            return False

        except Exception as e:
            print(f"❌ Erro forçando repost de sticky: {e}")
            return False

    async def cleanup_old_stickies(self):
        """Limpar stickies antigas e inválidas"""
        try:
            # Buscar todas as stickies
            all_stickies = await database.fetchall("SELECT * FROM sticky_messages")

            cleaned_count = 0

            for sticky in all_stickies:
                channel = self.bot.get_channel(int(sticky["channel_id"]))

                if not channel:
                    # Canal não existe mais, remover sticky
                    await database.run("DELETE FROM sticky_messages WHERE id = ?", (sticky["id"],))
                    cleaned_count += 1
                    continue

                # Verificar se mensagem ainda existe
                if sticky.get("last_message_id"):
                    try:
                        await channel.fetch_message(int(sticky["last_message_id"]))
                    except discord.NotFound:
                        # Mensagem não existe mais, limpar referência
                        await database.run(
                            "UPDATE sticky_messages SET last_message_id = NULL WHERE id = ?",
                            (sticky["id"],),
                        )

            return cleaned_count

        except Exception as e:
            print(f"❌ Erro limpando stickies antigas: {e}")
            return 0


async def setup(bot):
    await bot.add_cog(StickyMessagesPoster(bot))
