"""
Sistema de Roles - Gerenciamento de Roles
Comandos para adicionar, remover e gerenciar roles de usuários
"""

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class RoleManage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="role-add", description="➕ Adicionar role para um usuário")
    @app_commands.describe(
        usuario="Usuário que receberá o role",
        role="Role a ser adicionado",
        motivo="Motivo da adição do role",
    )
    async def role_add(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        role: discord.Role,
        motivo: str | None = None,
    ):
        try:
            # 🛡️ VERIFICAR PERMISSÕES
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para gerenciar roles. **Necessário**: Gerenciar Roles",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # 🔍 VERIFICAÇÕES DE SEGURANÇA

            # Verificar se é o próprio bot
            if usuario == interaction.guild.me:
                await interaction.followup.send(
                    "❌ Não posso adicionar roles em mim mesmo!", ephemeral=True
                )
                return

            # Verificar se usuário já tem o role
            if role in usuario.roles:
                await interaction.followup.send(
                    f"ℹ️ {usuario.mention} já possui o role {role.mention}!", ephemeral=True
                )
                return

            # Verificar hierarquia do bot
            if role.position >= interaction.guild.me.top_role.position:
                await interaction.followup.send(
                    f"❌ Não posso adicionar o role {role.mention}!\n"
                    f"**Motivo**: O role está acima da minha hierarquia.\n"
                    f"**Solução**: Mova meu role acima do role `{role.name}`",
                    ephemeral=True,
                )
                return

            # Verificar hierarquia do usuário (para evitar escalação de privilégios)
            if (
                role.position >= interaction.user.top_role.position
                and not interaction.user.guild_permissions.administrator
            ):
                await interaction.followup.send(
                    f"❌ Você não pode adicionar o role {role.mention}!\n"
                    f"**Motivo**: O role está acima da sua hierarquia.",
                    ephemeral=True,
                )
                return

            # Verificar se o role é gerenciado por bot/integração
            if role.managed:
                await interaction.followup.send(
                    f"❌ O role {role.mention} é gerenciado por uma integração/bot!\n"
                    f"**Motivo**: Roles automáticos não podem ser adicionados manualmente.",
                    ephemeral=True,
                )
                return

            # Verificar se é @everyone
            if role == interaction.guild.default_role:
                await interaction.followup.send(
                    "❌ Não posso adicionar o role @everyone!", ephemeral=True
                )
                return

            # ➕ ADICIONAR ROLE
            try:
                reason = (
                    f"Role adicionado por {interaction.user} | {motivo}"
                    if motivo
                    else f"Role adicionado por {interaction.user}"
                )
                await usuario.add_roles(role, reason=reason)

                # 🎨 EMBED DE SUCESSO
                success_embed = discord.Embed(
                    title="✅ **ROLE ADICIONADO!**",
                    color=role.color if role.color != discord.Color.default() else 0x00FF00,
                    timestamp=datetime.now(),
                )

                success_embed.add_field(
                    name="👤 Usuário", value=f"{usuario.mention}\n`{usuario.id}`", inline=True
                )

                success_embed.add_field(
                    name="🎭 Role", value=f"{role.mention}\n`{role.name}`", inline=True
                )

                success_embed.add_field(
                    name="⚖️ Adicionado por",
                    value=f"{interaction.user.mention}\n<t:{int(datetime.now().timestamp())}:R>",
                    inline=True,
                )

                success_embed.add_field(
                    name="📊 Informações do Role",
                    value=f"**Cor:** {role.color}\n"
                    f"**Posição:** #{role.position}\n"
                    f"**Membros:** {len(role.members)} usuários\n"
                    f"**Mencionável:** {'Sim' if role.mentionable else 'Não'}",
                    inline=True,
                )

                if motivo:
                    success_embed.add_field(name="📝 Motivo", value=f"`{motivo}`", inline=True)

                # Permissões do role
                perms = []
                if role.permissions.administrator:
                    perms.append("👑 Administrador")
                elif role.permissions.manage_guild:
                    perms.append("⚙️ Gerenciar Servidor")
                elif role.permissions.manage_roles:
                    perms.append("🎭 Gerenciar Roles")
                elif role.permissions.manage_channels:
                    perms.append("📂 Gerenciar Canais")
                elif role.permissions.kick_members:
                    perms.append("🥾 Expulsar Membros")
                elif role.permissions.ban_members:
                    perms.append("🔨 Banir Membros")

                if perms:
                    success_embed.add_field(
                        name="🔐 Permissões Importantes", value="\n".join(perms[:5]), inline=True
                    )

                success_embed.set_thumbnail(url=usuario.display_avatar.url)
                success_embed.set_footer(
                    text=f"Role ID: {role.id} | User ID: {usuario.id}",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
                )

                await interaction.followup.send(embed=success_embed)

                # 📝 LOG PARA CANAL DE MODERAÇÃO
                try:
                    from ...utils.database import database

                    log_data = await database.get(
                        "SELECT channel_id FROM logs WHERE guild_id = ? AND log_type = 'moderation'",
                        (str(interaction.guild.id),),
                    )

                    if log_data:
                        log_channel = interaction.guild.get_channel(int(log_data["channel_id"]))
                        if log_channel:
                            log_embed = discord.Embed(
                                title="🎭 Role Adicionado",
                                description=f"**Moderador:** {interaction.user.mention}\n"
                                f"**Usuário:** {usuario.mention}\n"
                                f"**Role:** {role.mention}\n"
                                + (
                                    f"**Motivo:** {motivo}"
                                    if motivo
                                    else "**Motivo:** Não especificado"
                                ),
                                color=0x00FF00,
                                timestamp=datetime.now(),
                            )
                            await log_channel.send(embed=log_embed)
                except:
                    pass

            except discord.Forbidden:
                await interaction.followup.send(
                    f"❌ Falha ao adicionar role!\n"
                    f"**Possíveis causas:**\n"
                    f"• Não tenho permissão **Gerenciar Roles**\n"
                    f"• O role {role.mention} está acima da minha hierarquia\n"
                    f"• Problema de permissões no servidor",
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erro inesperado ao adicionar role: {e!s}", ephemeral=True
                )

        except Exception as e:
            print(f"❌ Erro no comando role-add: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao processar comando. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="role-remove", description="➖ Remover role de um usuário")
    @app_commands.describe(
        usuario="Usuário que terá o role removido",
        role="Role a ser removido",
        motivo="Motivo da remoção do role",
    )
    async def role_remove(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        role: discord.Role,
        motivo: str | None = None,
    ):
        try:
            # 🛡️ VERIFICAR PERMISSÕES
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para gerenciar roles. **Necessário**: Gerenciar Roles",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # 🔍 VERIFICAÇÕES DE SEGURANÇA

            # Verificar se usuário tem o role
            if role not in usuario.roles:
                await interaction.followup.send(
                    f"ℹ️ {usuario.mention} não possui o role {role.mention}!", ephemeral=True
                )
                return

            # Verificar hierarquia do bot
            if role.position >= interaction.guild.me.top_role.position:
                await interaction.followup.send(
                    f"❌ Não posso remover o role {role.mention}!\n"
                    f"**Motivo**: O role está acima da minha hierarquia.\n"
                    f"**Solução**: Mova meu role acima do role `{role.name}`",
                    ephemeral=True,
                )
                return

            # Verificar hierarquia do usuário
            if (
                role.position >= interaction.user.top_role.position
                and not interaction.user.guild_permissions.administrator
            ):
                await interaction.followup.send(
                    f"❌ Você não pode remover o role {role.mention}!\n"
                    f"**Motivo**: O role está acima da sua hierarquia.",
                    ephemeral=True,
                )
                return

            # ➖ REMOVER ROLE
            try:
                reason = (
                    f"Role removido por {interaction.user} | {motivo}"
                    if motivo
                    else f"Role removido por {interaction.user}"
                )
                await usuario.remove_roles(role, reason=reason)

                # 🎨 EMBED DE SUCESSO
                success_embed = discord.Embed(
                    title="✅ **ROLE REMOVIDO!**", color=0xFF6B6B, timestamp=datetime.now()
                )

                success_embed.add_field(
                    name="👤 Usuário", value=f"{usuario.mention}\n`{usuario.id}`", inline=True
                )

                success_embed.add_field(
                    name="🎭 Role", value=f"{role.mention}\n`{role.name}`", inline=True
                )

                success_embed.add_field(
                    name="⚖️ Removido por",
                    value=f"{interaction.user.mention}\n<t:{int(datetime.now().timestamp())}:R>",
                    inline=True,
                )

                if motivo:
                    success_embed.add_field(name="📝 Motivo", value=f"`{motivo}`", inline=False)

                success_embed.set_thumbnail(url=usuario.display_avatar.url)
                success_embed.set_footer(
                    text=f"Role ID: {role.id} | User ID: {usuario.id}",
                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
                )

                await interaction.followup.send(embed=success_embed)

                # 📝 LOG PARA CANAL DE MODERAÇÃO
                try:
                    from ...utils.database import database

                    log_data = await database.get(
                        "SELECT channel_id FROM logs WHERE guild_id = ? AND log_type = 'moderation'",
                        (str(interaction.guild.id),),
                    )

                    if log_data:
                        log_channel = interaction.guild.get_channel(int(log_data["channel_id"]))
                        if log_channel:
                            log_embed = discord.Embed(
                                title="🎭 Role Removido",
                                description=f"**Moderador:** {interaction.user.mention}\n"
                                f"**Usuário:** {usuario.mention}\n"
                                f"**Role:** {role.mention}\n"
                                + (
                                    f"**Motivo:** {motivo}"
                                    if motivo
                                    else "**Motivo:** Não especificado"
                                ),
                                color=0xFF6B6B,
                                timestamp=datetime.now(),
                            )
                            await log_channel.send(embed=log_embed)
                except:
                    pass

            except discord.Forbidden:
                await interaction.followup.send(
                    f"❌ Falha ao remover role!\n"
                    f"**Possíveis causas:**\n"
                    f"• Não tenho permissão **Gerenciar Roles**\n"
                    f"• O role {role.mention} está acima da minha hierarquia\n"
                    f"• Problema de permissões no servidor",
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erro inesperado ao remover role: {e!s}", ephemeral=True
                )

        except Exception as e:
            print(f"❌ Erro no comando role-remove: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao processar comando. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(
        name="role-info", description="ℹ️ Mostrar informações detalhadas de um role"
    )
    @app_commands.describe(role="Role para visualizar informações")
    async def role_info(self, interaction: discord.Interaction, role: discord.Role):
        try:
            await interaction.response.defer()

            # 🎨 EMBED DE INFORMAÇÕES
            info_embed = discord.Embed(
                title="🎭 **INFORMAÇÕES DO ROLE**",
                description=f"**Nome:** {role.name}\n**Menção:** {role.mention}",
                color=role.color if role.color != discord.Color.default() else 0x2F3136,
                timestamp=datetime.now(),
            )

            # ℹ️ INFORMAÇÕES BÁSICAS
            info_embed.add_field(
                name="📊 Informações Básicas",
                value=f"**ID:** `{role.id}`\n"
                f"**Posição:** #{role.position}\n"
                f"**Cor:** {role.color}\n"
                f"**Criado:** <t:{int(role.created_at.timestamp())}:F>",
                inline=True,
            )

            # 👥 MEMBROS
            member_count = len(role.members)
            info_embed.add_field(
                name="👥 Membros",
                value=f"**Total:** {member_count} usuários\n"
                f"**Porcentagem:** {(member_count / interaction.guild.member_count) * 100:.1f}% do servidor",
                inline=True,
            )

            # ⚙️ CONFIGURAÇÕES
            info_embed.add_field(
                name="⚙️ Configurações",
                value=f"**Mencionável:** {'✅ Sim' if role.mentionable else '❌ Não'}\n"
                f"**Separado:** {'✅ Sim' if role.hoist else '❌ Não'}\n"
                f"**Gerenciado:** {'✅ Bot/Integração' if role.managed else '❌ Manual'}",
                inline=True,
            )

            # 🔐 PERMISSÕES IMPORTANTES
            important_perms = []
            if role.permissions.administrator:
                important_perms.append("👑 **Administrador**")
            if role.permissions.manage_guild:
                important_perms.append("⚙️ Gerenciar Servidor")
            if role.permissions.manage_roles:
                important_perms.append("🎭 Gerenciar Roles")
            if role.permissions.manage_channels:
                important_perms.append("📂 Gerenciar Canais")
            if role.permissions.kick_members:
                important_perms.append("🥾 Expulsar Membros")
            if role.permissions.ban_members:
                important_perms.append("🔨 Banir Membros")
            if role.permissions.manage_messages:
                important_perms.append("🧹 Gerenciar Mensagens")
            if role.permissions.mention_everyone:
                important_perms.append("📢 Mencionar Everyone")

            if important_perms:
                info_embed.add_field(
                    name="🔐 Permissões Importantes",
                    value="\n".join(important_perms[:8]),
                    inline=False,
                )
            else:
                info_embed.add_field(
                    name="🔐 Permissões", value="Apenas permissões básicas", inline=False
                )

            # 👥 ALGUNS MEMBROS (se não for muitos)
            if member_count > 0 and member_count <= 20:
                members_list = [m.mention for m in role.members[:10]]
                members_text = ", ".join(members_list)
                if member_count > 10:
                    members_text += f" e mais {member_count - 10} membros..."

                info_embed.add_field(
                    name=f"👥 Membros ({member_count})", value=members_text, inline=False
                )

            # 🏷️ TAGS
            tags = []
            if role == interaction.guild.default_role:
                tags.append("@everyone")
            if role.managed:
                tags.append("Gerenciado automaticamente")
            if role.position >= interaction.guild.me.top_role.position:
                tags.append("Acima do bot")
            if role.permissions.administrator:
                tags.append("Administrador")

            if tags:
                info_embed.add_field(name="🏷️ Tags", value=" • ".join(tags), inline=False)

            info_embed.set_footer(
                text=f"Role criado em {role.created_at.strftime('%d/%m/%Y')} • ID: {role.id}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            await interaction.followup.send(embed=info_embed)

        except Exception as e:
            print(f"❌ Erro no comando role-info: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao buscar informações do role. Tente novamente.", ephemeral=True
                )
            except:
                pass


async def setup(bot):
    await bot.add_cog(RoleManage(bot))
