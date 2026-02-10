"""
Sistema de Container Builder
Sistema para criação e gerenciamento de containers customizados
"""

import json
import os
import sqlite3
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class ContainerSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.join("src", "data", "containers.db")
        self.templates = {}
        self.init_database()
        self.load_templates()

    def init_database(self):
        """Inicializar banco de dados de containers"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS containers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                template_data TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                is_public BOOLEAN DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, name)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS container_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (container_id) REFERENCES containers (id)
            )
        """)

        conn.commit()
        conn.close()

    def load_templates(self):
        """Carregar templates de containers pré-definidos"""
        self.templates = {
            "anuncio": {
                "name": "Anúncio Padrão",
                "description": "Template para anúncios importantes",
                "embed": {
                    "title": "📢 **ANÚNCIO IMPORTANTE**",
                    "color": 0x00FF00,
                    "fields": [
                        {"name": "📋 Título", "value": "[TÍTULO DO ANÚNCIO]", "inline": False},
                        {"name": "📝 Descrição", "value": "[CONTEÚDO PRINCIPAL]", "inline": False},
                        {
                            "name": "👤 Responsável",
                            "value": "[NOME DO RESPONSÁVEL]",
                            "inline": True,
                        },
                        {"name": "📅 Data", "value": "[DATA/PRAZO]", "inline": True},
                    ],
                    "footer": {"text": "Anúncio Oficial"},
                },
            },
            "evento": {
                "name": "Evento do Servidor",
                "description": "Template para divulgação de eventos",
                "embed": {
                    "title": "🎉 **EVENTO DO SERVIDOR**",
                    "color": 0xFF6B6B,
                    "fields": [
                        {"name": "🎯 Nome do Evento", "value": "[NOME DO EVENTO]", "inline": False},
                        {"name": "📝 Descrição", "value": "[DESCRIÇÃO DO EVENTO]", "inline": False},
                        {"name": "📅 Data e Hora", "value": "[DIA/HORÁRIO]", "inline": True},
                        {"name": "📍 Local/Canal", "value": "[LOCAL OU CANAL]", "inline": True},
                        {
                            "name": "🎁 Premiação",
                            "value": "[PRÊMIOS OU RECOMPENSAS]",
                            "inline": False,
                        },
                        {
                            "name": "📋 Requisitos",
                            "value": "[REQUISITOS PARA PARTICIPAR]",
                            "inline": False,
                        },
                    ],
                    "footer": {"text": "Evento Oficial • Não perca!"},
                },
            },
            "regras": {
                "name": "Regras do Servidor",
                "description": "Template para apresentação de regras",
                "embed": {
                    "title": "📜 **REGRAS DO SERVIDOR**",
                    "color": 0x3742FA,
                    "fields": [
                        {
                            "name": "1️⃣ Respeito",
                            "value": "Trate todos com respeito e cordialidade",
                            "inline": False,
                        },
                        {
                            "name": "2️⃣ Spam",
                            "value": "Não faça spam ou flood nos canais",
                            "inline": False,
                        },
                        {
                            "name": "3️⃣ Conteúdo Inadequado",
                            "value": "Proibido conteúdo NSFW ou ofensivo",
                            "inline": False,
                        },
                        {
                            "name": "4️⃣ Canais",
                            "value": "Use os canais apropriados para cada tipo de conversa",
                            "inline": False,
                        },
                        {
                            "name": "⚠️ Punições",
                            "value": "Violações podem resultar em warn, mute ou ban",
                            "inline": False,
                        },
                    ],
                    "footer": {"text": "Leia todas as regras • Última atualização"},
                },
            },
            "suporte": {
                "name": "Ticket de Suporte",
                "description": "Template para sistema de suporte",
                "embed": {
                    "title": "🎫 **SISTEMA DE SUPORTE**",
                    "color": 0x2ED573,
                    "fields": [
                        {
                            "name": "❓ Precisa de Ajuda?",
                            "value": "Clique no botão abaixo para abrir um ticket",
                            "inline": False,
                        },
                        {
                            "name": "📝 Como Funciona",
                            "value": "Um canal privado será criado para você conversar com a equipe",
                            "inline": False,
                        },
                        {
                            "name": "⏱️ Tempo de Resposta",
                            "value": "Geralmente respondemos em até 24 horas",
                            "inline": True,
                        },
                        {
                            "name": "🔒 Privacidade",
                            "value": "Suas informações ficam protegidas",
                            "inline": True,
                        },
                    ],
                    "footer": {"text": "Suporte Oficial • Estamos aqui para ajudar"},
                },
            },
            "welcome": {
                "name": "Boas-vindas",
                "description": "Template para mensagem de boas-vindas",
                "embed": {
                    "title": "🎉 **BEM-VINDO(A)!**",
                    "color": 0x5F27CD,
                    "fields": [
                        {
                            "name": "👋 Olá [NOME]!",
                            "value": "Seja muito bem-vindo(a) ao nosso servidor!",
                            "inline": False,
                        },
                        {
                            "name": "📋 Primeiro Passo",
                            "value": "Leia as regras em #regras",
                            "inline": True,
                        },
                        {
                            "name": "💬 Segundo Passo",
                            "value": "Se apresente em #apresentações",
                            "inline": True,
                        },
                        {
                            "name": "🎯 Canais Importantes",
                            "value": "#anúncios - #regras - #suporte",
                            "inline": False,
                        },
                        {
                            "name": "🎊 Aproveite!",
                            "value": "Esperamos que você se divirta aqui!",
                            "inline": False,
                        },
                    ],
                    "footer": {"text": "Você é o membro nº [NÚMERO] do servidor!"},
                },
            },
        }

    @app_commands.command(
        name="container-create", description="📦 Criar novo container personalizado"
    )
    @app_commands.describe(
        nome="Nome único para o container",
        template="Template base (opcional)",
        publico="Tornar disponível para outros usuários",
    )
    @app_commands.choices(
        template=[
            app_commands.Choice(name="Anúncio", value="anuncio"),
            app_commands.Choice(name="Evento", value="evento"),
            app_commands.Choice(name="Regras", value="regras"),
            app_commands.Choice(name="Suporte", value="suporte"),
            app_commands.Choice(name="Boas-vindas", value="welcome"),
            app_commands.Choice(name="Vazio", value="empty"),
        ]
    )
    async def container_create(
        self,
        interaction: discord.Interaction,
        nome: str,
        template: str | None = "empty",
        publico: bool | None = False,
    ):
        try:
            # Validar nome
            if len(nome) < 3 or len(nome) > 30:
                await interaction.response.send_message(
                    "❌ **Nome Inválido**\nO nome deve ter entre 3 e 30 caracteres.", ephemeral=True
                )
                return

            # Verificar se já existe
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id FROM containers 
                WHERE guild_id = ? AND name = ?
            """,
                (str(interaction.guild.id), nome),
            )

            if cursor.fetchone():
                conn.close()
                await interaction.response.send_message(
                    f"❌ **Container Já Existe**\nJá existe um container com o nome `{nome}`.",
                    ephemeral=True,
                )
                return

            # Criar template base
            if template == "empty":
                template_data = {
                    "embed": {
                        "title": f"📦 {nome}",
                        "description": "Container personalizado criado pelo usuário",
                        "color": 0x6C5CE7,
                        "fields": [],
                        "footer": {"text": "Container Personalizado"},
                    }
                }
            elif template in self.templates:
                template_data = self.templates[template].copy()
            else:
                template_data = self.templates["anuncio"].copy()

            # Salvar no banco
            cursor.execute(
                """
                INSERT INTO containers 
                (guild_id, name, description, template_data, creator_id, is_public)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    str(interaction.guild.id),
                    nome,
                    f"Container criado por {interaction.user.display_name}",
                    json.dumps(template_data),
                    str(interaction.user.id),
                    publico,
                ),
            )

            container_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # Criar embed de confirmação
            embed = discord.Embed(
                title="📦 **CONTAINER CRIADO**", color=0x00FF00, timestamp=datetime.now()
            )

            embed.add_field(name="📝 Nome", value=f"`{nome}`", inline=True)

            embed.add_field(name="🎨 Template", value=template.title(), inline=True)

            embed.add_field(
                name="🌐 Visibilidade", value="Público" if publico else "Privado", inline=True
            )

            embed.add_field(name="🆔 ID", value=f"`{container_id}`", inline=True)

            embed.add_field(name="👤 Criador", value=interaction.user.mention, inline=True)

            embed.add_field(
                name="📋 Comandos Úteis",
                value="• `/container-edit` - Editar\n• `/container-send` - Enviar\n• `/container-view` - Visualizar",
                inline=False,
            )

            embed.set_footer(
                text=f"Use /container-edit {nome} para personalizar",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando container-create: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao criar container.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="container-list", description="📋 Listar containers disponíveis")
    @app_commands.describe(filtro="Filtrar containers por tipo")
    @app_commands.choices(
        filtro=[
            app_commands.Choice(name="Todos", value="all"),
            app_commands.Choice(name="Meus", value="mine"),
            app_commands.Choice(name="Públicos", value="public"),
            app_commands.Choice(name="Templates", value="templates"),
        ]
    )
    async def container_list(self, interaction: discord.Interaction, filtro: str | None = "all"):
        try:
            embed = discord.Embed(
                title="📋 **LISTA DE CONTAINERS**", color=0x6C5CE7, timestamp=datetime.now()
            )

            if filtro == "templates":
                # Mostrar templates predefinidos
                templates_text = ""
                for key, template in self.templates.items():
                    templates_text += f"**{key}** - {template['name']}\n"
                    templates_text += f"   *{template['description']}*\n\n"

                embed.add_field(
                    name="🎨 Templates Predefinidos",
                    value=templates_text[:1000] + ("..." if len(templates_text) > 1000 else ""),
                    inline=False,
                )

                embed.add_field(
                    name="💡 Como Usar",
                    value="Use `/container-create` e escolha um template base!",
                    inline=False,
                )

            else:
                # Buscar containers do banco
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                if filtro == "mine":
                    cursor.execute(
                        """
                        SELECT id, name, description, creator_id, is_public, usage_count, created_at
                        FROM containers 
                        WHERE guild_id = ? AND creator_id = ?
                        ORDER BY created_at DESC
                    """,
                        (str(interaction.guild.id), str(interaction.user.id)),
                    )
                elif filtro == "public":
                    cursor.execute(
                        """
                        SELECT id, name, description, creator_id, is_public, usage_count, created_at
                        FROM containers 
                        WHERE guild_id = ? AND is_public = 1
                        ORDER BY usage_count DESC
                    """,
                        (str(interaction.guild.id),),
                    )
                else:  # all
                    cursor.execute(
                        """
                        SELECT id, name, description, creator_id, is_public, usage_count, created_at
                        FROM containers 
                        WHERE guild_id = ? AND (is_public = 1 OR creator_id = ?)
                        ORDER BY created_at DESC
                    """,
                        (str(interaction.guild.id), str(interaction.user.id)),
                    )

                containers = cursor.fetchall()
                conn.close()

                if not containers:
                    embed.add_field(
                        name="📭 Nenhum Container",
                        value="Nenhum container encontrado com os filtros especificados.",
                        inline=False,
                    )
                else:
                    containers_text = ""
                    for i, (id, name, desc, creator_id, is_public, usage, created_at) in enumerate(
                        containers[:10]
                    ):
                        visibility = "🌐" if is_public else "🔒"

                        try:
                            creator = await self.bot.fetch_user(int(creator_id))
                            creator_name = creator.display_name
                        except:
                            creator_name = f"ID: {creator_id}"

                        created_timestamp = int(datetime.fromisoformat(created_at).timestamp())

                        containers_text += f"{visibility} **{name}** (ID: `{id}`)\n"
                        containers_text += f"   👤 {creator_name} • 📊 {usage} usos • <t:{created_timestamp}:R>\n\n"

                    embed.add_field(
                        name=f"📦 Containers ({len(containers)} encontrados)",
                        value=containers_text[:1000]
                        + ("..." if len(containers_text) > 1000 else ""),
                        inline=False,
                    )

                    if len(containers) > 10:
                        embed.add_field(
                            name="➕ Mais Containers",
                            value=f"E mais **{len(containers) - 10}** containers...",
                            inline=False,
                        )

            embed.add_field(
                name="🔧 Comandos Úteis",
                value="• `/container-create` - Criar novo\n• `/container-send [nome]` - Enviar\n• `/container-view [nome]` - Ver detalhes",
                inline=False,
            )

            embed.set_footer(
                text=f"Filtro: {filtro} | Solicitado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando container-list: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao listar containers.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="container-send", description="📤 Enviar container para o canal")
    @app_commands.describe(
        nome="Nome do container para enviar", canal="Canal de destino (padrão: atual)"
    )
    async def container_send(
        self,
        interaction: discord.Interaction,
        nome: str,
        canal: discord.TextChannel | None = None,
    ):
        try:
            if canal is None:
                canal = interaction.channel

            # Verificar permissões
            permissions = canal.permissions_for(interaction.guild.me)
            if not permissions.send_messages or not permissions.embed_links:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\n"
                    f"Não tenho permissões para enviar embeds em {canal.mention}.",
                    ephemeral=True,
                )
                return

            # Buscar container
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, template_data, creator_id, is_public
                FROM containers 
                WHERE guild_id = ? AND name = ?
            """,
                (str(interaction.guild.id), nome),
            )

            result = cursor.fetchone()

            if not result:
                conn.close()
                await interaction.response.send_message(
                    f"❌ **Container Não Encontrado**\nNão existe um container chamado `{nome}`.",
                    ephemeral=True,
                )
                return

            container_id, template_data, creator_id, is_public = result

            # Verificar permissões de uso
            if not is_public and str(interaction.user.id) != creator_id:
                if not interaction.user.guild_permissions.manage_messages:
                    conn.close()
                    await interaction.response.send_message(
                        "❌ **Container Privado**\n"
                        "Este container é privado e você não tem permissão para usá-lo.",
                        ephemeral=True,
                    )
                    return

            # Atualizar contador de uso
            cursor.execute(
                """
                UPDATE containers 
                SET usage_count = usage_count + 1, updated_at = ?
                WHERE id = ?
            """,
                (datetime.now(), container_id),
            )

            # Registrar uso
            cursor.execute(
                """
                INSERT INTO container_usage 
                (container_id, user_id, channel_id)
                VALUES (?, ?, ?)
            """,
                (container_id, str(interaction.user.id), str(canal.id)),
            )

            conn.commit()
            conn.close()

            # Processar template
            template = json.loads(template_data)

            # Substituir variáveis padrão
            template_str = json.dumps(template)
            template_str = template_str.replace("[NOME]", interaction.user.display_name)
            template_str = template_str.replace("[SERVIDOR]", interaction.guild.name)
            template_str = template_str.replace("[CANAL]", canal.name)
            template_str = template_str.replace("[DATA]", datetime.now().strftime("%d/%m/%Y"))
            template_str = template_str.replace("[HORA]", datetime.now().strftime("%H:%M"))
            template_str = template_str.replace("[NUMERO]", str(interaction.guild.member_count))

            template = json.loads(template_str)

            # Criar e enviar embed
            if "embed" in template:
                embed_data = template["embed"]
                embed = discord.Embed(
                    title=embed_data.get("title", "Container"),
                    description=embed_data.get("description"),
                    color=embed_data.get("color", 0x6C5CE7),
                )

                # Adicionar fields
                for field in embed_data.get("fields", []):
                    embed.add_field(
                        name=field["name"], value=field["value"], inline=field.get("inline", False)
                    )

                # Footer
                if "footer" in embed_data:
                    embed.set_footer(text=embed_data["footer"]["text"])

                # Thumbnail e imagem
                if "thumbnail" in embed_data:
                    embed.set_thumbnail(url=embed_data["thumbnail"])
                if "image" in embed_data:
                    embed.set_image(url=embed_data["image"])

                message_content = template.get("content", None)
                sent_message = await canal.send(content=message_content, embed=embed)
            else:
                sent_message = await canal.send(template.get("content", "Container enviado!"))

            # Confirmação
            confirm_embed = discord.Embed(
                title="📤 **CONTAINER ENVIADO**", color=0x00FF00, timestamp=datetime.now()
            )

            confirm_embed.add_field(name="📦 Container", value=f"`{nome}`", inline=True)

            confirm_embed.add_field(name="📢 Canal", value=canal.mention, inline=True)

            confirm_embed.add_field(
                name="🔗 Link", value=f"[Ver Mensagem]({sent_message.jump_url})", inline=True
            )

            confirm_embed.set_footer(
                text="Container enviado com sucesso", icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando container-send: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Erro ao enviar container.", ephemeral=True
                )
            except:
                pass


async def setup(bot):
    await bot.add_cog(ContainerSystem(bot))
