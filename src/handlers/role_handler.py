"""
Role Handler - Sistema de gerenciamento de cargos
"""

import sys
from pathlib import Path

import discord
from discord.ext import commands

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import database


class RoleHandler:
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def handle_button(interaction: discord.Interaction):
        """Handler básico para botões de cargo"""
        try:
            custom_id = interaction.data["custom_id"]

            if custom_id.startswith("role_assign_"):
                role_id = int(custom_id.split("_")[2])
                role = interaction.guild.get_role(role_id)

                if not role:
                    return await interaction.response.send_message(
                        "❌ Cargo não encontrado.", ephemeral=True
                    )

                member = interaction.user

                if role in member.roles:
                    await member.remove_roles(role)
                    await interaction.response.send_message(
                        f"➖ Cargo {role.name} removido!", ephemeral=True
                    )
                else:
                    await member.add_roles(role)
                    await interaction.response.send_message(
                        f"➕ Cargo {role.name} adicionado!", ephemeral=True
                    )

        except Exception as error:
            print(f"❌ Erro no roleHandler: {error}")
            await interaction.response.send_message("❌ Erro ao gerenciar cargo.", ephemeral=True)

    @staticmethod
    async def handle_select_menu(interaction: discord.Interaction):
        """Handler para select menus de cargos"""
        try:
            selected_roles = interaction.data["values"]
            member = interaction.user

            # Adicionar cargos selecionados
            roles_added = []
            for role_id in selected_roles:
                role = interaction.guild.get_role(int(role_id))
                if role and role not in member.roles:
                    await member.add_roles(role)
                    roles_added.append(role.name)

            await interaction.response.send_message(
                f"✅ Cargos atualizados: {len(roles_added)} cargos aplicados!\\n"
                + (f"Cargos adicionados: {', '.join(roles_added)}" if roles_added else ""),
                ephemeral=True,
            )

        except Exception as error:
            print(f"❌ Erro no roleHandler selectMenu: {error}")
            await interaction.response.send_message("❌ Erro ao atualizar cargos.", ephemeral=True)

    @staticmethod
    async def create_role_embed(
        title: str, description: str, roles: list, embed_type: str = "button"
    ) -> tuple:
        """Criar embed e componentes para sistema de cargos"""
        try:
            embed = discord.Embed(title=title, description=description, color=0x00FF00)

            components = []

            if embed_type == "button":
                # Criar botões para cada cargo
                view = discord.ui.View(timeout=None)

                for role_data in roles:
                    if isinstance(role_data, dict):
                        role_id = role_data.get("id")
                        role_name = role_data.get("name")
                        role_emoji = role_data.get("emoji", "🎭")
                    else:
                        role_id = role_data.id
                        role_name = role_data.name
                        role_emoji = "🎭"

                    button = discord.ui.Button(
                        label=role_name,
                        emoji=role_emoji,
                        custom_id=f"role_assign_{role_id}",
                        style=discord.ButtonStyle.secondary,
                    )
                    view.add_item(button)

                components = view

            elif embed_type == "select":
                # Criar select menu para cargos
                view = discord.ui.View(timeout=None)

                options = []
                for role_data in roles:
                    if isinstance(role_data, dict):
                        role_id = role_data.get("id")
                        role_name = role_data.get("name")
                        role_description = role_data.get(
                            "description", "Clique para obter este cargo"
                        )
                        role_emoji = role_data.get("emoji")
                    else:
                        role_id = role_data.id
                        role_name = role_data.name
                        role_description = "Clique para obter este cargo"
                        role_emoji = None

                    options.append(
                        discord.SelectOption(
                            label=role_name,
                            value=str(role_id),
                            description=role_description,
                            emoji=role_emoji,
                        )
                    )

                select = discord.ui.Select(
                    placeholder="Escolha seus cargos...",
                    options=options,
                    max_values=len(options),
                    custom_id="role_select_menu",
                )

                view.add_item(select)
                components = view

            return embed, components

        except Exception as e:
            print(f"❌ Erro criando embed de cargos: {e}")
            return None, None

    @staticmethod
    async def get_assignable_roles(guild_id: int) -> list:
        """Buscar cargos atribuíveis do servidor"""
        try:
            result = await database.fetchall(
                "SELECT * FROM assignable_roles WHERE guild_id = ? ORDER BY position ASC",
                (str(guild_id),),
            )

            return [dict(row) for row in result] if result else []

        except Exception as e:
            print(f"❌ Erro buscando cargos atribuíveis: {e}")
            return []

    @staticmethod
    async def add_assignable_role(
        guild_id: int, role_id: int, name: str, description: str = None, emoji: str = None
    ) -> bool:
        """Adicionar cargo atribuível"""
        try:
            await database.run(
                """INSERT OR REPLACE INTO assignable_roles 
                   (guild_id, role_id, name, description, emoji, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(guild_id),
                    str(role_id),
                    name,
                    description,
                    emoji,
                    discord.utils.utcnow().isoformat(),
                ),
            )

            return True

        except Exception as e:
            print(f"❌ Erro adicionando cargo atribuível: {e}")
            return False

    @staticmethod
    async def remove_assignable_role(guild_id: int, role_id: int) -> bool:
        """Remover cargo atribuível"""
        try:
            await database.run(
                "DELETE FROM assignable_roles WHERE guild_id = ? AND role_id = ?",
                (str(guild_id), str(role_id)),
            )

            return True

        except Exception as e:
            print(f"❌ Erro removendo cargo atribuível: {e}")
            return False

    @staticmethod
    async def log_role_change(
        guild_id: int, user_id: int, role_id: int, action: str, moderator_id: int = None
    ):
        """Registrar mudança de cargo"""
        try:
            await database.run(
                """INSERT INTO role_logs 
                   (guild_id, user_id, role_id, action, moderator_id, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(guild_id),
                    str(user_id),
                    str(role_id),
                    action,
                    str(moderator_id) if moderator_id else None,
                    discord.utils.utcnow().isoformat(),
                ),
            )

        except Exception as e:
            print(f"❌ Erro registrando mudança de cargo: {e}")


class RoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_handler = RoleHandler(bot)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Listener para interações de cargos"""
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")

        if custom_id.startswith("role_assign_"):
            await RoleHandler.handle_button(interaction)
        elif custom_id == "role_select_menu":
            await RoleHandler.handle_select_menu(interaction)


async def setup(bot):
    await bot.add_cog(RoleCog(bot))
