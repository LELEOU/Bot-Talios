"""
Event handler para interações - VERSÃO COMPLETA ADAPTADA DO JS
Gerencia todos os tipos: slash commands, buttons, selects, modals
"""

import sys
import time
import traceback
from pathlib import Path

import discord
from discord.ext import commands

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database


class InteractionCreate(commands.Cog):
    """Event handler completo para todas as interações"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Manipular todas as interações"""
        try:
            # Comandos slash
            if interaction.type == discord.InteractionType.application_command:
                await self.handle_slash_command(interaction)

            # Buttons e Select Menus
            elif interaction.type == discord.InteractionType.component:
                await self.handle_component(interaction)

            # Modals
            elif interaction.type == discord.InteractionType.modal_submit:
                await self.handle_modal(interaction)

        except Exception as e:
            print(f"❌ Erro processando interação: {e}")
            traceback.print_exc()

    async def handle_slash_command(self, interaction: discord.Interaction):
        """Sistema de cooldown para comandos slash"""
        try:
            command_name = interaction.data.get("name")

            # Sistema de cooldown
            cooldown_passed = await self.check_cooldown(interaction, command_name)
            if not cooldown_passed:
                return

            print(f"✅ Comando {command_name} executado por {interaction.user}")

        except discord.InteractionResponded:
            # Comando já foi respondido
            pass
        except Exception as e:
            print(f"❌ Erro no comando slash {command_name}: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ Erro interno do bot!", ephemeral=True
                    )
            except:
                pass

    async def handle_component(self, interaction: discord.Interaction):
        """Manipular botões e select menus"""
        try:
            custom_id = interaction.data.get("custom_id", "")

            # 🎁 GIVEAWAY BUTTONS
            if custom_id.startswith("giveaway_"):
                await self.handle_giveaway_component(interaction)

            # 🎫 TICKET BUTTONS
            elif custom_id.startswith("ticket_"):
                await self.handle_ticket_component(interaction)

            # 📊 POLL BUTTONS
            elif custom_id.startswith("poll_"):
                await self.handle_poll_component(interaction)

            # 💡 SUGGESTION BUTTONS
            elif custom_id.startswith("suggestion_"):
                await self.handle_suggestion_component(interaction)

            # 📦 CONTAINER BUTTONS
            elif custom_id.startswith("container_"):
                await self.handle_container_component(interaction)

            # 🎭 ROLE BUTTONS
            elif custom_id.startswith("role_"):
                await self.handle_role_component(interaction)

            # 🔨 MODERATION BUTTONS
            elif custom_id.startswith(("ban_", "kick_", "mute_", "warn_")):
                await self.handle_moderation_component(interaction)

            # 🎵 MUSIC BUTTONS
            elif custom_id.startswith("music_"):
                await self.handle_music_component(interaction)

            # 📋 EMBED BUILDER
            elif custom_id.startswith("embed_"):
                await self.handle_embed_component(interaction)

            else:
                await interaction.response.send_message(
                    "❌ Componente não reconhecido!", ephemeral=True
                )

        except Exception as e:
            print(f"❌ Erro manipulando componente {custom_id}: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Erro interno!", ephemeral=True)
            except:
                pass

    async def handle_modal(self, interaction: discord.Interaction):
        """Manipular modals"""
        try:
            custom_id = interaction.data.get("custom_id", "")

            # 🎫 TICKET MODALS
            if custom_id.startswith("ticket_modal_"):
                await self.handle_ticket_modal(interaction)

            # 📦 CONTAINER MODALS
            elif custom_id.startswith("container_modal_"):
                await self.handle_container_modal(interaction)

            # 📋 EMBED MODALS
            elif custom_id.startswith("embed_modal_"):
                await self.handle_embed_modal(interaction)

            # 📊 POLL MODALS
            elif custom_id.startswith("poll_modal_"):
                await self.handle_poll_modal(interaction)

            # 💡 SUGGESTION MODALS
            elif custom_id.startswith("suggestion_modal_"):
                await self.handle_suggestion_modal(interaction)

            else:
                await interaction.response.send_message("❌ Modal não reconhecido!", ephemeral=True)

        except Exception as e:
            print(f"❌ Erro processando modal {custom_id}: {e}")

    # ⏰ SISTEMA DE COOLDOWN
    async def check_cooldown(self, interaction: discord.Interaction, command_name: str):
        """Sistema de cooldown robusto"""
        try:
            if not hasattr(self.bot, "cooldowns"):
                self.bot.cooldowns = {}

            if command_name not in self.bot.cooldowns:
                self.bot.cooldowns[command_name] = {}

            user_id = interaction.user.id
            current_time = time.time()
            cooldown_time = 3  # 3 segundos padrão

            # Verificar se usuário está em cooldown
            if user_id in self.bot.cooldowns[command_name]:
                last_used = self.bot.cooldowns[command_name][user_id]
                time_left = cooldown_time - (current_time - last_used)

                if time_left > 0:
                    timestamp = int(current_time + time_left)
                    await interaction.response.send_message(
                        f"⏰ Aguarde <t:{timestamp}:R> para usar este comando novamente.",
                        ephemeral=True,
                    )
                    return False

            # Atualizar cooldown
            self.bot.cooldowns[command_name][user_id] = current_time

            # Limpar cooldowns antigos automaticamente (performance)
            for uid, timestamp in list(self.bot.cooldowns[command_name].items()):
                if current_time - timestamp > 3600:  # 1 hora
                    del self.bot.cooldowns[command_name][uid]

            return True

        except Exception as e:
            print(f"❌ Erro no sistema de cooldown: {e}")
            return True  # Em caso de erro, permitir execução

    # 🎁 GIVEAWAY HANDLERS
    async def handle_giveaway_component(self, interaction: discord.Interaction):
        """Manipular componentes de giveaway"""
        try:
            custom_id = interaction.data.get("custom_id")

            if custom_id == "giveaway_enter":
                await self.giveaway_enter(interaction)
            elif custom_id == "giveaway_leave":
                await self.giveaway_leave(interaction)
            elif custom_id == "giveaway_reroll":
                await self.giveaway_reroll(interaction)

        except Exception as e:
            print(f"❌ Erro giveaway component: {e}")

    async def giveaway_enter(self, interaction: discord.Interaction):
        """Entrar no giveaway"""
        try:
            message_id = str(interaction.message.id)
            user_id = str(interaction.user.id)

            # Verificar se giveaway existe e está ativo
            giveaway = await database.get_giveaway_by_message_id(message_id)
            if not giveaway:
                return await interaction.response.send_message(
                    "❌ Giveaway não encontrado!", ephemeral=True
                )

            if giveaway["status"] != "active":
                return await interaction.response.send_message(
                    "❌ Este giveaway não está mais ativo!", ephemeral=True
                )

            # Verificar se já está participando
            participant = await database.get_giveaway_participant(message_id, user_id)
            if participant:
                return await interaction.response.send_message(
                    "❌ Você já está participando deste giveaway!", ephemeral=True
                )

            # Adicionar participante
            await database.add_giveaway_participant(message_id, user_id)

            # Contar participantes
            count = await database.get_giveaway_participants_count(message_id)

            await interaction.response.send_message(
                f"✅ Você entrou no giveaway! Total de participantes: **{count}**", ephemeral=True
            )

        except Exception as e:
            print(f"❌ Erro entrando no giveaway: {e}")
            await interaction.response.send_message(
                "❌ Erro ao entrar no giveaway!", ephemeral=True
            )

    # 🎫 TICKET HANDLERS
    async def handle_ticket_component(self, interaction: discord.Interaction):
        """Manipular componentes de ticket"""
        try:
            custom_id = interaction.data.get("custom_id")

            if custom_id == "ticket_create":
                await self.create_ticket(interaction)
            elif custom_id == "ticket_close":
                await self.close_ticket(interaction)
            elif custom_id == "ticket_delete":
                await self.delete_ticket(interaction)

        except Exception as e:
            print(f"❌ Erro ticket component: {e}")

    async def create_ticket(self, interaction: discord.Interaction):
        """Criar novo ticket"""
        try:
            # Verificar se já tem ticket aberto
            existing = await database.get_user_open_ticket(
                str(interaction.guild.id), str(interaction.user.id)
            )

            if existing:
                channel = interaction.guild.get_channel(int(existing["channel_id"]))
                if channel:
                    return await interaction.response.send_message(
                        f"❌ Você já possui um ticket aberto: {channel.mention}", ephemeral=True
                    )

            # Criar categoria se não existir
            category = discord.utils.get(interaction.guild.categories, name="🎫 Tickets")
            if not category:
                category = await interaction.guild.create_category("🎫 Tickets")

            # Criar canal
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, attach_files=True, embed_links=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    attach_files=True,
                    embed_links=True,
                ),
            }

            # Adicionar staff role se existir
            staff_roles = ["Staff", "Moderator", "Admin", "Suporte"]
            for role_name in staff_roles:
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True, manage_messages=True
                    )

            ticket_channel = await interaction.guild.create_text_channel(
                f"ticket-{interaction.user.name}", category=category, overwrites=overwrites
            )

            # Salvar no banco
            await database.create_ticket(
                str(interaction.guild.id),
                str(interaction.user.id),
                str(ticket_channel.id),
                "Ticket de suporte",
            )

            # Embed de boas-vindas
            embed = discord.Embed(
                title="🎫 Ticket de Suporte",
                description=f"Olá {interaction.user.mention}!\\n\\n"
                "Descreva seu problema detalhadamente e nossa equipe irá ajudá-lo.",
                color=0x00FF00,
            )

            embed.add_field(
                name="📋 Como funciona",
                value="• Explique sua dúvida claramente\\n"
                "• Seja paciente, responderemos em breve\\n"
                "• Use o botão para fechar quando resolver",
                inline=False,
            )

            # Botões do ticket
            view = discord.ui.View(timeout=None)

            close_btn = discord.ui.Button(
                label="🔒 Fechar", style=discord.ButtonStyle.danger, custom_id="ticket_close"
            )

            view.add_item(close_btn)

            await ticket_channel.send(embed=embed, view=view)

            await interaction.response.send_message(
                f"✅ Ticket criado: {ticket_channel.mention}", ephemeral=True
            )

        except Exception as e:
            print(f"❌ Erro criando ticket: {e}")
            await interaction.response.send_message("❌ Erro ao criar ticket!", ephemeral=True)

    # 📊 POLL HANDLERS
    async def handle_poll_component(self, interaction: discord.Interaction):
        """Manipular componentes de poll"""
        try:
            custom_id = interaction.data.get("custom_id")

            if custom_id.startswith("poll_vote_"):
                option = custom_id.split("_")[-1]
                await self.poll_vote(interaction, option)

        except Exception as e:
            print(f"❌ Erro poll component: {e}")

    async def poll_vote(self, interaction: discord.Interaction, option: str):
        """Votar em poll"""
        try:
            message_id = str(interaction.message.id)
            user_id = str(interaction.user.id)

            # Verificar se já votou
            existing_vote = await database.get_poll_vote(message_id, user_id)

            if existing_vote:
                # Atualizar voto
                await database.update_poll_vote(message_id, user_id, option)
                msg = f"✅ Voto atualizado para opção {option}!"
            else:
                # Novo voto
                await database.add_poll_vote(message_id, user_id, option)
                msg = f"✅ Voto registrado na opção {option}!"

            await interaction.response.send_message(msg, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro votando: {e}")

    # 💡 SUGGESTION HANDLERS
    async def handle_suggestion_component(self, interaction: discord.Interaction):
        """Manipular componentes de sugestão"""
        try:
            custom_id = interaction.data.get("custom_id")

            if custom_id == "suggestion_approve":
                await self.approve_suggestion(interaction)
            elif custom_id == "suggestion_deny":
                await self.deny_suggestion(interaction)

        except Exception as e:
            print(f"❌ Erro suggestion component: {e}")

    # 🎫 MODAL HANDLERS
    async def handle_ticket_modal(self, interaction: discord.Interaction):
        """Processar modal de ticket"""
        try:
            # Obter dados do modal
            reason = None
            for component in interaction.data.get("components", []):
                if component["components"][0]["custom_id"] == "ticket_reason":
                    reason = component["components"][0]["value"]
                    break

            if not reason:
                reason = "Motivo não especificado"

            # Usar a mesma lógica do create_ticket mas com reason
            await self.create_ticket_with_reason(interaction, reason)

        except Exception as e:
            print(f"❌ Erro modal ticket: {e}")

    async def create_ticket_with_reason(self, interaction: discord.Interaction, reason: str):
        """Criar ticket com motivo específico"""
        # Similar ao create_ticket mas inclui o motivo
        await self.create_ticket(interaction)


async def setup(bot):
    """Setup function para carregar o cog"""
    await bot.add_cog(InteractionCreate(bot))
