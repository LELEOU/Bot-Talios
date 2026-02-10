"""
Sistema de Roles - Reação Roles
Comando para configurar sistema de roles por reação
"""

import json
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class ReactionRoleView(discord.ui.View):
    """Interface para gerenciar reaction roles"""

    def __init__(self, reaction_roles_data):
        super().__init__(timeout=None)
        self.reaction_roles_data = reaction_roles_data

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Processa as reações para dar/remover roles"""
        try:
            # Encontrar qual role foi solicitado
            component_id = interaction.data.get("custom_id", "")

            if component_id.startswith("reaction_role_"):
                role_id = component_id.replace("reaction_role_", "")
                role = interaction.guild.get_role(int(role_id))

                if not role:
                    await interaction.response.send_message(
                        "❌ Role não encontrado! Pode ter sido deletado.", ephemeral=True
                    )
                    return False

                # Verificar se usuário já tem o role
                if role in interaction.user.roles:
                    # Remover role
                    try:
                        await interaction.user.remove_roles(
                            role, reason="Reaction Role - Removido pelo usuário"
                        )
                        await interaction.response.send_message(
                            f"➖ **Role removido!**\n"
                            f"🎭 **Role:** {role.mention}\n"
                            f"👤 **Usuário:** {interaction.user.mention}",
                            ephemeral=True,
                        )
                        return True
                    except discord.Forbidden:
                        await interaction.response.send_message(
                            f"❌ Não tenho permissão para remover o role {role.mention}!",
                            ephemeral=True,
                        )
                        return False
                else:
                    # Adicionar role
                    try:
                        await interaction.user.add_roles(
                            role, reason="Reaction Role - Adicionado pelo usuário"
                        )
                        await interaction.response.send_message(
                            f"➕ **Role adicionado!**\n"
                            f"🎭 **Role:** {role.mention}\n"
                            f"👤 **Usuário:** {interaction.user.mention}\n"
                            f"🎉 **Bem-vindo ao grupo!**",
                            ephemeral=True,
                        )
                        return True
                    except discord.Forbidden:
                        await interaction.response.send_message(
                            f"❌ Não tenho permissão para adicionar o role {role.mention}!",
                            ephemeral=True,
                        )
                        return False

        except Exception as e:
            print(f"❌ Erro no reaction role: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao processar role. Tente novamente.", ephemeral=True
                )
            except:
                pass
            return False

        return True


class RoleReaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="reaction-roles", description="🎭 Configurar sistema de roles por reação/botão"
    )
    @app_commands.describe(
        titulo="Título da mensagem de roles",
        descricao="Descrição/instruções para os usuários",
        roles="Roles separados por vírgula (máximo 20)",
        modo="Modo de interação (reação ou botões)",
    )
    async def reaction_roles(
        self,
        interaction: discord.Interaction,
        titulo: str,
        roles: str,
        descricao: str | None = None,
        modo: str | None = "botoes",
    ):
        try:
            # 🛡️ VERIFICAR PERMISSÕES
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para configurar reaction roles. **Necessário**: Gerenciar Roles",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # 🎭 PROCESSAR ROLES
            role_mentions = [r.strip() for r in roles.split(",") if r.strip()]

            if len(role_mentions) > 20:
                await interaction.followup.send(
                    "❌ Máximo de **20 roles** por mensagem de reaction roles!", ephemeral=True
                )
                return

            if not role_mentions:
                await interaction.followup.send(
                    "❌ Nenhum role válido encontrado!\n💡 **Formato:** `@Role1, @Role2, @Role3`",
                    ephemeral=True,
                )
                return

            # 🔍 VALIDAR ROLES
            valid_roles = []
            invalid_roles = []

            for role_mention in role_mentions:
                # Tentar encontrar role por menção, nome ou ID
                role_found = None

                # Por menção
                if role_mention.startswith("<@&") and role_mention.endswith(">"):
                    role_id = role_mention[3:-1]
                    role_found = interaction.guild.get_role(int(role_id))

                # Por ID
                elif role_mention.isdigit():
                    role_found = interaction.guild.get_role(int(role_mention))

                # Por nome
                else:
                    role_found = discord.utils.get(interaction.guild.roles, name=role_mention)

                if role_found:
                    # Verificar hierarquia
                    if role_found.position >= interaction.guild.me.top_role.position:
                        invalid_roles.append(f"{role_found.name} (hierarquia)")
                    elif role_found.managed:
                        invalid_roles.append(f"{role_found.name} (gerenciado por bot/integração)")
                    elif role_found == interaction.guild.default_role:
                        invalid_roles.append(f"{role_found.name} (@everyone não permitido)")
                    else:
                        valid_roles.append(role_found)
                else:
                    invalid_roles.append(f"{role_mention} (não encontrado)")

            # 🚨 VERIFICAR SE HÁ ROLES VÁLIDOS
            if not valid_roles:
                await interaction.followup.send(
                    "❌ **Nenhum role válido encontrado!**\n\n"
                    "**❌ Roles inválidos:**\n" + "\n".join([f"• {r}" for r in invalid_roles]),
                    ephemeral=True,
                )
                return

            # ⚠️ AVISAR SOBRE ROLES INVÁLIDOS
            if invalid_roles:
                warning_text = "⚠️ **Alguns roles foram ignorados:**\n" + "\n".join(
                    [f"• {r}" for r in invalid_roles]
                )
                await interaction.followup.send(warning_text, ephemeral=True)

            # 🎨 CRIAR EMBED PRINCIPAL
            embed = discord.Embed(
                title=titulo,
                description=descricao or "Clique nos botões abaixo para adicionar/remover roles!",
                color=0x2F3136,
                timestamp=datetime.now(),
            )

            # 📋 LISTAR ROLES DISPONÍVEIS
            roles_text = ""
            emojis = [
                "🔴",
                "🟠",
                "🟡",
                "🟢",
                "🔵",
                "🟣",
                "🟤",
                "⚫",
                "⚪",
                "🔥",
                "⭐",
                "💎",
                "🎯",
                "🎪",
                "🎨",
                "🎭",
                "🎪",
                "🎹",
                "🎸",
                "🥁",
            ]

            for i, role in enumerate(valid_roles):
                emoji = emojis[i % len(emojis)]
                member_count = len(role.members)
                roles_text += f"{emoji} {role.mention} `({member_count} membros)`\n"

            embed.add_field(
                name=f"🎭 Roles Disponíveis ({len(valid_roles)})", value=roles_text, inline=False
            )

            embed.add_field(
                name="📖 Como usar",
                value="• **Adicionar role:** Clique no botão do role desejado\n"
                "• **Remover role:** Clique novamente no mesmo botão\n"
                "• **Múltiplos roles:** Você pode ter quantos quiser",
                inline=True,
            )

            embed.add_field(
                name="ℹ️ Informações",
                value=f"**Modo:** Botões interativos\n"
                f"**Roles:** {len(valid_roles)} disponíveis\n"
                f"**Configurado por:** {interaction.user.mention}",
                inline=True,
            )

            embed.set_footer(
                text="💡 Clique nos botões para gerenciar seus roles",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            # 🎮 CRIAR BOTÕES (MODO BOTÕES)
            if modo.lower() in ["botoes", "botão", "button", "buttons"]:
                view = discord.ui.View(timeout=None)

                for i, role in enumerate(valid_roles):
                    emoji = emojis[i % len(emojis)]

                    # Criar botão customizado para cada role
                    button = discord.ui.Button(
                        label=f"{role.name}",
                        emoji=emoji,
                        style=discord.ButtonStyle.secondary,
                        custom_id=f"reaction_role_{role.id}",
                    )

                    # Função callback personalizada
                    async def button_callback(interaction_callback, role=role):
                        try:
                            if role in interaction_callback.user.roles:
                                await interaction_callback.user.remove_roles(
                                    role, reason="Reaction Role - Removido"
                                )
                                await interaction_callback.response.send_message(
                                    f"➖ **Role {role.mention} removido!**", ephemeral=True
                                )
                            else:
                                await interaction_callback.user.add_roles(
                                    role, reason="Reaction Role - Adicionado"
                                )
                                await interaction_callback.response.send_message(
                                    f"➕ **Role {role.mention} adicionado!**", ephemeral=True
                                )
                        except discord.Forbidden:
                            await interaction_callback.response.send_message(
                                f"❌ Não tenho permissão para gerenciar o role {role.mention}!",
                                ephemeral=True,
                            )
                        except Exception:
                            await interaction_callback.response.send_message(
                                "❌ Erro ao processar role. Tente novamente.", ephemeral=True
                            )

                    button.callback = button_callback
                    view.add_item(button)

                    # Máximo 25 botões por view (Discord limit)
                    if len(view.children) >= 25:
                        break

                # 📨 ENVIAR MENSAGEM COM BOTÕES
                message = await interaction.channel.send(embed=embed, view=view)

            else:
                # 🎭 MODO REAÇÕES (FALLBACK)
                message = await interaction.channel.send(embed=embed)

                # Adicionar reações
                for i, role in enumerate(valid_roles[:20]):  # Máximo 20 reações
                    emoji = emojis[i % len(emojis)]
                    await message.add_reaction(emoji)

            # 💾 SALVAR CONFIGURAÇÃO NO BANCO
            try:
                from ...utils.database import database

                reaction_role_data = {
                    "message_id": str(message.id),
                    "channel_id": str(interaction.channel.id),
                    "guild_id": str(interaction.guild.id),
                    "roles": [
                        {"role_id": str(r.id), "emoji": emojis[i % len(emojis)]}
                        for i, r in enumerate(valid_roles)
                    ],
                    "mode": modo,
                    "created_by": str(interaction.user.id),
                    "created_at": datetime.now().isoformat(),
                }

                await database.execute(
                    """INSERT INTO reaction_roles 
                       (message_id, channel_id, guild_id, config_data) 
                       VALUES (?, ?, ?, ?)""",
                    (
                        str(message.id),
                        str(interaction.channel.id),
                        str(interaction.guild.id),
                        json.dumps(reaction_role_data),
                    ),
                )
            except Exception as e:
                print(f"❌ Erro ao salvar reaction roles: {e}")

            # ✅ CONFIRMAÇÃO
            success_embed = discord.Embed(
                title="✅ Reaction Roles Configurado!",
                description=f"Sistema instalado com sucesso no canal {interaction.channel.mention}",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="📊 Estatísticas",
                value=f"**Roles configurados:** {len(valid_roles)}\n"
                f"**Modo:** {modo.title()}\n"
                f"**Mensagem:** [Clique aqui]({message.jump_url})",
                inline=True,
            )

            if invalid_roles:
                success_embed.add_field(
                    name="⚠️ Ignorados", value=f"{len(invalid_roles)} roles inválidos", inline=True
                )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando reaction-roles: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao configurar reaction roles. Tente novamente.", ephemeral=True
                )
            except:
                pass


async def setup(bot):
    await bot.add_cog(RoleReaction(bot))
