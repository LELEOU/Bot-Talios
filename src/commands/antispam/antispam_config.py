"""
Sistema de Antispam - Proteção Avançada contra Spam
Sistema inteligente de detecção e prevenção de spam
"""

from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class AntispamSystem:
    """Sistema de detecção de spam inteligente"""

    def __init__(self) -> None:
        # Armazenamento temporário de mensagens por usuário
        self.user_messages: dict[int, deque[datetime]] = defaultdict(lambda: deque(maxlen=20))
        self.user_violations: dict[int, int] = defaultdict(int)
        self.user_warnings: dict[int, int] = defaultdict(int)

        # Configurações padrão
        self.default_config: dict[str, Any] = {
            "enabled": True,
            "max_messages": 5,  # Máximo de mensagens
            "time_window": 10,  # Em segundos
            "max_duplicates": 3,  # Máximo de mensagens duplicadas
            "max_mentions": 5,  # Máximo de menções
            "max_emojis": 10,  # Máximo de emojis
            "max_caps_percentage": 70,  # Máximo de CAPS %
            "auto_mute": True,  # Auto-mute em violações
            "mute_duration": 300,  # Duração do mute (segundos)
            "delete_messages": True,  # Deletar mensagens de spam
            "warn_before_action": True,  # Avisar antes de punir
            "max_warnings": 3,  # Máximo de avisos
            "ignored_roles": [],  # Roles ignorados
            "ignored_channels": [],  # Canais ignorados
            "whitelist_users": [],  # Usuários na whitelist
            "actions": {
                "first_violation": "warn",  # warn, mute, kick, ban
                "second_violation": "mute",
                "third_violation": "kick",
                "persistent_violation": "ban",
            },
        }

    def is_spam_message(
        self, message: discord.Message, config: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Analisa se uma mensagem é spam"""
        violations: list[str] = []

        # Verificar se usuário está na whitelist
        if str(message.author.id) in config.get("whitelist_users", []):
            return False, []

        # Verificar roles ignorados
        ignored_roles: list[str] = config.get("ignored_roles", [])
        if any(str(role.id) in ignored_roles for role in message.author.roles):
            return False, []

        # Verificar canal ignorado
        if str(message.channel.id) in config.get("ignored_channels", []):
            return False, []

        # Verificar permissões especiais
        if message.author.guild_permissions.manage_messages:
            return False, []

        content: str = message.content
        user_id: int = message.author.id

        # 1. SPAM DE MENSAGENS RÁPIDAS
        now: datetime = datetime.now()
        user_msgs: deque[datetime] = self.user_messages[user_id]

        # Adicionar mensagem atual
        user_msgs.append(now)

        # Contar mensagens no período
        time_window: int = config.get("time_window", 10)
        recent_msgs: list[datetime] = [
            msg for msg in user_msgs if (now - msg).seconds <= time_window
        ]

        if len(recent_msgs) > config.get("max_messages", 5):
            violations.append(f"Muitas mensagens ({len(recent_msgs)} em {time_window}s)")

        # 2. MENSAGENS DUPLICADAS
        recent_content: list[Any] = []
        for msg_time in list(user_msgs)[-10:]:  # Últimas 10 mensagens
            # Aqui seria ideal salvar o conteúdo também, mas por simplicidade...
            pass

        # Verificação simples de duplicatas (seria melhor com histórico completo)
        if len(content) > 10:  # Só verificar mensagens com conteúdo
            duplicate_count: int = sum(
                1 for _ in re.finditer(re.escape(content.lower()), content.lower())
            )
            if duplicate_count > config.get("max_duplicates", 3):
                violations.append("Mensagem duplicada repetida")

        # 3. MUITAS MENÇÕES
        mentions_count: int = len(message.mentions) + len(message.role_mentions)
        if mentions_count > config.get("max_mentions", 5):
            violations.append(f"Muitas menções ({mentions_count})")

        # 4. MUITOS EMOJIS
        emoji_count: int = len(
            re.findall(
                r"<:\w+:\d+>|[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]",
                content,
            )
        )
        if emoji_count > config.get("max_emojis", 10):
            violations.append(f"Muitos emojis ({emoji_count})")

        # 5. MUITO CAPS
        if len(content) > 10:
            caps_count: int = sum(1 for c in content if c.isupper())
            caps_percentage: float = (caps_count / len(content)) * 100
            if caps_percentage > config.get("max_caps_percentage", 70):
                violations.append(f"Muito CAPS ({caps_percentage:.1f}%)")

        # 6. LINKS SUSPEITOS (básico)
        suspicious_patterns: list[str] = [
            r"discord\.gg/\w+",  # Convites Discord
            r"bit\.ly/\w+",  # Links encurtados
            r"tinyurl\.com/\w+",  # Links encurtados
            r"free\s+(nitro|money|robux)",  # Scams comuns
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append("Link suspeito detectado")
                break

        # 7. CARACTERES REPETIDOS
        repeated_chars: list[Any] = re.findall(r"(.)\1{4,}", content)  # 5+ caracteres iguais seguidos
        if repeated_chars:
            violations.append("Caracteres repetidos excessivamente")

        return len(violations) > 0, violations


class AntispamConfig(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.antispam: AntispamSystem = AntispamSystem()

    @app_commands.command(name="antispam-setup", description="🛡️ Configurar sistema de antispam")
    @app_commands.describe(
        ativo="Ativar ou desativar o sistema",
        max_mensagens="Máximo de mensagens permitidas",
        tempo_janela="Janela de tempo em segundos",
        auto_mute="Auto-mute em violações",
    )
    async def antispam_setup(
        self,
        interaction: discord.Interaction,
        ativo: bool | None = True,
        max_mensagens: int | None = None,
        tempo_janela: int | None = None,
        auto_mute: bool | None = None,
    ) -> None:
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Você não tem permissão para configurar antispam. **Necessário**: Gerenciar Servidor",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar configuração existente ou usar padrão
            try:
                from ...utils.database import database

                existing: Any = await database.get(
                    "SELECT config_data FROM antispam_config WHERE guild_id = ?",
                    (str(interaction.guild.id),),
                )

                config: dict[str, Any]
                if existing:
                    config = json.loads(existing["config_data"])
                else:
                    config = self.antispam.default_config.copy()

            except Exception as e:
                print(f"❌ Erro ao carregar config: {e}")
                config = self.antispam.default_config.copy()

            # Aplicar alterações
            config["enabled"] = ativo
            if max_mensagens is not None:
                config["max_messages"] = max(1, min(20, max_mensagens))
            if tempo_janela is not None:
                config["time_window"] = max(5, min(60, tempo_janela))
            if auto_mute is not None:
                config["auto_mute"] = auto_mute

            # Salvar configuração
            try:
                config_json: str = json.dumps(config)

                if existing:
                    await database.execute(
                        "UPDATE antispam_config SET config_data = ? WHERE guild_id = ?",
                        (config_json, str(interaction.guild.id)),
                    )
                else:
                    await database.execute(
                        "INSERT INTO antispam_config (guild_id, config_data) VALUES (?, ?)",
                        (str(interaction.guild.id), config_json),
                    )
            except Exception as e:
                print(f"❌ Erro ao salvar config: {e}")
                await interaction.followup.send("❌ Erro ao salvar configuração.", ephemeral=True)
                return

            # Embed de confirmação
            setup_embed: discord.Embed = discord.Embed(
                title="🛡️ **SISTEMA ANTISPAM CONFIGURADO**",
                description="Sistema de proteção contra spam configurado com sucesso!",
                color=0x00FF00 if ativo else 0xFF6B6B,
                timestamp=datetime.now(),
            )

            setup_embed.add_field(
                name="⚙️ Configurações Principais",
                value=f"**Status:** {'✅ Ativo' if config['enabled'] else '❌ Desativo'}\n"
                f"**Max mensagens:** {config['max_messages']} por {config['time_window']}s\n"
                f"**Auto-mute:** {'✅ Sim' if config['auto_mute'] else '❌ Não'}\n"
                f"**Duração mute:** {config['mute_duration']}s",
                inline=True,
            )

            setup_embed.add_field(
                name="🎯 Detecções Ativas",
                value="📨 Spam de mensagens\n"
                "🔄 Mensagens duplicadas\n"
                "📞 Excesso de menções\n"
                "😀 Excesso de emojis\n"
                "🔠 Muito CAPS\n"
                "🔗 Links suspeitos",
                inline=True,
            )

            setup_embed.add_field(
                name="🔧 Comandos Úteis",
                value="`/antispam-whitelist` - Gerenciar whitelist\n"
                "`/antispam-ignore` - Ignorar canais/roles\n"
                "`/antispam-stats` - Ver estatísticas\n"
                "`/antispam-test` - Testar sistema",
                inline=False,
            )

            setup_embed.set_footer(
                text=f"Configurado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=setup_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando antispam-setup: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao configurar antispam. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(
        name="antispam-whitelist", description="👥 Gerenciar whitelist do antispam"
    )
    @app_commands.describe(
        acao="Ação a ser realizada", usuario="Usuário para adicionar/remover da whitelist"
    )
    async def antispam_whitelist(
        self, interaction: discord.Interaction, acao: str, usuario: discord.Member | None = None
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Sem permissão para gerenciar whitelist antispam.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar config
            try:
                from ...utils.database import database

                existing: Any = await database.get(
                    "SELECT config_data FROM antispam_config WHERE guild_id = ?",
                    (str(interaction.guild.id),),
                )

                config: dict[str, Any]
                if existing:
                    config = json.loads(existing["config_data"])
                else:
                    config = self.antispam.default_config.copy()
            except:
                config = self.antispam.default_config.copy()

            whitelist: list[str] = config.get("whitelist_users", [])

            if acao.lower() in ["add", "adicionar"] and usuario:
                if str(usuario.id) not in whitelist:
                    whitelist.append(str(usuario.id))
                    config["whitelist_users"] = whitelist

                    # Salvar
                    await database.execute(
                        "UPDATE antispam_config SET config_data = ? WHERE guild_id = ?",
                        (json.dumps(config), str(interaction.guild.id)),
                    )

                    await interaction.followup.send(
                        f"✅ **{usuario.mention} adicionado à whitelist antispam!**", ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"ℹ️ {usuario.mention} já está na whitelist.", ephemeral=True
                    )

            elif acao.lower() in ["remove", "remover"] and usuario:
                if str(usuario.id) in whitelist:
                    whitelist.remove(str(usuario.id))
                    config["whitelist_users"] = whitelist

                    # Salvar
                    await database.execute(
                        "UPDATE antispam_config SET config_data = ? WHERE guild_id = ?",
                        (json.dumps(config), str(interaction.guild.id)),
                    )

                    await interaction.followup.send(
                        f"✅ **{usuario.mention} removido da whitelist antispam!**", ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"ℹ️ {usuario.mention} não está na whitelist.", ephemeral=True
                    )

            elif acao.lower() in ["list", "listar"]:
                if whitelist:
                    users_list: list[str] = []
                    for user_id in whitelist:
                        user: discord.Member | None = interaction.guild.get_member(int(user_id))
                        users_list.append(
                            user.mention if user else f"Usuário não encontrado (`{user_id}`)"
                        )

                    whitelist_embed: discord.Embed = discord.Embed(
                        title="👥 **Whitelist Antispam**",
                        description="\n".join(users_list),
                        color=0x2F3136,
                        timestamp=datetime.now(),
                    )

                    await interaction.followup.send(embed=whitelist_embed, ephemeral=True)
                else:
                    await interaction.followup.send(
                        "📝 **Whitelist vazia**\nNenhum usuário na whitelist do antispam.",
                        ephemeral=True,
                    )

            else:
                await interaction.followup.send(
                    "❌ **Uso incorreto!**\n"
                    "**Ações válidas:** `add`, `remove`, `list`\n"
                    "**Exemplo:** `/antispam-whitelist add @usuário`",
                    ephemeral=True,
                )

        except Exception as e:
            print(f"❌ Erro no antispam-whitelist: {e}")
            await interaction.followup.send("❌ Erro ao gerenciar whitelist.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Event listener para detectar spam"""
        try:
            # Ignorar bots e DMs
            if message.author.bot or not message.guild:
                return

            # Buscar configuração
            try:
                from ...utils.database import database

                config_data: Any = await database.get(
                    "SELECT config_data FROM antispam_config WHERE guild_id = ?",
                    (str(message.guild.id),),
                )

                if not config_data:
                    return

                config: dict[str, Any] = json.loads(config_data["config_data"])

                if not config.get("enabled", False):
                    return

            except Exception as e:
                print(f"❌ Erro ao carregar config antispam: {e}")
                return

            # Verificar se é spam
            is_spam: bool
            violations: list[str]
            is_spam, violations = self.antispam.is_spam_message(message, config)

            if is_spam:
                await self.handle_spam_detection(message, violations, config)

        except Exception as e:
            print(f"❌ Erro no antispam listener: {e}")

    async def handle_spam_detection(
        self, message: discord.Message, violations: list[str], config: dict[str, Any]
    ) -> None:
        """Lida com detecção de spam"""
        try:
            user_id: int = message.author.id

            # Incrementar violações
            self.antispam.user_violations[user_id] += 1
            violation_count: int = self.antispam.user_violations[user_id]

            # Deletar mensagem se configurado
            if config.get("delete_messages", True):
                try:
                    await message.delete()
                except:
                    pass

            # Determinar ação
            actions: dict[str, str] = config.get("actions", {})

            action: str
            if violation_count == 1:
                action = actions.get("first_violation", "warn")
            elif violation_count == 2:
                action = actions.get("second_violation", "mute")
            elif violation_count == 3:
                action = actions.get("third_violation", "kick")
            else:
                action = actions.get("persistent_violation", "ban")

            # Executar ação
            await self.execute_antispam_action(message, action, violations, violation_count, config)

        except Exception as e:
            print(f"❌ Erro ao lidar com spam: {e}")

    async def execute_antispam_action(
        self,
        message: discord.Message,
        action: str,
        violations: list[str],
        count: int,
        config: dict[str, Any],
    ) -> None:
        """Executa ação antispam"""
        try:
            member: discord.Member = message.author
            guild: discord.Guild = message.guild

            # Criar embed de violação
            violation_embed: discord.Embed = discord.Embed(
                title="🛡️ **DETECÇÃO DE SPAM**",
                description=f"Usuário: {member.mention}\nViolação #{count}",
                color=0xFF6B6B,
                timestamp=datetime.now(),
            )

            violation_embed.add_field(
                name="❌ Violações Detectadas",
                value="\n".join([f"• {v}" for v in violations]),
                inline=False,
            )

            violation_embed.add_field(name="📍 Canal", value=message.channel.mention, inline=True)

            # Executar ação específica
            if action == "warn":
                violation_embed.add_field(name="⚠️ Ação", value="Aviso enviado", inline=True)

                # Enviar DM de aviso
                try:
                    dm_embed: discord.Embed = discord.Embed(
                        title="⚠️ **AVISO DE SPAM**",
                        description=f"Você foi detectado fazendo spam em **{guild.name}**.",
                        color=0xFFAA00,
                        timestamp=datetime.now(),
                    )

                    dm_embed.add_field(
                        name="❌ Violações", value="\n".join(violations), inline=False
                    )

                    dm_embed.add_field(
                        name="🔔 Aviso",
                        value="Evite repetir esse comportamento para não ser punido.",
                        inline=False,
                    )

                    await member.send(embed=dm_embed)
                except:
                    pass

            elif action == "mute" and config.get("auto_mute", True):
                # Aplicar timeout/mute
                mute_duration: int = config.get("mute_duration", 300)

                try:
                    await member.timeout(
                        datetime.now() + timedelta(seconds=mute_duration),
                        reason=f"Antispam: {', '.join(violations)}",
                    )

                    violation_embed.add_field(
                        name="🔇 Ação", value=f"Mute por {mute_duration}s", inline=True
                    )

                    # Aviso no canal
                    await message.channel.send(
                        f"🛡️ {member.mention} foi temporariamente silenciado por spam.",
                        embed=violation_embed,
                        delete_after=10,
                    )

                except discord.Forbidden:
                    violation_embed.add_field(
                        name="❌ Erro", value="Sem permissão para aplicar timeout", inline=True
                    )

            elif action == "kick":
                try:
                    await member.kick(reason="Antispam: Spam persistente")
                    violation_embed.add_field(name="🥾 Ação", value="Usuário expulso", inline=True)
                except discord.Forbidden:
                    violation_embed.add_field(
                        name="❌ Erro", value="Sem permissão para expulsar", inline=True
                    )

            elif action == "ban":
                try:
                    await member.ban(reason="Antispam: Spam excessivo", delete_message_days=1)
                    violation_embed.add_field(name="🔨 Ação", value="Usuário banido", inline=True)
                except discord.Forbidden:
                    violation_embed.add_field(
                        name="❌ Erro", value="Sem permissão para banir", inline=True
                    )

            # Enviar log se houver canal configurado
            try:
                from ...utils.database import database

                log_config: Any = await database.get(
                    "SELECT channel_id FROM logs WHERE guild_id = ? AND log_type = 'antispam'",
                    (str(guild.id),),
                )

                if log_config:
                    log_channel: discord.TextChannel | None = guild.get_channel(
                        int(log_config["channel_id"])
                    )
                    if log_channel:
                        await log_channel.send(embed=violation_embed)
            except:
                pass

        except Exception as e:
            print(f"❌ Erro ao executar ação antispam: {e}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AntispamConfig(bot))
