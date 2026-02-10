"""
Sistema de Cases Moderativos
Gerenciamento completo de casos de moderação com histórico
"""

import os
import sqlite3
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class CaseSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.join("src", "data", "cases.db")
        self.init_database()

    def init_database(self):
        """Inicializar banco de dados de cases"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mod_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                moderator_id TEXT NOT NULL,
                type TEXT NOT NULL,
                reason TEXT,
                evidence TEXT,
                duration TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(guild_id, case_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                guild_id TEXT NOT NULL,
                attachment_url TEXT NOT NULL,
                attachment_name TEXT,
                uploaded_by TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES mod_cases (case_id)
            )
        """)

        conn.commit()
        conn.close()

    def get_next_case_id(self, guild_id: str) -> int:
        """Obter próximo ID de case para o servidor"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT MAX(case_id) FROM mod_cases WHERE guild_id = ?
        """,
            (guild_id,),
        )

        result = cursor.fetchone()
        conn.close()

        return (result[0] or 0) + 1

    def get_case_emoji_color(self, case_type: str) -> tuple:
        """Obter emoji e cor baseado no tipo do case"""
        case_configs = {
            "warning": ("⚠️", 0xFFFF00),
            "mute": ("🔇", 0xFF9900),
            "kick": ("👢", 0xFF6600),
            "ban": ("🔨", 0xFF0000),
            "ban_temp": ("⏰", 0xFF3300),
            "unban": ("🔓", 0x00FF00),
            "unmute": ("🔊", 0x00FF00),
            "note": ("📝", 0x0099FF),
        }

        return case_configs.get(case_type, ("📝", 0x0099FF))

    @app_commands.command(name="case-create", description="📝 Criar um novo case moderativo")
    @app_commands.describe(
        user="Usuário do case",
        tipo="Tipo de moderação",
        motivo="Motivo da ação moderativa",
        evidencia="Links ou provas (opcional)",
    )
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="Aviso", value="warning"),
            app_commands.Choice(name="Mute", value="mute"),
            app_commands.Choice(name="Kick", value="kick"),
            app_commands.Choice(name="Ban", value="ban"),
            app_commands.Choice(name="Ban Temporário", value="ban_temp"),
            app_commands.Choice(name="Unban", value="unban"),
            app_commands.Choice(name="Unmute", value="unmute"),
            app_commands.Choice(name="Nota", value="note"),
        ]
    )
    @app_commands.default_permissions(moderate_members=True)
    async def case_create(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        tipo: str,
        motivo: str,
        evidencia: str | None = None,
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para criar cases moderativos.",
                    ephemeral=True,
                )
                return

            # Obter próximo ID do case
            case_id = self.get_next_case_id(str(interaction.guild.id))

            # Salvar no banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO mod_cases 
                (case_id, guild_id, user_id, moderator_id, type, reason, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    case_id,
                    str(interaction.guild.id),
                    str(user.id),
                    str(interaction.user.id),
                    tipo,
                    motivo,
                    evidencia,
                ),
            )

            conn.commit()
            conn.close()

            # Obter emoji e cor
            emoji, color = self.get_case_emoji_color(tipo)

            # Criar embed
            embed = discord.Embed(
                title=f"{emoji} **CASE #{case_id} CRIADO**", color=color, timestamp=datetime.now()
            )

            embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)

            embed.add_field(
                name="👮 Moderador",
                value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                inline=True,
            )

            embed.add_field(
                name="📋 Tipo", value=f"**{tipo.replace('_', ' ').title()}**", inline=True
            )

            embed.add_field(
                name="📝 Motivo",
                value=motivo[:500] + ("..." if len(motivo) > 500 else ""),
                inline=False,
            )

            if evidencia:
                embed.add_field(
                    name="🔍 Evidência",
                    value=evidencia[:300] + ("..." if len(evidencia) > 300 else ""),
                    inline=False,
                )

            embed.set_thumbnail(url=user.display_avatar.url)

            embed.set_footer(
                text=f"Case ID: {case_id}", icon_url=interaction.user.display_avatar.url
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando case-create: {e}")
            try:
                await interaction.response.send_message("❌ Erro ao criar case.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="case-view", description="👁️ Ver detalhes de um case")
    @app_commands.describe(case_id="ID do case para visualizar")
    @app_commands.default_permissions(moderate_members=True)
    async def case_view(self, interaction: discord.Interaction, case_id: int):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para ver cases moderativos.",
                    ephemeral=True,
                )
                return

            # Buscar case no banco
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM mod_cases 
                WHERE guild_id = ? AND case_id = ?
            """,
                (str(interaction.guild.id), case_id),
            )

            case_data = cursor.fetchone()

            if not case_data:
                await interaction.response.send_message(
                    f"❌ **Case Não Encontrado**\nCase #{case_id} não existe neste servidor.",
                    ephemeral=True,
                )
                return

            # Buscar anexos
            cursor.execute(
                """
                SELECT attachment_url, attachment_name, uploaded_by, uploaded_at
                FROM case_attachments 
                WHERE guild_id = ? AND case_id = ?
            """,
                (str(interaction.guild.id), case_id),
            )

            attachments = cursor.fetchall()
            conn.close()

            # Extrair dados do case
            (
                id,
                case_id,
                guild_id,
                user_id,
                moderator_id,
                case_type,
                reason,
                evidence,
                duration,
                created_at,
                updated_at,
                is_active,
            ) = case_data

            # Buscar informações dos usuários
            try:
                target_user = await self.bot.fetch_user(int(user_id))
            except:
                target_user = None

            try:
                moderator = await self.bot.fetch_user(int(moderator_id))
            except:
                moderator = None

            # Obter emoji e cor
            emoji, color = self.get_case_emoji_color(case_type)

            # Criar embed
            embed = discord.Embed(
                title=f"{emoji} **CASE #{case_id}**",
                color=color,
                timestamp=datetime.fromisoformat(created_at),
            )

            # Status do case
            status = "🟢 Ativo" if is_active else "🔴 Inativo"
            embed.add_field(name="📊 Status", value=status, inline=True)

            embed.add_field(
                name="📋 Tipo", value=f"**{case_type.replace('_', ' ').title()}**", inline=True
            )

            if duration:
                embed.add_field(name="⏰ Duração", value=duration, inline=True)

            # Usuário
            user_info = target_user.mention if target_user else f"ID: {user_id}"
            if target_user:
                user_info += f"\n`{target_user.name}#{target_user.discriminator}`\n`{user_id}`"

            embed.add_field(name="👤 Usuário", value=user_info, inline=True)

            # Moderador
            mod_info = moderator.mention if moderator else f"ID: {moderator_id}"
            if moderator:
                mod_info += f"\n`{moderator.name}#{moderator.discriminator}`\n`{moderator_id}`"

            embed.add_field(name="👮 Moderador", value=mod_info, inline=True)

            # Timestamps
            created_timestamp = int(datetime.fromisoformat(created_at).timestamp())
            embed.add_field(
                name="📅 Criado",
                value=f"<t:{created_timestamp}:R>\n<t:{created_timestamp}:F>",
                inline=True,
            )

            # Motivo
            embed.add_field(name="📝 Motivo", value=reason or "Não especificado", inline=False)

            # Evidência
            if evidence:
                embed.add_field(
                    name="🔍 Evidência",
                    value=evidence[:500] + ("..." if len(evidence) > 500 else ""),
                    inline=False,
                )

            # Anexos
            if attachments:
                attachments_text = ""
                for i, (url, name, uploaded_by, uploaded_at) in enumerate(attachments[:5]):
                    uploader = await self.bot.fetch_user(int(uploaded_by))
                    uploader_name = uploader.display_name if uploader else f"ID: {uploaded_by}"
                    attachments_text += f"[{name or f'Anexo {i + 1}'}]({url}) - {uploader_name}\n"

                embed.add_field(name="📎 Anexos", value=attachments_text, inline=False)

            if target_user:
                embed.set_thumbnail(url=target_user.display_avatar.url)

            embed.set_footer(
                text=f"Case ID: {case_id} | DB ID: {id}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando case-view: {e}")
            try:
                await interaction.response.send_message("❌ Erro ao buscar case.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="case-list", description="📋 Listar cases de um usuário")
    @app_commands.describe(
        user="Usuário para listar cases (opcional)",
        tipo="Filtrar por tipo (opcional)",
        limite="Número máximo de cases (padrão: 10)",
    )
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="Todos", value="all"),
            app_commands.Choice(name="Avisos", value="warning"),
            app_commands.Choice(name="Mutes", value="mute"),
            app_commands.Choice(name="Kicks", value="kick"),
            app_commands.Choice(name="Bans", value="ban"),
            app_commands.Choice(name="Notas", value="note"),
        ]
    )
    @app_commands.default_permissions(moderate_members=True)
    async def case_list(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        tipo: str | None = "all",
        limite: int | None = 10,
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    "❌ **Sem Permissões**\nVocê não tem permissão para ver cases moderativos.",
                    ephemeral=True,
                )
                return

            # Limitar número de resultados
            if limite > 25:
                limite = 25
            elif limite < 1:
                limite = 10

            # Construir query
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if user and tipo != "all":
                cursor.execute(
                    """
                    SELECT case_id, user_id, moderator_id, type, reason, created_at, is_active
                    FROM mod_cases 
                    WHERE guild_id = ? AND user_id = ? AND type = ?
                    ORDER BY case_id DESC LIMIT ?
                """,
                    (str(interaction.guild.id), str(user.id), tipo, limite),
                )
            elif user:
                cursor.execute(
                    """
                    SELECT case_id, user_id, moderator_id, type, reason, created_at, is_active
                    FROM mod_cases 
                    WHERE guild_id = ? AND user_id = ?
                    ORDER BY case_id DESC LIMIT ?
                """,
                    (str(interaction.guild.id), str(user.id), limite),
                )
            elif tipo != "all":
                cursor.execute(
                    """
                    SELECT case_id, user_id, moderator_id, type, reason, created_at, is_active
                    FROM mod_cases 
                    WHERE guild_id = ? AND type = ?
                    ORDER BY case_id DESC LIMIT ?
                """,
                    (str(interaction.guild.id), tipo, limite),
                )
            else:
                cursor.execute(
                    """
                    SELECT case_id, user_id, moderator_id, type, reason, created_at, is_active
                    FROM mod_cases 
                    WHERE guild_id = ?
                    ORDER BY case_id DESC LIMIT ?
                """,
                    (str(interaction.guild.id), limite),
                )

            cases = cursor.fetchall()
            conn.close()

            if not cases:
                await interaction.response.send_message(
                    "❌ **Nenhum Case Encontrado**\nNão há cases com os filtros especificados.",
                    ephemeral=True,
                )
                return

            # Criar embed
            embed = discord.Embed(
                title="📋 **LISTA DE CASES**", color=0x6C5CE7, timestamp=datetime.now()
            )

            # Filtros aplicados
            filtros = []
            if user:
                filtros.append(f"Usuário: {user.display_name}")
            if tipo != "all":
                filtros.append(f"Tipo: {tipo}")

            if filtros:
                embed.add_field(name="🔍 Filtros", value=" • ".join(filtros), inline=False)

            embed.add_field(
                name="📊 Total",
                value=f"**{len(cases)}** case{'s' if len(cases) != 1 else ''}",
                inline=True,
            )

            embed.add_field(name="📄 Limite", value=f"**{limite}** resultados", inline=True)

            # Lista de cases
            cases_text = ""
            for case_id, user_id, mod_id, case_type, reason, created_at, is_active in cases[:10]:
                emoji, _ = self.get_case_emoji_color(case_type)
                status = "🟢" if is_active else "🔴"

                # Buscar usuário
                try:
                    case_user = await self.bot.fetch_user(int(user_id))
                    user_name = case_user.display_name
                except:
                    user_name = f"ID: {user_id}"

                created_timestamp = int(datetime.fromisoformat(created_at).timestamp())

                cases_text += (
                    f"{status}{emoji} **Case #{case_id}** - {case_type.replace('_', ' ').title()}\n"
                )
                cases_text += f"   👤 {user_name[:30]}{'...' if len(user_name) > 30 else ''}\n"
                cases_text += f"   📅 <t:{created_timestamp}:R>\n"
                cases_text += f"   📝 {(reason or 'Sem motivo')[:40]}{'...' if len(reason or '') > 40 else ''}\n\n"

            embed.add_field(
                name="📋 Cases",
                value=cases_text[:1000] + ("..." if len(cases_text) > 1000 else ""),
                inline=False,
            )

            if len(cases) > 10:
                embed.add_field(
                    name="➕ Mais Cases",
                    value=f"E mais **{len(cases) - 10}** cases...\nUse filtros específicos para refinar.",
                    inline=False,
                )

            embed.set_footer(
                text=f"Use /case-view [id] para ver detalhes | Solicitado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando case-list: {e}")
            try:
                await interaction.response.send_message("❌ Erro ao listar cases.", ephemeral=True)
            except:
                pass


async def setup(bot):
    await bot.add_cog(CaseSystem(bot))
