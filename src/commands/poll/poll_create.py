"""
Sistema de Poll - Criar Votações
Comando para criar enquetes/votações interativas
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
import uuid

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from typing import Callable


class PollView(discord.ui.View):
    """Interface de votação para polls"""

    def __init__(self, poll_data: dict[str, Any]) -> None:
        super().__init__(timeout=None)
        self.poll_data: dict[str, Any] = poll_data
        self.poll_id: str = poll_data["id"]

        # Criar botões dinamicamente baseado nas opções
        for i, option in enumerate(poll_data["options"]):
            button: discord.ui.Button = discord.ui.Button(
                label=f"{option['emoji']} {option['text'][:20]}{'...' if len(option['text']) > 20 else ''}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"poll_vote_{self.poll_id}_{i}",
                emoji=option["emoji"],
            )
            button.callback = self.create_vote_callback(i)
            self.add_item(button)

    def create_vote_callback(self, option_index: int) -> Callable:
        """Cria callback personalizado para cada opção"""

        async def vote_callback(interaction: discord.Interaction) -> None:
            await self.handle_vote(interaction, option_index)

        return vote_callback

    async def handle_vote(self, interaction: discord.Interaction, option_index: int) -> None:
        """Processa voto do usuário"""
        try:
            await interaction.response.defer(ephemeral=True)

            # Verificar se poll ainda está ativo
            if self.poll_data.get("status") != "active":
                await interaction.followup.send(
                    "❌ Esta votação já foi finalizada!", ephemeral=True
                )
                return

            # Verificar se ainda está no prazo (se houver)
            if self.poll_data.get("end_time"):
                end_time: datetime = datetime.fromisoformat(self.poll_data["end_time"])
                if datetime.now() > end_time:
                    await interaction.followup.send(
                        "❌ O prazo para votação já expirou!", ephemeral=True
                    )
                    return

            try:
                from ...utils.database import database

                # Verificar se já votou
                existing_vote: dict[str, Any] | None = await database.get(
                    "SELECT * FROM poll_votes WHERE poll_id = ? AND user_id = ?",
                    (self.poll_id, str(interaction.user.id)),
                )

                if existing_vote:
                    if existing_vote["option_index"] == option_index:
                        # Remover voto (toggle)
                        await database.execute(
                            "DELETE FROM poll_votes WHERE poll_id = ? AND user_id = ?",
                            (self.poll_id, str(interaction.user.id)),
                        )

                        option_text: str = self.poll_data["options"][option_index]["text"]
                        await interaction.followup.send(
                            f"🗳️ **Voto removido!**\nSua escolha `{option_text}` foi retirada.",
                            ephemeral=True,
                        )
                    else:
                        # Alterar voto
                        await database.execute(
                            "UPDATE poll_votes SET option_index = ?, voted_at = ? WHERE poll_id = ? AND user_id = ?",
                            (
                                option_index,
                                datetime.now().isoformat(),
                                self.poll_id,
                                str(interaction.user.id),
                            ),
                        )

                        old_option: str = self.poll_data["options"][
                            existing_vote["option_index"]
                        ]["text"]
                        new_option: str = self.poll_data["options"][option_index]["text"]
                        await interaction.followup.send(
                            f"🔄 **Voto alterado!**\nDe: `{old_option}`\nPara: `{new_option}`",
                            ephemeral=True,
                        )
                else:
                    # Novo voto
                    await database.execute(
                        "INSERT INTO poll_votes (poll_id, user_id, option_index, voted_at) VALUES (?, ?, ?, ?)",
                        (
                            self.poll_id,
                            str(interaction.user.id),
                            option_index,
                            datetime.now().isoformat(),
                        ),
                    )

                    option_text: str = self.poll_data["options"][option_index]["text"]
                    await interaction.followup.send(
                        f"✅ **Voto registrado!**\nSua escolha: `{option_text}`", ephemeral=True
                    )

                # Atualizar embed com resultados
                await self.update_poll_embed(interaction)

            except Exception as e:
                print(f"❌ Erro ao registrar voto: {e}")
                await interaction.followup.send(
                    "❌ Erro ao registrar voto. Tente novamente.", ephemeral=True
                )

        except Exception as e:
            print(f"❌ Erro no sistema de votação: {e}")

    async def update_poll_embed(self, interaction: discord.Interaction) -> None:
        """Atualiza embed com resultados atualizados"""
        try:
            from ...utils.database import database

            # Buscar todos os votos
            votes: list[dict[str, Any]] | None = await database.get_all(
                "SELECT option_index FROM poll_votes WHERE poll_id = ?", (self.poll_id,)
            )

            votes = votes or []
            total_votes: int = len(votes)

            # Contar votos por opção
            vote_counts: dict[int, int] = {}
            for vote in votes:
                option_index: int = vote["option_index"]
                vote_counts[option_index] = vote_counts.get(option_index, 0) + 1

            # Criar embed atualizado
            embed: discord.Embed = discord.Embed(
                title=f"🗳️ **{self.poll_data['question']}**",
                description=self.poll_data.get("description", ""),
                color=0x2F3136,
                timestamp=datetime.now(),
            )

            # Adicionar opções com resultados
            results_text: str = ""
            for i, option in enumerate(self.poll_data["options"]):
                count: int = vote_counts.get(i, 0)
                percentage: float = (count / total_votes * 100) if total_votes > 0 else 0

                # Criar barra de progresso
                bar_length: int = 10
                filled_bars: int = int(percentage / 10)
                empty_bars: int = bar_length - filled_bars
                progress_bar: str = "█" * filled_bars + "░" * empty_bars

                results_text += f"{option['emoji']} **{option['text']}**\n"
                results_text += f"`{progress_bar}` {count} votos ({percentage:.1f}%)\n\n"

            embed.add_field(name="📊 Resultados", value=results_text, inline=False)

            # Informações adicionais
            embed.add_field(
                name="📈 Estatísticas",
                value=f"**Total de votos:** {total_votes}\n"
                f"**Opções:** {len(self.poll_data['options'])}\n"
                f"**Status:** {'🟢 Ativo' if self.poll_data.get('status') == 'active' else '🔴 Finalizado'}",
                inline=True,
            )

            # Informações de tempo
            created_time: datetime = datetime.fromisoformat(self.poll_data["created_at"])
            time_info: str = f"**Criado:** <t:{int(created_time.timestamp())}:R>\n"

            if self.poll_data.get("end_time"):
                end_time: datetime = datetime.fromisoformat(self.poll_data["end_time"])
                if datetime.now() < end_time:
                    time_info += f"**Termina:** <t:{int(end_time.timestamp())}:R>"
                else:
                    time_info += f"**Terminou:** <t:{int(end_time.timestamp())}:R>"
            else:
                time_info += "**Duração:** Permanente"

            embed.add_field(name="⏰ Tempo", value=time_info, inline=True)

            embed.add_field(name="👤 Criador", value=f"<@{self.poll_data['user_id']}>", inline=True)

            embed.set_footer(
                text=f"Poll ID: {self.poll_id} • Vote usando os botões abaixo",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            # Atualizar mensagem
            message: discord.Message = interaction.message
            await message.edit(embed=embed, view=self)

        except Exception as e:
            print(f"❌ Erro ao atualizar embed: {e}")


class PollCreate(commands.Cog):
    """Sistema de criação de enquetes/votações"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(name="poll-create", description="🗳️ Criar uma enquete/votação")
    @app_commands.describe(
        pergunta="A pergunta da votação",
        opcoes="Opções separadas por | (máximo 10)",
        duracao="Duração em minutos (opcional)",
        descricao="Descrição adicional da votação",
    )
    async def poll_create(
        self,
        interaction: discord.Interaction,
        pergunta: str,
        opcoes: str,
        duracao: int | None = None,
        descricao: str | None = None,
    ) -> None:
        try:
            await interaction.response.defer()

            # Validar pergunta
            if len(pergunta) > 200:
                await interaction.followup.send(
                    "❌ **Pergunta muito longa!**\n"
                    f"Máximo: 200 caracteres\n"
                    f"Atual: {len(pergunta)} caracteres",
                    ephemeral=True,
                )
                return

            # Processar opções
            option_texts: list[str] = [opt.strip() for opt in opcoes.split("|") if opt.strip()]

            if len(option_texts) < 2:
                await interaction.followup.send(
                    "❌ **Mínimo de 2 opções necessárias!**\n"
                    "💡 **Formato:** `Opção 1 | Opção 2 | Opção 3`",
                    ephemeral=True,
                )
                return

            if len(option_texts) > 10:
                await interaction.followup.send(
                    "❌ **Máximo de 10 opções permitidas!**\n"
                    f"Você forneceu: {len(option_texts)} opções",
                    ephemeral=True,
                )
                return

            # Validar duração
            if duracao is not None:
                if duracao < 1:
                    await interaction.followup.send(
                        "❌ **Duração deve ser pelo menos 1 minuto!**", ephemeral=True
                    )
                    return
                if duracao > 10080:  # 1 semana
                    await interaction.followup.send(
                        "❌ **Duração máxima: 1 semana (10080 minutos)!**", ephemeral=True
                    )
                    return

            # Gerar ID único
            poll_id: str = str(uuid.uuid4())[:8]

            # Emojis para opções
            option_emojis: list[str] = [
                "1️⃣",
                "2️⃣",
                "3️⃣",
                "4️⃣",
                "5️⃣",
                "6️⃣",
                "7️⃣",
                "8️⃣",
                "9️⃣",
                "🔟",
            ]

            # Criar estrutura de opções
            poll_options: list[dict[str, str]] = []
            for i, text in enumerate(option_texts):
                if len(text) > 50:
                    text = text[:47] + "..."

                poll_options.append({"text": text, "emoji": option_emojis[i]})

            # Calcular tempo de fim
            end_time: str | None = None
            if duracao:
                end_time = (datetime.now() + timedelta(minutes=duracao)).isoformat()

            # Dados do poll
            poll_data: dict[str, Any] = {
                "id": poll_id,
                "guild_id": str(interaction.guild.id),
                "channel_id": str(interaction.channel.id),
                "user_id": str(interaction.user.id),
                "question": pergunta,
                "description": descricao,
                "options": poll_options,
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "end_time": end_time,
            }

            # Criar embed inicial
            embed: discord.Embed = discord.Embed(
                title=f"🗳️ **{pergunta}**",
                description=descricao or "Vote usando os botões abaixo!",
                color=0x2F3136,
                timestamp=datetime.now(),
            )

            # Adicionar opções
            options_text: str = ""
            for option in poll_options:
                options_text += f"{option['emoji']} **{option['text']}**\n"
                options_text += "`░░░░░░░░░░` 0 votos (0.0%)\n\n"

            embed.add_field(name="📊 Opções", value=options_text, inline=False)

            embed.add_field(
                name="📈 Estatísticas",
                value="**Total de votos:** 0\n"
                f"**Opções:** {len(poll_options)}\n"
                "**Status:** 🟢 Ativo",
                inline=True,
            )

            # Informações de tempo
            time_info: str = f"**Criado:** <t:{int(datetime.now().timestamp())}:R>\n"
            if end_time:
                end_timestamp: int = int(datetime.fromisoformat(end_time).timestamp())
                time_info += f"**Termina:** <t:{end_timestamp}:R>"
            else:
                time_info += "**Duração:** Permanente"

            embed.add_field(name="⏰ Tempo", value=time_info, inline=True)

            embed.add_field(name="👤 Criador", value=interaction.user.mention, inline=True)

            embed.set_footer(
                text=f"Poll ID: {poll_id} • Vote usando os botões abaixo",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            # Criar view com botões
            view: PollView = PollView(poll_data)

            # Enviar mensagem
            message: discord.Message = await interaction.channel.send(
                f"📢 **Nova votação criada por {interaction.user.mention}!**",
                embed=embed,
                view=view,
            )

            # Salvar no banco
            try:
                from ...utils.database import database

                await database.execute(
                    """INSERT INTO polls 
                       (id, guild_id, channel_id, message_id, user_id, question, description, options, status, created_at, end_time) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        poll_id,
                        str(interaction.guild.id),
                        str(interaction.channel.id),
                        str(message.id),
                        str(interaction.user.id),
                        pergunta,
                        descricao,
                        json.dumps(poll_options),
                        "active",
                        datetime.now().isoformat(),
                        end_time,
                    ),
                )
            except Exception as e:
                print(f"❌ Erro ao salvar poll: {e}")

            # Confirmação para criador
            success_embed: discord.Embed = discord.Embed(
                title="✅ **Votação Criada!**",
                description="Sua enquete foi publicada com sucesso!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(name="🗳️ Pergunta", value=pergunta, inline=False)

            success_embed.add_field(
                name="📊 Opções", value=f"{len(poll_options)} opções disponíveis", inline=True
            )

            success_embed.add_field(name="🆔 ID da Votação", value=f"`{poll_id}`", inline=True)

            success_embed.add_field(
                name="🔗 Link", value=f"[Ver votação]({message.jump_url})", inline=True
            )

            if duracao:
                success_embed.add_field(name="⏰ Duração", value=f"{duracao} minutos", inline=True)

            success_embed.add_field(
                name="🎯 Comandos úteis",
                value="`/poll-results` - Ver resultados\n"
                "`/poll-end` - Finalizar votação\n"
                "`/poll-list` - Listar suas votações",
                inline=False,
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

            # Agendar finalização automática se houver duração
            if duracao:
                asyncio.create_task(self.auto_end_poll(poll_id, duracao * 60))

        except Exception as e:
            print(f"❌ Erro no comando poll-create: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao criar votação. Tente novamente.", ephemeral=True
                )
            except:
                pass

    async def auto_end_poll(self, poll_id: str, duration_seconds: int) -> None:
        """Finaliza poll automaticamente após duração especificada"""
        try:
            await asyncio.sleep(duration_seconds)

            # Buscar poll no banco
            from ...utils.database import database

            poll: dict[str, Any] | None = await database.get(
                "SELECT * FROM polls WHERE id = ? AND status = 'active'", (poll_id,)
            )

            if poll:
                # Atualizar status
                await database.execute(
                    "UPDATE polls SET status = 'finished' WHERE id = ?", (poll_id,)
                )

                # Buscar mensagem e atualizar
                try:
                    guild: discord.Guild | None = self.bot.get_guild(int(poll["guild_id"]))
                    channel: discord.TextChannel | None = guild.get_channel(
                        int(poll["channel_id"])
                    )
                    message: discord.Message = await channel.fetch_message(int(poll["message_id"]))

                    # Atualizar embed
                    if message.embeds:
                        embed: discord.Embed = message.embeds[0]
                        embed.color = 0xFF6B6B
                        embed.title = f"🔒 **{poll['question']}** (FINALIZADA)"

                        # Atualizar status no embed
                        for i, field in enumerate(embed.fields):
                            if "Estatísticas" in field.name:
                                old_value: str = field.value
                                new_value: str = old_value.replace("🟢 Ativo", "🔴 Finalizada")
                                embed.set_field_at(
                                    i, name=field.name, value=new_value, inline=field.inline
                                )
                                break

                        embed.set_footer(
                            text=f"Poll ID: {poll_id} • Votação finalizada automaticamente",
                            icon_url=embed.footer.icon_url,
                        )

                        await message.edit(embed=embed, view=None)

                        # Enviar mensagem de finalização
                        await channel.send(
                            f"⏰ **Votação finalizada!**\n"
                            f'A enquete "{poll["question"]}" atingiu o tempo limite.\n'
                            f"Use `/poll-results {poll_id}` para ver os resultados finais."
                        )

                except Exception as e:
                    print(f"❌ Erro ao finalizar poll automaticamente: {e}")

        except Exception as e:
            print(f"❌ Erro no auto-end poll: {e}")


async def setup(bot: commands.Bot) -> None:
    """Carrega o cog e views persistentes"""
    await bot.add_cog(PollCreate(bot))

    # Adicionar view persistente
    bot.add_view(PollView({"id": "persistent", "options": [], "status": "active"}))
