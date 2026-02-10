"""
Sistema de Welcome - Configuração e Mensagens de Boas-vindas
Comando para configurar mensagens personalizadas de entrada
"""

import json
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class WelcomePreview(discord.ui.View):
    """Preview das mensagens de boas-vindas"""

    def __init__(self, welcome_config, user):
        super().__init__(timeout=300)
        self.welcome_config = welcome_config
        self.user = user

    @discord.ui.button(label="📝 Editar Mensagem", style=discord.ButtonStyle.secondary)
    async def edit_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WelcomeEditModal(self.welcome_config)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🎨 Editar Embed", style=discord.ButtonStyle.primary)
    async def edit_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WelcomeEmbedModal(self.welcome_config)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="✅ Confirmar & Salvar", style=discord.ButtonStyle.success)
    async def confirm_save(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Salvar configuração no banco
            from ...utils.database import database

            config_json = json.dumps(self.welcome_config)

            # Verificar se já existe
            existing = await database.get(
                "SELECT * FROM welcome_config WHERE guild_id = ?", (str(interaction.guild.id),)
            )

            if existing:
                await database.execute(
                    "UPDATE welcome_config SET config_data = ? WHERE guild_id = ?",
                    (config_json, str(interaction.guild.id)),
                )
            else:
                await database.execute(
                    "INSERT INTO welcome_config (guild_id, config_data) VALUES (?, ?)",
                    (str(interaction.guild.id), config_json),
                )

            success_embed = discord.Embed(
                title="✅ **Sistema de Boas-vindas Salvo!**",
                description="As configurações foram salvas com sucesso!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            success_embed.add_field(
                name="📍 Canal", value=f"<#{self.welcome_config['channel_id']}>", inline=True
            )

            success_embed.add_field(
                name="🎯 Status",
                value="✅ Ativo" if self.welcome_config["enabled"] else "❌ Desativo",
                inline=True,
            )

            success_embed.add_field(
                name="💡 Teste", value="Use `/welcome-test` para testar o sistema", inline=True
            )

            await interaction.response.edit_message(embed=success_embed, view=None)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao salvar configuração: {e}", ephemeral=True
            )


class WelcomeEditModal(discord.ui.Modal):
    """Modal para editar mensagem de texto"""

    def __init__(self, welcome_config):
        super().__init__(title="📝 Editar Mensagem de Boas-vindas")
        self.welcome_config = welcome_config

        self.message = discord.ui.TextInput(
            label="Mensagem de texto (opcional)",
            placeholder="Digite uma mensagem ou deixe vazio para apenas embed...",
            default=self.welcome_config.get("message", ""),
            required=False,
            max_length=1000,
            style=discord.TextStyle.long,
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        self.welcome_config["message"] = self.message.value

        await interaction.response.send_message(
            '✅ **Mensagem atualizada!** Use o botão "Confirmar & Salvar" para salvar as alterações.',
            ephemeral=True,
        )


class WelcomeEmbedModal(discord.ui.Modal):
    """Modal para editar embed"""

    def __init__(self, welcome_config):
        super().__init__(title="🎨 Editar Embed de Boas-vindas")
        self.welcome_config = welcome_config

        embed_config = self.welcome_config.get("embed", {})

        self.title = discord.ui.TextInput(
            label="Título do embed",
            placeholder="Ex: Bem-vindo ao servidor!",
            default=embed_config.get("title", ""),
            required=False,
            max_length=256,
        )

        self.description = discord.ui.TextInput(
            label="Descrição",
            placeholder="Use {user}, {server}, {count} para variáveis...",
            default=embed_config.get("description", ""),
            required=False,
            max_length=1000,
            style=discord.TextStyle.long,
        )

        self.color = discord.ui.TextInput(
            label="Cor (hex, ex: #ff0000)",
            placeholder="Ex: #00ff00",
            default=embed_config.get("color", "#2f3136"),
            required=False,
            max_length=7,
        )

        self.footer = discord.ui.TextInput(
            label="Rodapé (footer)",
            placeholder="Ex: Membro #{count}",
            default=embed_config.get("footer", ""),
            required=False,
            max_length=200,
        )

        self.add_item(self.title)
        self.add_item(self.description)
        self.add_item(self.color)
        self.add_item(self.footer)

    async def on_submit(self, interaction: discord.Interaction):
        # Validar cor
        color_value = self.color.value
        if color_value:
            if not color_value.startswith("#"):
                color_value = "#" + color_value

            try:
                int(color_value[1:], 16)
            except:
                color_value = "#2f3136"
        else:
            color_value = "#2f3136"

        self.welcome_config["embed"] = {
            "title": self.title.value,
            "description": self.description.value,
            "color": color_value,
            "footer": self.footer.value,
            "enabled": True,
        }

        await interaction.response.send_message(
            '✅ **Embed atualizado!** Use o botão "Confirmar & Salvar" para salvar as alterações.',
            ephemeral=True,
        )


class WelcomeSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def replace_variables(self, text: str, member: discord.Member) -> str:
        """Substitui variáveis na mensagem"""
        replacements = {
            "{user}": member.mention,
            "{username}": member.name,
            "{discriminator}": member.discriminator,
            "{user.id}": str(member.id),
            "{server}": member.guild.name,
            "{server.name}": member.guild.name,
            "{server.id}": str(member.guild.id),
            "{count}": str(member.guild.member_count),
            "{member.count}": str(member.guild.member_count),
        }

        for var, value in replacements.items():
            text = text.replace(var, value)

        return text

    @app_commands.command(name="welcome-setup", description="👋 Configurar sistema de boas-vindas")
    @app_commands.describe(
        canal="Canal onde as mensagens de boas-vindas aparecerão",
        ativo="Ativar ou desativar o sistema",
    )
    async def welcome_setup(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        ativo: bool | None = True,
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para configurar boas-vindas. **Necessário**: Gerenciar Servidor",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Verificar permissões do bot no canal
            permissions = canal.permissions_for(interaction.guild.me)
            missing_perms = []

            if not permissions.send_messages:
                missing_perms.append("Enviar Mensagens")
            if not permissions.embed_links:
                missing_perms.append("Inserir Links")

            if missing_perms:
                await interaction.followup.send(
                    f"❌ **Permissões insuficientes no canal {canal.mention}!**\n\n"
                    f"**🔐 Permissões necessárias:**\n"
                    + "\n".join([f"• {perm}" for perm in missing_perms]),
                    ephemeral=True,
                )
                return

            # Configuração padrão
            welcome_config = {
                "channel_id": str(canal.id),
                "enabled": ativo,
                "message": f"👋 Bem-vindo(a) ao **{interaction.guild.name}**, {{user}}!",
                "embed": {
                    "enabled": True,
                    "title": "🎉 Novo membro!",
                    "description": "Olá {user}! Bem-vindo(a) ao **{server}**!\n\n"
                    "Você é nosso **membro #{count}**!\n\n"
                    "📋 Leia as regras\n"
                    "💬 Participe dos chats\n"
                    "🎮 Divirta-se!",
                    "color": "#00ff00",
                    "footer": "Membro #{count} • Bem-vindo!",
                },
            }

            # Buscar configuração existente
            try:
                from ...utils.database import database

                existing = await database.get(
                    "SELECT config_data FROM welcome_config WHERE guild_id = ?",
                    (str(interaction.guild.id),),
                )

                if existing:
                    try:
                        existing_config = json.loads(existing["config_data"])
                        # Manter configurações existentes, apenas atualizar canal e status
                        existing_config["channel_id"] = str(canal.id)
                        existing_config["enabled"] = ativo
                        welcome_config = existing_config
                    except:
                        pass  # Usar configuração padrão
            except Exception as e:
                print(f"❌ Erro ao buscar config existente: {e}")

            # Criar preview
            preview_embed = discord.Embed(
                title="👋 **CONFIGURAR BOAS-VINDAS**",
                description="Configure sua mensagem de boas-vindas personalizada!",
                color=0x2F3136,
                timestamp=datetime.now(),
            )

            preview_embed.add_field(name="📍 Canal", value=canal.mention, inline=True)

            preview_embed.add_field(
                name="🎯 Status", value="✅ Ativo" if ativo else "❌ Desativo", inline=True
            )

            preview_embed.add_field(
                name="⚙️ Configuração", value="Use os botões abaixo para personalizar", inline=True
            )

            # Preview da mensagem atual
            if welcome_config["message"]:
                preview_message = self.replace_variables(
                    welcome_config["message"], interaction.user
                )
                preview_embed.add_field(
                    name="💬 Prévia da Mensagem",
                    value=f"`{preview_message[:200]}{'...' if len(preview_message) > 200 else ''}`",
                    inline=False,
                )

            # Preview do embed
            if welcome_config["embed"]["enabled"]:
                embed_config = welcome_config["embed"]
                preview_title = self.replace_variables(embed_config["title"], interaction.user)
                preview_desc = self.replace_variables(embed_config["description"], interaction.user)

                preview_embed.add_field(
                    name="🎨 Prévia do Embed",
                    value=f"**Título:** {preview_title[:50]}{'...' if len(preview_title) > 50 else ''}\n"
                    f"**Descrição:** {preview_desc[:100]}{'...' if len(preview_desc) > 100 else ''}\n"
                    f"**Cor:** {embed_config['color']}",
                    inline=False,
                )

            preview_embed.add_field(
                name="🔧 Variáveis Disponíveis",
                value="`{user}` - Menção do usuário\n"
                "`{username}` - Nome do usuário\n"
                "`{server}` - Nome do servidor\n"
                "`{count}` - Número de membros",
                inline=True,
            )

            preview_embed.add_field(
                name="💡 Dicas",
                value="• Use **markdown** para formatar\n"
                "• Embeds são mais visuais\n"
                "• Teste com `/welcome-test`",
                inline=True,
            )

            preview_embed.set_footer(
                text="Use os botões para personalizar sua mensagem",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            view = WelcomePreview(welcome_config, interaction.user)

            await interaction.followup.send(embed=preview_embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando welcome-setup: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao configurar sistema de boas-vindas. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="welcome-test", description="🧪 Testar sistema de boas-vindas")
    async def welcome_test(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            # Buscar configuração
            try:
                from ...utils.database import database

                config = await database.get(
                    "SELECT config_data FROM welcome_config WHERE guild_id = ?",
                    (str(interaction.guild.id),),
                )

                if not config:
                    await interaction.followup.send(
                        "❌ **Sistema não configurado!**\n"
                        "Use `/welcome-setup` para configurar primeiro.",
                        ephemeral=True,
                    )
                    return

                welcome_config = json.loads(config["config_data"])

            except Exception as e:
                print(f"❌ Erro ao buscar config: {e}")
                await interaction.followup.send("❌ Erro ao carregar configuração.", ephemeral=True)
                return

            if not welcome_config["enabled"]:
                await interaction.followup.send(
                    "⚠️ **Sistema desativado!**\n"
                    "O sistema de boas-vindas está desativado. Use `/welcome-setup` para ativar.",
                    ephemeral=True,
                )
                return

            # Buscar canal
            channel = interaction.guild.get_channel(int(welcome_config["channel_id"]))
            if not channel:
                await interaction.followup.send(
                    "❌ **Canal não encontrado!**\n"
                    "O canal configurado pode ter sido deletado. Reconfigure o sistema.",
                    ephemeral=True,
                )
                return

            # Enviar mensagem de teste
            try:
                content = None
                embed = None

                # Processar mensagem de texto
                if welcome_config.get("message"):
                    content = self.replace_variables(welcome_config["message"], interaction.user)
                    content = f"🧪 **TESTE** {content}"

                # Processar embed
                if welcome_config.get("embed", {}).get("enabled"):
                    embed_config = welcome_config["embed"]

                    embed = discord.Embed(
                        title=f"🧪 TESTE - {self.replace_variables(embed_config['title'], interaction.user)}",
                        description=self.replace_variables(
                            embed_config["description"], interaction.user
                        ),
                        color=int(embed_config["color"].replace("#", ""), 16),
                        timestamp=datetime.now(),
                    )

                    if embed_config.get("footer"):
                        embed.set_footer(
                            text=self.replace_variables(embed_config["footer"], interaction.user),
                            icon_url=interaction.user.display_avatar.url,
                        )

                    embed.set_thumbnail(url=interaction.user.display_avatar.url)

                # Enviar teste
                test_message = await channel.send(content=content, embed=embed)

                # Confirmação
                success_embed = discord.Embed(
                    title="🧪 **Teste Enviado!**",
                    description=f"Mensagem de teste enviada em {channel.mention}",
                    color=0x00FF00,
                    timestamp=datetime.now(),
                )

                success_embed.add_field(name="📍 Canal", value=channel.mention, inline=True)

                success_embed.add_field(
                    name="🔗 Link", value=f"[Ver mensagem]({test_message.jump_url})", inline=True
                )

                success_embed.add_field(
                    name="💡 Próximo passo",
                    value="A mensagem será enviada automaticamente quando novos membros entrarem!",
                    inline=False,
                )

                await interaction.followup.send(embed=success_embed, ephemeral=True)

            except discord.Forbidden:
                await interaction.followup.send(
                    f"❌ **Sem permissão para enviar em {channel.mention}!**\n"
                    "Verifique se tenho as permissões necessárias no canal.",
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao enviar teste: {e}", ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando welcome-test: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao testar sistema. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Event listener para novos membros"""
        try:
            # Buscar configuração
            from ...utils.database import database

            config = await database.get(
                "SELECT config_data FROM welcome_config WHERE guild_id = ?", (str(member.guild.id),)
            )

            if not config:
                return

            welcome_config = json.loads(config["config_data"])

            if not welcome_config["enabled"]:
                return

            # Buscar canal
            channel = member.guild.get_channel(int(welcome_config["channel_id"]))
            if not channel:
                return

            # Preparar conteúdo
            content = None
            embed = None

            # Mensagem de texto
            if welcome_config.get("message"):
                content = self.replace_variables(welcome_config["message"], member)

            # Embed
            if welcome_config.get("embed", {}).get("enabled"):
                embed_config = welcome_config["embed"]

                embed = discord.Embed(
                    title=self.replace_variables(embed_config["title"], member),
                    description=self.replace_variables(embed_config["description"], member),
                    color=int(embed_config["color"].replace("#", ""), 16),
                    timestamp=datetime.now(),
                )

                if embed_config.get("footer"):
                    embed.set_footer(
                        text=self.replace_variables(embed_config["footer"], member),
                        icon_url=member.display_avatar.url,
                    )

                embed.set_thumbnail(url=member.display_avatar.url)

            # Enviar mensagem
            await channel.send(content=content, embed=embed)

        except Exception as e:
            print(f"❌ Erro no evento welcome: {e}")


async def setup(bot):
    await bot.add_cog(WelcomeSetup(bot))
