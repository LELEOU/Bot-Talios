"""
Sistema de Backup - Backup Completo do Servidor
Sistema avançado para criar e restaurar backups do servidor
"""

import asyncio
import json
from datetime import datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands


class BackupCreateModal(discord.ui.Modal):
    """Modal para configurar backup"""

    def __init__(self, guild: discord.Guild, user: discord.Member):
        super().__init__(title=f"📦 Criar Backup - {guild.name}", timeout=300)
        self.guild = guild
        self.user = user

        # Nome do backup
        self.backup_name = discord.ui.TextInput(
            label="Nome do Backup",
            placeholder=f"Backup-{guild.name}-{datetime.now().strftime('%d%m%Y')}",
            required=True,
            max_length=100,
            default=f"Backup-{guild.name}-{datetime.now().strftime('%d%m%Y')}",
        )

        # Descrição
        self.backup_description = discord.ui.TextInput(
            label="Descrição do Backup",
            placeholder="Descreva o motivo ou contexto deste backup...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500,
        )

        # Configurações de inclusão
        self.include_settings = discord.ui.TextInput(
            label="Incluir (separado por vírgulas)",
            placeholder="roles,channels,permissions,emojis,webhooks",
            required=False,
            max_length=200,
            default="roles,channels,permissions,emojis",
        )

        self.add_item(self.backup_name)
        self.add_item(self.backup_description)
        self.add_item(self.include_settings)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            # Processar configurações
            include_options = [
                opt.strip().lower() for opt in self.include_settings.value.split(",") if opt.strip()
            ]
            if not include_options:
                include_options = ["roles", "channels", "permissions"]

            # Criar dados do backup
            backup_data = await self.create_backup_data(include_options)

            # Gerar ID único do backup
            backup_id = f"backup_{self.guild.id}_{int(datetime.now().timestamp())}"

            # Salvar no banco de dados
            try:
                from ...utils.database import database

                backup_info = {
                    "id": backup_id,
                    "guild_id": str(self.guild.id),
                    "name": self.backup_name.value,
                    "description": self.backup_description.value,
                    "created_by": str(self.user.id),
                    "created_at": datetime.now().isoformat(),
                    "guild_name": self.guild.name,
                    "member_count": self.guild.member_count,
                    "included_features": include_options,
                    "backup_size": len(json.dumps(backup_data)),
                }

                await database.execute(
                    """INSERT INTO server_backups 
                    (backup_id, guild_id, backup_name, backup_data, backup_info, created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        backup_id,
                        str(self.guild.id),
                        self.backup_name.value,
                        json.dumps(backup_data),
                        json.dumps(backup_info),
                        datetime.now().isoformat(),
                        str(self.user.id),
                    ),
                )

            except Exception as e:
                print(f"❌ Erro ao salvar backup: {e}")
                await interaction.followup.send(
                    "❌ Erro ao salvar backup no banco de dados.", ephemeral=True
                )
                return

            # Criar embed de confirmação
            success_embed = discord.Embed(
                title="✅ **BACKUP CRIADO COM SUCESSO**",
                description=f"Backup do servidor `{self.guild.name}` foi criado!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            # Estatísticas do backup
            stats = backup_data.get("statistics", {})

            success_embed.add_field(
                name="📦 Informações do Backup",
                value=f"**Nome:** {self.backup_name.value}\n"
                f"**ID:** `{backup_id[:20]}...`\n"
                f"**Tamanho:** {len(json.dumps(backup_data)) / 1024:.1f} KB",
                inline=True,
            )

            success_embed.add_field(
                name="📊 Conteúdo Salvo",
                value=f"**Canais:** {stats.get('channels', 0)}\n"
                f"**Roles:** {stats.get('roles', 0)}\n"
                f"**Emojis:** {stats.get('emojis', 0)}\n"
                f"**Webhooks:** {stats.get('webhooks', 0)}",
                inline=True,
            )

            success_embed.add_field(
                name="🔧 Funcionalidades Incluídas",
                value="\n".join([f"✅ {opt.title()}" for opt in include_options]),
                inline=False,
            )

            if self.backup_description.value:
                success_embed.add_field(
                    name="📝 Descrição", value=self.backup_description.value, inline=False
                )

            success_embed.add_field(
                name="💡 Como Usar",
                value=f"`/backup-list` - Ver todos os backups\n"
                f"`/backup-restore {backup_id[:8]}` - Restaurar backup\n"
                f"`/backup-info {backup_id[:8]}` - Ver detalhes",
                inline=False,
            )

            success_embed.set_thumbnail(url=self.guild.icon.url if self.guild.icon else None)
            success_embed.set_footer(
                text=f"Criado por {self.user}", icon_url=self.user.display_avatar.url
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no backup modal: {e}")
            try:
                await interaction.followup.send("❌ Erro ao processar backup.", ephemeral=True)
            except:
                pass

    async def create_backup_data(self, include_options: list[str]) -> dict[str, Any]:
        """Cria os dados completos do backup"""
        backup_data = {
            "version": "2.0",
            "created_at": datetime.now().isoformat(),
            "guild_info": {
                "name": self.guild.name,
                "id": str(self.guild.id),
                "description": self.guild.description,
                "icon_url": str(self.guild.icon.url) if self.guild.icon else None,
                "banner_url": str(self.guild.banner.url) if self.guild.banner else None,
                "member_count": self.guild.member_count,
                "verification_level": str(self.guild.verification_level),
                "explicit_content_filter": str(self.guild.explicit_content_filter),
                "default_notifications": str(self.guild.default_notifications),
                "preferred_locale": str(self.guild.preferred_locale),
            },
            "statistics": {},
            "data": {},
        }

        try:
            # Backup de Roles
            if "roles" in include_options:
                roles_data = []
                for role in self.guild.roles:
                    if role.name != "@everyone":  # Pular @everyone
                        role_data = {
                            "name": role.name,
                            "color": role.color.value,
                            "permissions": role.permissions.value,
                            "position": role.position,
                            "hoist": role.hoist,
                            "mentionable": role.mentionable,
                            "managed": role.managed,
                            "icon": str(role.icon.url) if role.icon else None,
                        }
                        roles_data.append(role_data)

                backup_data["data"]["roles"] = roles_data
                backup_data["statistics"]["roles"] = len(roles_data)

            # Backup de Canais
            if "channels" in include_options:
                channels_data = []

                for channel in self.guild.channels:
                    channel_data = {
                        "name": channel.name,
                        "type": str(channel.type),
                        "position": channel.position,
                        "category_id": str(channel.category.id) if channel.category else None,
                    }

                    # Dados específicos por tipo
                    if isinstance(channel, discord.TextChannel):
                        channel_data.update(
                            {
                                "topic": channel.topic,
                                "slowmode_delay": channel.slowmode_delay,
                                "nsfw": channel.nsfw,
                                "news": channel.news if hasattr(channel, "news") else False,
                            }
                        )
                    elif isinstance(channel, discord.VoiceChannel):
                        channel_data.update(
                            {
                                "bitrate": channel.bitrate,
                                "user_limit": channel.user_limit,
                                "rtc_region": str(channel.rtc_region)
                                if channel.rtc_region
                                else None,
                            }
                        )
                    elif isinstance(channel, discord.CategoryChannel):
                        channel_data["is_category"] = True

                    # Permissões do canal
                    if "permissions" in include_options:
                        overwrites = []
                        for target, overwrite in channel.overwrites.items():
                            overwrites.append(
                                {
                                    "id": str(target.id),
                                    "type": "role"
                                    if isinstance(target, discord.Role)
                                    else "member",
                                    "allow": overwrite.pair()[0].value,
                                    "deny": overwrite.pair()[1].value,
                                }
                            )
                        channel_data["overwrites"] = overwrites

                    channels_data.append(channel_data)

                backup_data["data"]["channels"] = channels_data
                backup_data["statistics"]["channels"] = len(channels_data)

            # Backup de Emojis
            if "emojis" in include_options:
                emojis_data = []
                for emoji in self.guild.emojis:
                    emoji_data = {
                        "name": emoji.name,
                        "animated": emoji.animated,
                        "url": str(emoji.url),
                        "managed": emoji.managed,
                        "available": emoji.available,
                        "require_colons": emoji.require_colons,
                    }
                    emojis_data.append(emoji_data)

                backup_data["data"]["emojis"] = emojis_data
                backup_data["statistics"]["emojis"] = len(emojis_data)

            # Backup de Webhooks
            if "webhooks" in include_options:
                webhooks_data = []
                try:
                    webhooks = await self.guild.webhooks()
                    for webhook in webhooks:
                        webhook_data = {
                            "name": webhook.name,
                            "channel_id": str(webhook.channel.id) if webhook.channel else None,
                            "avatar_url": str(webhook.avatar.url) if webhook.avatar else None,
                            "user_id": str(webhook.user.id) if webhook.user else None,
                        }
                        webhooks_data.append(webhook_data)

                    backup_data["data"]["webhooks"] = webhooks_data
                    backup_data["statistics"]["webhooks"] = len(webhooks_data)
                except:
                    backup_data["statistics"]["webhooks"] = 0

            # Configurações do servidor
            if "settings" in include_options:
                settings_data = {
                    "verification_level": str(self.guild.verification_level),
                    "explicit_content_filter": str(self.guild.explicit_content_filter),
                    "default_notifications": str(self.guild.default_notifications),
                    "mfa_level": self.guild.mfa_level,
                    "premium_tier": self.guild.premium_tier,
                    "premium_subscribers": self.guild.premium_subscription_count,
                    "features": list(self.guild.features),
                    "system_channel_id": str(self.guild.system_channel.id)
                    if self.guild.system_channel
                    else None,
                    "rules_channel_id": str(self.guild.rules_channel.id)
                    if self.guild.rules_channel
                    else None,
                    "public_updates_channel_id": str(self.guild.public_updates_channel.id)
                    if self.guild.public_updates_channel
                    else None,
                }
                backup_data["data"]["settings"] = settings_data

        except Exception as e:
            print(f"❌ Erro ao criar backup data: {e}")

        return backup_data


class ServerBackup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_in_progress = set()
        self.restore_in_progress = set()

    @app_commands.command(name="backup-create", description="📦 Criar backup completo do servidor")
    async def backup_create(self, interaction: discord.Interaction):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Você precisa de permissão de **Administrador** para criar backups do servidor.",
                    ephemeral=True,
                )
                return

            # Verificar se já há backup em progresso
            if interaction.guild.id in self.backup_in_progress:
                await interaction.response.send_message(
                    "⏳ Já existe um backup sendo criado para este servidor. Aguarde a conclusão.",
                    ephemeral=True,
                )
                return

            # Adicionar à lista de backups em progresso
            self.backup_in_progress.add(interaction.guild.id)

            try:
                # Abrir modal de configuração
                modal = BackupCreateModal(interaction.guild, interaction.user)
                await interaction.response.send_modal(modal)
            finally:
                # Remover da lista após 5 minutos (timeout do modal)
                await asyncio.sleep(300)
                self.backup_in_progress.discard(interaction.guild.id)

        except Exception as e:
            print(f"❌ Erro no comando backup-create: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao iniciar criação de backup.", ephemeral=True
                )
            except:
                pass


async def setup(bot):
    await bot.add_cog(ServerBackup(bot))
