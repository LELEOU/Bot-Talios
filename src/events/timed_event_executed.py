"""
Timed Event Executed - Sistema de eventos agendados
"""

import sys
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands, tasks

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class TimedEventExecuted(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_scheduled_events.start()

    def cog_unload(self):
        self.check_scheduled_events.cancel()

    @tasks.loop(seconds=30)  # Verificar a cada 30 segundos
    async def check_scheduled_events(self):
        """Verificar e executar eventos agendados"""
        try:
            # Buscar eventos prontos para execução
            current_time = discord.utils.utcnow().isoformat()

            pending_events = await database.fetchall(
                "SELECT * FROM scheduled_events WHERE execute_at <= ? AND status = 'pending' ORDER BY execute_at",
                (current_time,),
            )

            for event in pending_events:
                await self.execute_scheduled_event(event)

        except Exception as e:
            print(f"❌ Erro verificando eventos agendados: {e}")

    @check_scheduled_events.before_loop
    async def before_check_scheduled_events(self):
        """Aguardar bot ficar online"""
        await self.bot.wait_until_ready()

    async def execute_scheduled_event(self, event):
        """Executar evento agendado"""
        try:
            event_type = event["event_type"]

            # Marcar como em execução
            await database.run(
                "UPDATE scheduled_events SET status = 'executing', executed_at = ? WHERE id = ?",
                (discord.utils.utcnow().isoformat(), event["id"]),
            )

            # Executar baseado no tipo
            success = False

            if event_type == "reminder":
                success = await self.execute_reminder(event)
            elif event_type == "unmute":
                success = await self.execute_unmute(event)
            elif event_type == "unban":
                success = await self.execute_unban(event)
            elif event_type == "role_remove":
                success = await self.execute_role_remove(event)
            elif event_type == "giveaway_end":
                success = await self.execute_giveaway_end(event)
            elif event_type == "poll_end":
                success = await self.execute_poll_end(event)
            elif event_type == "announcement":
                success = await self.execute_announcement(event)
            else:
                print(f"⚠️ Tipo de evento desconhecido: {event_type}")

            # Atualizar status final
            final_status = "completed" if success else "failed"
            await database.run(
                "UPDATE scheduled_events SET status = ?, completed_at = ? WHERE id = ?",
                (final_status, discord.utils.utcnow().isoformat(), event["id"]),
            )

        except Exception as e:
            print(f"❌ Erro executando evento agendado: {e}")
            # Marcar como falhou
            await database.run(
                "UPDATE scheduled_events SET status = 'failed', error = ? WHERE id = ?",
                (str(e), event["id"]),
            )

    async def execute_reminder(self, event):
        """Executar lembrete"""
        try:
            import json

            data = json.loads(event["event_data"]) if event["event_data"] else {}

            user_id = data.get("user_id")
            message = data.get("message", "Lembrete!")
            channel_id = data.get("channel_id")

            if user_id:
                user = self.bot.get_user(int(user_id))
                if user:
                    embed = discord.Embed(
                        title="⏰ Lembrete",
                        description=message,
                        color=0x0099FF,
                        timestamp=discord.utils.utcnow(),
                    )

                    try:
                        await user.send(embed=embed)
                        return True
                    except discord.Forbidden:
                        # Tentar enviar no canal se não conseguir DM
                        if channel_id:
                            channel = self.bot.get_channel(int(channel_id))
                            if channel:
                                await channel.send(f"{user.mention}", embed=embed)
                                return True

            return False

        except Exception as e:
            print(f"❌ Erro executando lembrete: {e}")
            return False

    async def execute_unmute(self, event):
        """Executar desmute"""
        try:
            import json

            data = json.loads(event["event_data"]) if event["event_data"] else {}

            guild_id = data.get("guild_id")
            user_id = data.get("user_id")

            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return False

            member = guild.get_member(int(user_id))
            if not member:
                return True  # Usuário saiu, considerar como sucesso

            # Buscar role de mute
            mute_role = discord.utils.get(guild.roles, name="Muted")
            if mute_role and mute_role in member.roles:
                await member.remove_roles(mute_role, reason="Mute temporário expirado")

            return True

        except Exception as e:
            print(f"❌ Erro executando unmute: {e}")
            return False

    async def execute_unban(self, event):
        """Executar desban"""
        try:
            import json

            data = json.loads(event["event_data"]) if event["event_data"] else {}

            guild_id = data.get("guild_id")
            user_id = data.get("user_id")

            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return False

            try:
                await guild.unban(discord.Object(id=int(user_id)), reason="Ban temporário expirado")
                return True
            except discord.NotFound:
                # Usuário já foi desbanido
                return True

        except Exception as e:
            print(f"❌ Erro executando unban: {e}")
            return False

    async def execute_role_remove(self, event):
        """Executar remoção de role"""
        try:
            import json

            data = json.loads(event["event_data"]) if event["event_data"] else {}

            guild_id = data.get("guild_id")
            user_id = data.get("user_id")
            role_id = data.get("role_id")

            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return False

            member = guild.get_member(int(user_id))
            if not member:
                return True  # Usuário saiu

            role = guild.get_role(int(role_id))
            if not role:
                return True  # Role foi deletado

            if role in member.roles:
                await member.remove_roles(role, reason="Role temporário expirado")

            return True

        except Exception as e:
            print(f"❌ Erro removendo role: {e}")
            return False

    async def execute_giveaway_end(self, event):
        """Finalizar sorteio"""
        try:
            import json

            data = json.loads(event["event_data"]) if event["event_data"] else {}

            giveaway_id = data.get("giveaway_id")

            # Buscar sorteio
            giveaway = await database.fetchone(
                "SELECT * FROM giveaways WHERE id = ?", (giveaway_id,)
            )

            if not giveaway:
                return False

            # Implementar lógica de finalização do sorteio
            # (será implementado no sistema específico de giveaways)

            return True

        except Exception as e:
            print(f"❌ Erro finalizando sorteio: {e}")
            return False

    async def execute_poll_end(self, event):
        """Finalizar enquete"""
        try:
            import json

            data = json.loads(event["event_data"]) if event["event_data"] else {}

            poll_id = data.get("poll_id")

            # Buscar enquete
            poll = await database.fetchone("SELECT * FROM polls WHERE id = ?", (poll_id,))

            if not poll:
                return False

            # Implementar lógica de finalização da enquete
            # (será implementado no sistema específico de polls)

            return True

        except Exception as e:
            print(f"❌ Erro finalizando enquete: {e}")
            return False

    async def execute_announcement(self, event):
        """Executar anúncio agendado"""
        try:
            import json

            data = json.loads(event["event_data"]) if event["event_data"] else {}

            channel_id = data.get("channel_id")
            message = data.get("message")
            embed_data = data.get("embed")

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return False

            # Preparar embed se houver
            embed = None
            if embed_data:
                embed = discord.Embed.from_dict(embed_data)

            await channel.send(content=message or None, embed=embed)
            return True

        except Exception as e:
            print(f"❌ Erro executando anúncio: {e}")
            return False

    async def schedule_event(
        self,
        event_type: str,
        execute_at: datetime,
        event_data: dict,
        guild_id: int = None,
        created_by: int = None,
    ) -> int:
        """Agendar novo evento"""
        try:
            import json

            result = await database.run(
                """INSERT INTO scheduled_events 
                   (event_type, execute_at, event_data, guild_id, created_by, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_type,
                    execute_at.isoformat(),
                    json.dumps(event_data),
                    str(guild_id) if guild_id else None,
                    str(created_by) if created_by else None,
                    "pending",
                    discord.utils.utcnow().isoformat(),
                ),
            )

            return result  # ID do evento agendado

        except Exception as e:
            print(f"❌ Erro agendando evento: {e}")
            return None

    async def cancel_scheduled_event(self, event_id: int) -> bool:
        """Cancelar evento agendado"""
        try:
            await database.run(
                "UPDATE scheduled_events SET status = 'cancelled', cancelled_at = ? WHERE id = ? AND status = 'pending'",
                (discord.utils.utcnow().isoformat(), event_id),
            )
            return True

        except Exception as e:
            print(f"❌ Erro cancelando evento: {e}")
            return False


async def setup(bot):
    await bot.add_cog(TimedEventExecuted(bot))
