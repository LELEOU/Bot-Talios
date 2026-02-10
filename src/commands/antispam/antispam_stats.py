"""
Sistema de Antispam - Estatísticas e Testes
Ferramentas de monitoramento e teste do sistema antispam
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    pass


class AntispamStats(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

        # Estatísticas temporárias (em memória)
        self.temp_stats: defaultdict[int, dict[str, Any]] = defaultdict(
            lambda: {
                "detections": 0,
                "warnings": 0,
                "mutes": 0,
                "kicks": 0,
                "bans": 0,
                "last_detection": None,
            }
        )

    @app_commands.command(name="antispam-stats", description="📊 Ver estatísticas do antispam")
    @app_commands.describe(
        periodo="Período das estatísticas", usuario="Ver estatísticas de um usuário específico"
    )
    async def antispam_stats(
        self,
        interaction: discord.Interaction,
        periodo: str | None = "hoje",
        usuario: discord.Member | None = None,
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Sem permissão para ver estatísticas antispam.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Calcular período
            now: datetime = datetime.now()
            start_date: datetime

            if periodo == "hoje":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif periodo == "semana":
                start_date = now - timedelta(days=7)
            elif periodo == "mes":
                start_date = now - timedelta(days=30)
            else:
                start_date = now - timedelta(days=1)  # Default: último dia

            # Buscar estatísticas do banco
            try:
                from ...utils.database import database

                # Query base
                query: str
                params: tuple[Any, ...]

                if usuario:
                    query = """
                        SELECT action_type, COUNT(*) as count
                        FROM antispam_logs
                        WHERE guild_id = ? AND user_id = ? AND timestamp >= ?
                        GROUP BY action_type
                    """
                    params = (str(interaction.guild.id), str(usuario.id), start_date.isoformat())
                else:
                    query = """
                        SELECT action_type, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
                        FROM antispam_logs
                        WHERE guild_id = ? AND timestamp >= ?
                        GROUP BY action_type
                    """
                    params = (str(interaction.guild.id), start_date.isoformat())

                results: Any = await database.fetch_all(query, params)

                # Processar resultados
                stats: dict[str, int] = {
                    "detections": 0,
                    "warnings": 0,
                    "mutes": 0,
                    "kicks": 0,
                    "bans": 0,
                    "total": 0,
                }

                unique_users: int = 0

                for row in results:
                    action_type: str = row.get("action_type", "")
                    count: int = row.get("count", 0)

                    if action_type in stats:
                        stats[action_type] = count
                        stats["total"] += count

                    if not usuario and "unique_users" in row:
                        unique_users = max(unique_users, row["unique_users"])

            except Exception as e:
                print(f"❌ Erro ao buscar estatísticas: {e}")
                stats = {
                    "detections": 0,
                    "warnings": 0,
                    "mutes": 0,
                    "kicks": 0,
                    "bans": 0,
                    "total": 0,
                }
                unique_users = 0

            # Criar embed de estatísticas
            stats_embed: discord.Embed = discord.Embed(
                title="📊 **ESTATÍSTICAS ANTISPAM**",
                description=f"**Período:** {periodo.capitalize()}\n"
                + (f"**Usuário:** {usuario.mention}" if usuario else "**Servidor inteiro**"),
                color=0x5865F2,
                timestamp=datetime.now(),
            )

            # Total de detecções
            total_detections: int = stats["total"]

            stats_embed.add_field(
                name="🎯 Resumo Geral",
                value=f"**Total de detecções:** {total_detections}\n"
                + (f"**Usuários únicos:** {unique_users}" if not usuario else ""),
                inline=False,
            )

            # Detalhamento por ação
            action_details: str = ""

            if stats["warnings"] > 0:
                pct: float = (stats["warnings"] / total_detections * 100) if total_detections > 0 else 0
                action_details += f"⚠️ **Avisos:** {stats['warnings']} ({pct:.1f}%)\n"

            if stats["mutes"] > 0:
                pct = (stats["mutes"] / total_detections * 100) if total_detections > 0 else 0
                action_details += f"🔇 **Mutes:** {stats['mutes']} ({pct:.1f}%)\n"

            if stats["kicks"] > 0:
                pct = (stats["kicks"] / total_detections * 100) if total_detections > 0 else 0
                action_details += f"🥾 **Expulsões:** {stats['kicks']} ({pct:.1f}%)\n"

            if stats["bans"] > 0:
                pct = (stats["bans"] / total_detections * 100) if total_detections > 0 else 0
                action_details += f"🔨 **Banimentos:** {stats['bans']} ({pct:.1f}%)\n"

            if not action_details:
                action_details = "✅ Nenhuma ação tomada neste período."

            stats_embed.add_field(name="📋 Ações Tomadas", value=action_details, inline=False)

            # Top violadores (se for servidor inteiro)
            if not usuario:
                try:
                    top_query: str = """
                        SELECT user_id, COUNT(*) as violations
                        FROM antispam_logs
                        WHERE guild_id = ? AND timestamp >= ?
                        GROUP BY user_id
                        ORDER BY violations DESC
                        LIMIT 5
                    """

                    top_results: Any = await database.fetch_all(
                        top_query, (str(interaction.guild.id), start_date.isoformat())
                    )

                    if top_results:
                        top_violators: str = ""
                        medals: list[str] = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

                        for idx, row in enumerate(top_results):
                            user_id: str = row.get("user_id", "")
                            violations_count: int = row.get("violations", 0)

                            user: discord.Member | None = interaction.guild.get_member(int(user_id))
                            user_mention: str = (
                                user.mention if user else f"Usuário não encontrado (`{user_id}`)"
                            )

                            medal: str = medals[idx] if idx < len(medals) else "•"
                            top_violators += (
                                f"{medal} {user_mention} - **{violations_count} violações**\n"
                            )

                        stats_embed.add_field(
                            name="👥 Top Violadores", value=top_violators, inline=False
                        )
                except:
                    pass

            # Informações adicionais
            stats_embed.add_field(
                name="🔧 Comandos Úteis",
                value="`/antispam-reset` - Resetar estatísticas\n"
                "`/antispam-test` - Testar sistema\n"
                "`/antispam-rules` - Ver regras ativas",
                inline=False,
            )

            stats_embed.set_footer(
                text=f"Solicitado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=stats_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando antispam-stats: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao buscar estatísticas. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="antispam-test", description="🧪 Testar sistema antispam")
    @app_commands.describe(
        tipo="Tipo de teste a ser realizado", intensidade="Intensidade do teste (1-5)"
    )
    async def antispam_test(
        self, interaction: discord.Interaction, tipo: str = "basico", intensidade: int | None = 3
    ) -> None:
        try:
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ Sem permissão para testar antispam.", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Buscar configuração
            try:
                from ...utils.database import database

                config_data: Any = await database.get(
                    "SELECT config_data FROM antispam_config WHERE guild_id = ?",
                    (str(interaction.guild.id),),
                )

                if not config_data:
                    await interaction.followup.send(
                        "❌ Sistema antispam não configurado.\nUse `/antispam-setup` primeiro.",
                        ephemeral=True,
                    )
                    return

                config: dict[str, Any] = json.loads(config_data["config_data"])

            except Exception as e:
                print(f"❌ Erro ao carregar config: {e}")
                await interaction.followup.send(
                    "❌ Erro ao carregar configuração antispam.", ephemeral=True
                )
                return

            # Validar intensidade
            if intensidade is None:
                intensidade = 3

            intensidade = max(1, min(5, intensidade))

            # Criar embed de teste
            test_embed: discord.Embed = discord.Embed(
                title="🧪 **TESTE ANTISPAM**",
                description=f"**Tipo:** {tipo.capitalize()}\n**Intensidade:** {'⭐' * intensidade}",
                color=0x00AAFF,
                timestamp=datetime.now(),
            )

            test_results: list[str] = []

            # TESTE BÁSICO - Verificar configuração
            if tipo.lower() == "basico":
                test_results.append(
                    f"✅ Sistema {'ativo' if config.get('enabled') else 'desativo'}"
                )
                test_results.append(
                    f"✅ Max mensagens: {config.get('max_messages', 5)} por {config.get('time_window', 10)}s"
                )
                test_results.append(
                    f"✅ Auto-mute: {'Sim' if config.get('auto_mute') else 'Não'}"
                )
                test_results.append(f"✅ Whitelist: {len(config.get('whitelist_users', []))} usuários")

            # TESTE DE SPAM - Simular spam de mensagens
            elif tipo.lower() == "spam":
                max_msgs: int = config.get("max_messages", 5)
                time_window: int = config.get("time_window", 10)

                test_msgs: int = max_msgs + intensidade

                test_results.append(f"📨 Simulando {test_msgs} mensagens em {time_window}s")
                test_results.append(
                    f"🎯 Limite configurado: {max_msgs} mensagens"
                )

                if test_msgs > max_msgs:
                    test_results.append("⚠️ **SPAM DETECTADO** - Ação seria tomada")
                else:
                    test_results.append("✅ Dentro do limite permitido")

            # TESTE DE MENÇÕES
            elif tipo.lower() in ["mencoes", "mentions"]:
                max_mentions: int = config.get("max_mentions", 5)
                test_mentions: int = max_mentions + intensidade

                test_results.append(f"📞 Simulando {test_mentions} menções")
                test_results.append(f"🎯 Limite configurado: {max_mentions} menções")

                if test_mentions > max_mentions:
                    test_results.append("⚠️ **EXCESSO DE MENÇÕES** - Ação seria tomada")
                else:
                    test_results.append("✅ Dentro do limite permitido")

            # TESTE DE CAPS
            elif tipo.lower() == "caps":
                max_caps: int = config.get("max_caps_percentage", 70)
                test_caps: int = min(100, max_caps + (intensidade * 5))

                test_results.append(f"🔠 Simulando {test_caps}% de CAPS")
                test_results.append(f"🎯 Limite configurado: {max_caps}%")

                if test_caps > max_caps:
                    test_results.append("⚠️ **MUITO CAPS** - Ação seria tomada")
                else:
                    test_results.append("✅ Dentro do limite permitido")

            # TESTE DE EMOJIS
            elif tipo.lower() == "emojis":
                max_emojis: int = config.get("max_emojis", 10)
                test_emojis: int = max_emojis + intensidade

                test_results.append(f"😀 Simulando {test_emojis} emojis")
                test_results.append(f"🎯 Limite configurado: {max_emojis} emojis")

                if test_emojis > max_emojis:
                    test_results.append("⚠️ **MUITOS EMOJIS** - Ação seria tomada")
                else:
                    test_results.append("✅ Dentro do limite permitido")

            else:
                test_results.append("❌ Tipo de teste inválido")
                test_results.append("**Tipos disponíveis:** basico, spam, mencoes, caps, emojis")

            test_embed.add_field(
                name="📊 Resultados do Teste", value="\n".join(test_results), inline=False
            )

            # Informações sobre ações
            actions: dict[str, str] = config.get(
                "actions",
                {
                    "first_violation": "warn",
                    "second_violation": "mute",
                    "third_violation": "kick",
                    "persistent_violation": "ban",
                },
            )

            test_embed.add_field(
                name="⚙️ Ações Configuradas",
                value=f"1ª violação: {actions.get('first_violation', 'warn')}\n"
                f"2ª violação: {actions.get('second_violation', 'mute')}\n"
                f"3ª violação: {actions.get('third_violation', 'kick')}\n"
                f"Persistente: {actions.get('persistent_violation', 'ban')}",
                inline=False,
            )

            test_embed.set_footer(
                text=f"Teste realizado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=test_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no comando antispam-test: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao executar teste. Tente novamente.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="antispam-reset", description="🔄 Resetar dados do antispam")
    @app_commands.describe(
        tipo="Tipo de reset", usuario="Resetar apenas para um usuário específico"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def antispam_reset(
        self,
        interaction: discord.Interaction,
        tipo: str = "violacoes",
        usuario: discord.Member | None = None,
    ) -> None:
        try:
            await interaction.response.defer(ephemeral=True)

            # Buscar dados a serem resetados
            try:
                from ...utils.database import database

                reset_count: int = 0

                if tipo.lower() == "violacoes":
                    # Resetar apenas contadores de violações
                    if usuario:
                        # Reset para usuário específico
                        user_id: int = usuario.id
                        if user_id in self.temp_stats:
                            del self.temp_stats[user_id]
                            reset_count = 1

                        await interaction.followup.send(
                            f"✅ Violações de {usuario.mention} resetadas!", ephemeral=True
                        )
                    else:
                        # Reset geral
                        self.temp_stats.clear()
                        reset_count = len(self.temp_stats)

                        await interaction.followup.send(
                            "✅ Todas as violações foram resetadas!", ephemeral=True
                        )

                elif tipo.lower() == "estatisticas":
                    # Resetar logs do banco de dados
                    if usuario:
                        result: Any = await database.execute(
                            "DELETE FROM antispam_logs WHERE guild_id = ? AND user_id = ?",
                            (str(interaction.guild.id), str(usuario.id)),
                        )
                        reset_count = result.rowcount if hasattr(result, "rowcount") else 0

                        await interaction.followup.send(
                            f"✅ Estatísticas de {usuario.mention} resetadas!\n"
                            f"**Registros removidos:** {reset_count}",
                            ephemeral=True,
                        )
                    else:
                        result = await database.execute(
                            "DELETE FROM antispam_logs WHERE guild_id = ?",
                            (str(interaction.guild.id),),
                        )
                        reset_count = result.rowcount if hasattr(result, "rowcount") else 0

                        await interaction.followup.send(
                            f"✅ Todas as estatísticas foram resetadas!\n"
                            f"**Registros removidos:** {reset_count}",
                            ephemeral=True,
                        )

                elif tipo.lower() == "tudo":
                    # Reset completo
                    if usuario:
                        user_id = usuario.id
                        if user_id in self.temp_stats:
                            del self.temp_stats[user_id]

                        result = await database.execute(
                            "DELETE FROM antispam_logs WHERE guild_id = ? AND user_id = ?",
                            (str(interaction.guild.id), str(usuario.id)),
                        )

                        reset_count = result.rowcount if hasattr(result, "rowcount") else 0

                        await interaction.followup.send(
                            f"✅ **RESET COMPLETO** de {usuario.mention}!\n"
                            f"Violações e estatísticas removidas.",
                            ephemeral=True,
                        )
                    else:
                        self.temp_stats.clear()

                        result = await database.execute(
                            "DELETE FROM antispam_logs WHERE guild_id = ?",
                            (str(interaction.guild.id),),
                        )

                        reset_count = result.rowcount if hasattr(result, "rowcount") else 0

                        await interaction.followup.send(
                            f"✅ **RESET COMPLETO DO SERVIDOR**!\n"
                            f"Todas as violações e estatísticas foram removidas.\n"
                            f"**Registros removidos:** {reset_count}",
                            ephemeral=True,
                        )

                else:
                    await interaction.followup.send(
                        "❌ **Tipo de reset inválido!**\n"
                        "**Tipos disponíveis:** `violacoes`, `estatisticas`, `tudo`",
                        ephemeral=True,
                    )

            except Exception as e:
                print(f"❌ Erro ao resetar dados: {e}")
                await interaction.followup.send(
                    "❌ Erro ao resetar dados antispam.", ephemeral=True
                )

        except Exception as e:
            print(f"❌ Erro no comando antispam-reset: {e}")
            try:
                await interaction.followup.send("❌ Erro ao resetar. Tente novamente.", ephemeral=True)
            except:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AntispamStats(bot))
