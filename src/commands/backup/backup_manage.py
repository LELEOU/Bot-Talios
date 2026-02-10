"""
Sistema de Backup - Lista e Restauração
Gerenciamento e restauração de backups do servidor
"""

import asyncio
import json
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class BackupRestoreConfirmView(discord.ui.View):
    """View de confirmação para restaurar backup"""

    def __init__(self, backup_data: dict, user: discord.Member):
        super().__init__(timeout=300)
        self.backup_data = backup_data
        self.user = user
        self.confirmed = False

    @discord.ui.button(label="✅ Confirmar Restauração", style=discord.ButtonStyle.danger)
    async def confirm_restore(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Apenas quem solicitou a restauração pode confirmar.", ephemeral=True
            )
            return

        self.confirmed = True

        # Desabilitar todos os botões
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="⏳ **INICIANDO RESTAURAÇÃO...**\nEsta operação pode levar alguns minutos.",
            view=self,
        )

        self.stop()

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel_restore(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Apenas quem solicitou a restauração pode cancelar.", ephemeral=True
            )
            return

        self.confirmed = False

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="❌ **RESTAURAÇÃO CANCELADA**\nNenhuma alteração foi feita no servidor.",
            view=self,
        )

        self.stop()


class BackupListView(discord.ui.View):
    """View de paginação para lista de backups"""

    def __init__(self, backups: list[dict], user: discord.Member, per_page: int = 5):
        super().__init__(timeout=300)
        self.backups = backups
        self.user = user
        self.per_page = per_page
        self.current_page = 0
        self.max_page = (len(backups) - 1) // per_page

        # Desabilitar botões se necessário
        if self.max_page == 0:
            self.prev_button.disabled = True
            self.next_button.disabled = True
        else:
            self.prev_button.disabled = True  # Primeira página

    def get_page_embed(self) -> discord.Embed:
        """Gera embed da página atual"""
        start_idx = self.current_page * self.per_page
        end_idx = start_idx + self.per_page
        page_backups = self.backups[start_idx:end_idx]

        embed = discord.Embed(
            title="📦 **LISTA DE BACKUPS**",
            description=f"Página {self.current_page + 1}/{self.max_page + 1} • Total: {len(self.backups)} backups",
            color=0x4A90E2,
            timestamp=datetime.now(),
        )

        for i, backup in enumerate(page_backups, start_idx + 1):
            backup_info = json.loads(backup.get("backup_info", "{}"))
            created_date = datetime.fromisoformat(backup["created_at"])

            # Informações básicas
            info_text = f"**ID:** `{backup['backup_id'][:16]}...`\n"
            info_text += f"**Servidor:** {backup_info.get('guild_name', 'Nome não encontrado')}\n"
            info_text += f"**Criado em:** {created_date.strftime('%d/%m/%Y às %H:%M')}\n"
            info_text += f"**Tamanho:** {backup_info.get('backup_size', 0) / 1024:.1f} KB"

            # Descrição se houver
            description = backup_info.get("description", "").strip()
            if description:
                info_text += (
                    f"\n**Descrição:** {description[:100]}{'...' if len(description) > 100 else ''}"
                )

            # Features incluídas
            features = backup_info.get("included_features", [])
            if features:
                info_text += (
                    f"\n**Inclui:** {', '.join(features[:3])}{'...' if len(features) > 3 else ''}"
                )

            embed.add_field(name=f"📦 {backup['backup_name']}", value=info_text, inline=False)

        if not page_backups:
            embed.add_field(
                name="📭 Nenhum Backup",
                value="Não há backups criados para este servidor.\nUse `/backup-create` para criar o primeiro backup.",
                inline=False,
            )

        embed.set_footer(
            text=f"Use /backup-info <id> para ver detalhes • Solicitado por {self.user}",
            icon_url=self.user.display_avatar.url,
        )

        return embed

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Apenas quem solicitou pode navegar.", ephemeral=True
            )
            return

        self.current_page -= 1

        # Atualizar estado dos botões
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = False

        embed = self.get_page_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Apenas quem solicitou pode navegar.", ephemeral=True
            )
            return

        self.current_page += 1

        # Atualizar estado dos botões
        self.next_button.disabled = self.current_page == self.max_page
        self.prev_button.disabled = False

        embed = self.get_page_embed()
        await interaction.response.edit_message(embed=embed, view=self)


class BackupManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.restore_in_progress = set()

    @app_commands.command(name="backup-list", description="📋 Ver lista de backups do servidor")
    @app_commands.describe(todos="Ver backups de todos os servidores (apenas para proprietários)")
    async def backup_list(self, interaction: discord.Interaction, todos: bool | None = False):
        try:
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para ver backups.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar backups
            try:
                from ...utils.database import database

                if todos and interaction.user.id == interaction.guild.owner_id:
                    # Todos os backups (apenas owner)
                    backups = await database.get_all(
                        "SELECT * FROM server_backups ORDER BY created_at DESC", ()
                    )
                else:
                    # Apenas do servidor atual
                    backups = await database.get_all(
                        "SELECT * FROM server_backups WHERE guild_id = ? ORDER BY created_at DESC",
                        (str(interaction.guild.id),),
                    )

            except Exception as e:
                print(f"❌ Erro ao buscar backups: {e}")
                await interaction.followup.send(
                    "❌ Erro ao consultar backups no banco de dados.", ephemeral=True
                )
                return

            if not backups:
                empty_embed = discord.Embed(
                    title="📦 **NENHUM BACKUP ENCONTRADO**",
                    description="Não há backups criados para este servidor.",
                    color=0xFF6B6B,
                    timestamp=datetime.now(),
                )

                empty_embed.add_field(
                    name="💡 Como Criar um Backup",
                    value="Use o comando `/backup-create` para criar seu primeiro backup.\n"
                    "Os backups incluem:\n"
                    "• Canais e categorias\n"
                    "• Roles e permissões\n"
                    "• Emojis personalizados\n"
                    "• Webhooks\n"
                    "• Configurações do servidor",
                    inline=False,
                )

                await interaction.followup.send(embed=empty_embed, ephemeral=True)
                return

            # Criar view de paginação
            view = BackupListView(backups, interaction.user)
            embed = view.get_page_embed()

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando backup-list: {e}")
            try:
                await interaction.followup.send("❌ Erro ao listar backups.", ephemeral=True)
            except:
                pass

    @app_commands.command(
        name="backup-info", description="ℹ️ Ver informações detalhadas de um backup"
    )
    @app_commands.describe(backup_id="ID do backup (primeiros caracteres suficientes)")
    async def backup_info(self, interaction: discord.Interaction, backup_id: str):
        try:
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para ver informações de backups.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar backup
            try:
                from ...utils.database import database

                backup = await database.get(
                    "SELECT * FROM server_backups WHERE guild_id = ? AND backup_id LIKE ?",
                    (str(interaction.guild.id), f"{backup_id}%"),
                )

                if not backup:
                    await interaction.followup.send(
                        f"❌ **Backup não encontrado**\n"
                        f"Nenhum backup encontrado com ID: `{backup_id}`\n\n"
                        f"💡 Use `/backup-list` para ver todos os backups disponíveis.",
                        ephemeral=True,
                    )
                    return

            except Exception as e:
                print(f"❌ Erro ao buscar backup: {e}")
                await interaction.followup.send("❌ Erro ao consultar backup.", ephemeral=True)
                return

            # Processar dados do backup
            backup_info = json.loads(backup.get("backup_info", "{}"))
            backup_data = json.loads(backup.get("backup_data", "{}"))

            created_date = datetime.fromisoformat(backup["created_at"])
            creator = interaction.guild.get_member(int(backup["created_by"]))
            creator_name = creator.display_name if creator else "Usuário não encontrado"

            # Embed principal
            info_embed = discord.Embed(
                title="ℹ️ **INFORMAÇÕES DO BACKUP**",
                description=f"**{backup['backup_name']}**",
                color=0x4A90E2,
                timestamp=created_date,
            )

            # Informações básicas
            info_embed.add_field(
                name="📦 Detalhes Básicos",
                value=f"**ID:** `{backup['backup_id'][:20]}...`\n"
                f"**Servidor:** {backup_info.get('guild_name', 'N/A')}\n"
                f"**Criado por:** {creator_name}\n"
                f"**Data:** {created_date.strftime('%d/%m/%Y às %H:%M')}\n"
                f"**Tamanho:** {backup_info.get('backup_size', 0) / 1024:.1f} KB",
                inline=True,
            )

            # Estatísticas do conteúdo
            stats = backup_data.get("statistics", {})
            stats_text = ""
            if stats:
                for key, value in stats.items():
                    emoji_map = {
                        "channels": "📺",
                        "roles": "🎭",
                        "emojis": "😀",
                        "webhooks": "🔗",
                        "permissions": "🔒",
                    }
                    emoji = emoji_map.get(key, "📊")
                    stats_text += f"{emoji} **{key.title()}:** {value}\n"

            if stats_text:
                info_embed.add_field(name="📊 Conteúdo Salvo", value=stats_text, inline=True)

            # Descrição se houver
            description = backup_info.get("description", "").strip()
            if description:
                info_embed.add_field(name="📝 Descrição", value=description, inline=False)

            # Funcionalidades incluídas
            features = backup_info.get("included_features", [])
            if features:
                features_text = "\n".join([f"✅ {feature.title()}" for feature in features])
                info_embed.add_field(
                    name="🔧 Funcionalidades Incluídas", value=features_text, inline=True
                )

            # Informações do servidor original
            guild_info = backup_data.get("guild_info", {})
            if guild_info:
                server_text = f"**Membros:** {guild_info.get('member_count', 'N/A')}\n"
                server_text += f"**Verificação:** {guild_info.get('verification_level', 'N/A')}\n"
                server_text += (
                    f"**Filtro Conteúdo:** {guild_info.get('explicit_content_filter', 'N/A')}\n"
                )

                premium_tier = guild_info.get("premium_tier", 0)
                server_text += f"**Nível Premium:** {premium_tier}/3"

                info_embed.add_field(name="🏠 Servidor Original", value=server_text, inline=True)

            # Comandos úteis
            info_embed.add_field(
                name="💡 Comandos Úteis",
                value=f"`/backup-restore {backup_id}` - Restaurar este backup\n"
                f"`/backup-delete {backup_id}` - Excluir backup\n"
                f"`/backup-list` - Ver todos os backups",
                inline=False,
            )

            # Aviso importante
            info_embed.add_field(
                name="⚠️ **IMPORTANTE**",
                value="A restauração de um backup substituirá completamente a configuração atual do servidor. "
                "Esta ação é irreversível!",
                inline=False,
            )

            info_embed.set_footer(
                text=f"Consultado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=info_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando backup-info: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao consultar informações do backup.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="backup-restore", description="🔄 Restaurar backup do servidor")
    @app_commands.describe(backup_id="ID do backup para restaurar")
    async def backup_restore(self, interaction: discord.Interaction, backup_id: str):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Você precisa de permissão de **Administrador** para restaurar backups.",
                    ephemeral=True,
                )
                return

            # Verificar se já há restauração em progresso
            if interaction.guild.id in self.restore_in_progress:
                await interaction.response.send_message(
                    "⏳ Já existe uma restauração em progresso para este servidor.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar backup
            try:
                from ...utils.database import database

                backup = await database.get(
                    "SELECT * FROM server_backups WHERE guild_id = ? AND backup_id LIKE ?",
                    (str(interaction.guild.id), f"{backup_id}%"),
                )

                if not backup:
                    await interaction.followup.send(
                        f"❌ Backup não encontrado com ID: `{backup_id}`", ephemeral=True
                    )
                    return

            except Exception as e:
                print(f"❌ Erro ao buscar backup: {e}")
                await interaction.followup.send("❌ Erro ao consultar backup.", ephemeral=True)
                return

            # Processar dados
            backup_info = json.loads(backup.get("backup_info", "{}"))
            backup_data = json.loads(backup.get("backup_data", "{}"))

            # Embed de confirmação
            confirm_embed = discord.Embed(
                title="⚠️ **CONFIRMAÇÃO DE RESTAURAÇÃO**",
                description=f"Você está prestes a restaurar o backup:\n**{backup['backup_name']}**",
                color=0xFFA500,
                timestamp=datetime.now(),
            )

            confirm_embed.add_field(
                name="🔄 O que será restaurado:",
                value="• Todos os canais serão **deletados** e recriados\n"
                "• Todas as roles serão **removidas** e recriadas\n"
                "• Permissões serão **redefinidas**\n"
                "• Emojis personalizados serão **substituídos**\n"
                "• Webhooks serão **recriados**",
                inline=False,
            )

            confirm_embed.add_field(
                name="⚠️ **ATENÇÃO CRÍTICA**",
                value="• **Esta ação é IRREVERSÍVEL**\n"
                "• **TODO o conteúdo atual será PERDIDO**\n"
                "• **Mensagens NÃO são incluídas no backup**\n"
                "• **Membros permanecerão no servidor**\n"
                "• **Pode levar vários minutos para concluir**",
                inline=False,
            )

            # Estatísticas do que será restaurado
            stats = backup_data.get("statistics", {})
            if stats:
                stats_text = ""
                for key, value in stats.items():
                    stats_text += f"• {key.title()}: {value}\n"

                confirm_embed.add_field(
                    name="📊 Conteúdo a ser restaurado:", value=stats_text, inline=True
                )

            confirm_embed.add_field(
                name="❓ Tem certeza?",
                value="Clique em **✅ Confirmar Restauração** apenas se tiver **absoluta certeza**.\n"
                "Recomendamos criar um backup atual antes de prosseguir.",
                inline=False,
            )

            # View de confirmação
            view = BackupRestoreConfirmView(backup_data, interaction.user)

            await interaction.followup.send(embed=confirm_embed, view=view, ephemeral=True)

            # Aguardar confirmação
            await view.wait()

            if view.confirmed:
                # Adicionar à lista de restaurações em progresso
                self.restore_in_progress.add(interaction.guild.id)

                try:
                    await self.perform_restore(interaction, backup_data, backup_info)
                finally:
                    self.restore_in_progress.discard(interaction.guild.id)

        except Exception as e:
            print(f"❌ Erro no comando backup-restore: {e}")
            self.restore_in_progress.discard(interaction.guild.id)
            try:
                await interaction.followup.send(
                    "❌ Erro ao processar restauração do backup.", ephemeral=True
                )
            except:
                pass

    async def perform_restore(
        self, interaction: discord.Interaction, backup_data: dict, backup_info: dict
    ):
        """Executa a restauração completa do backup"""
        try:
            guild = interaction.guild

            # Status embed
            status_embed = discord.Embed(
                title="🔄 **RESTAURAÇÃO EM PROGRESSO**",
                description="Restaurando backup, por favor aguarde...",
                color=0xFFA500,
                timestamp=datetime.now(),
            )

            # Fase 1: Deletar canais existentes
            status_embed.add_field(
                name="📺 Fase 1: Removendo canais",
                value="Deletando canais existentes...",
                inline=False,
            )

            await interaction.edit_original_response(embed=status_embed, view=None)

            # Deletar todos os canais (exceto o canal onde o comando foi executado, se possível)
            channels_to_delete = [ch for ch in guild.channels if ch.id != interaction.channel.id]
            for channel in channels_to_delete:
                try:
                    await channel.delete(reason="Restauração de backup")
                    await asyncio.sleep(0.5)  # Rate limit
                except:
                    pass

            # Fase 2: Deletar roles existentes
            status_embed.clear_fields()
            status_embed.add_field(
                name="🎭 Fase 2: Removendo roles",
                value="Deletando roles existentes...",
                inline=False,
            )
            await interaction.edit_original_response(embed=status_embed)

            # Deletar roles (exceto @everyone e roles de bots)
            roles_to_delete = [
                role for role in guild.roles if not role.is_default() and not role.managed
            ]
            for role in roles_to_delete:
                try:
                    await role.delete(reason="Restauração de backup")
                    await asyncio.sleep(0.3)
                except:
                    pass

            # Fase 3: Recriar roles
            status_embed.clear_fields()
            status_embed.add_field(
                name="🎭 Fase 3: Recriando roles", value="Criando roles do backup...", inline=False
            )
            await interaction.edit_original_response(embed=status_embed)

            role_mapping = {}  # Mapear IDs antigos para novos

            if "roles" in backup_data.get("data", {}):
                for role_data in backup_data["data"]["roles"]:
                    try:
                        new_role = await guild.create_role(
                            name=role_data["name"],
                            permissions=discord.Permissions(role_data["permissions"]),
                            color=discord.Color(role_data["color"]),
                            hoist=role_data["hoist"],
                            mentionable=role_data["mentionable"],
                            reason="Restauração de backup",
                        )
                        await asyncio.sleep(0.3)
                    except:
                        pass

            # Fase 4: Recriar canais
            status_embed.clear_fields()
            status_embed.add_field(
                name="📺 Fase 4: Recriando canais",
                value="Criando canais do backup...",
                inline=False,
            )
            await interaction.edit_original_response(embed=status_embed)

            if "channels" in backup_data.get("data", {}):
                # Primeiro criar categorias
                category_mapping = {}
                for channel_data in backup_data["data"]["channels"]:
                    if channel_data.get("is_category"):
                        try:
                            new_category = await guild.create_category(
                                name=channel_data["name"], reason="Restauração de backup"
                            )
                            category_mapping[channel_data.get("id")] = new_category
                            await asyncio.sleep(0.3)
                        except:
                            pass

                # Depois criar outros canais
                for channel_data in backup_data["data"]["channels"]:
                    if not channel_data.get("is_category"):
                        try:
                            category = None
                            if channel_data.get("category_id"):
                                category = category_mapping.get(channel_data["category_id"])

                            if channel_data["type"] == "text":
                                new_channel = await guild.create_text_channel(
                                    name=channel_data["name"],
                                    topic=channel_data.get("topic"),
                                    slowmode_delay=channel_data.get("slowmode_delay", 0),
                                    nsfw=channel_data.get("nsfw", False),
                                    category=category,
                                    reason="Restauração de backup",
                                )
                            elif channel_data["type"] == "voice":
                                new_channel = await guild.create_voice_channel(
                                    name=channel_data["name"],
                                    bitrate=channel_data.get("bitrate", 64000),
                                    user_limit=channel_data.get("user_limit", 0),
                                    category=category,
                                    reason="Restauração de backup",
                                )

                            await asyncio.sleep(0.5)
                        except:
                            pass

            # Sucesso!
            success_embed = discord.Embed(
                title="✅ **BACKUP RESTAURADO COM SUCESSO**",
                description="A restauração foi concluída!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="🎉 Concluído",
                value="O servidor foi restaurado para o estado do backup.\n"
                "Algumas configurações avançadas podem precisar ser reajustadas manualmente.",
                inline=False,
            )

            success_embed.add_field(
                name="📝 Próximos Passos",
                value="• Verifique as configurações de permissões\n"
                "• Reconfigure bots se necessário\n"
                "• Teste as funcionalidades importantes\n"
                "• Considere criar um novo backup atual",
                inline=False,
            )

            await interaction.edit_original_response(embed=success_embed, view=None)

        except Exception as e:
            print(f"❌ Erro na restauração: {e}")

            error_embed = discord.Embed(
                title="❌ **ERRO NA RESTAURAÇÃO**",
                description="Ocorreu um erro durante a restauração do backup.",
                color=0xFF0000,
                timestamp=datetime.now(),
            )

            error_embed.add_field(
                name="🔧 O que fazer:",
                value="• Verifique as permissões do bot\n"
                "• Tente novamente em alguns minutos\n"
                "• Contate o suporte se o problema persistir",
                inline=False,
            )

            try:
                await interaction.edit_original_response(embed=error_embed, view=None)
            except:
                pass


async def setup(bot):
    await bot.add_cog(BackupManagement(bot))
