"""
Sistema de Leveling - Comando Level
Mostra nível, XP e progresso de usuários
"""

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="level", description="📊 Mostra seu nível e XP ou de outro usuário")
    @app_commands.describe(usuario="Usuário para ver o level (padrão: você)")
    async def level(
        self, interaction: discord.Interaction, usuario: discord.Member | None = None
    ):
        try:
            target_user = usuario or interaction.user

            await interaction.response.defer()

            # 📊 BUSCAR DADOS DO USUÁRIO
            try:
                from ...utils.database import database

                user_data = await database.get(
                    "SELECT * FROM user_levels WHERE guild_id = ? AND user_id = ?",
                    (str(interaction.guild.id), str(target_user.id)),
                )
            except:
                user_data = None

            if not user_data:
                embed = discord.Embed(
                    title="❌ Sem Dados de Level",
                    description=f"**{target_user.display_name}** ainda não possui dados de level.\n\n"
                    f"💡 **Dica**: Envie algumas mensagens para começar a ganhar XP!",
                    color=0xFF9999,
                    timestamp=datetime.now(),
                )
                embed.set_thumbnail(url=target_user.display_avatar.url)
                await interaction.followup.send(embed=embed)
                return

            # 🧮 CALCULAR PROGRESSÃO DE XP
            level = user_data["level"]
            current_xp = user_data["xp"]
            messages = user_data["messages"]

            # Sistema de XP progressivo (mais difícil a cada level)
            def xp_for_level(lv):
                if lv == 0:
                    return 0
                return int(100 * (lv**1.5))

            current_level_xp = xp_for_level(level)
            next_level_xp = xp_for_level(level + 1)
            progress_xp = current_xp - current_level_xp
            needed_xp = next_level_xp - current_level_xp

            # 📊 BARRA DE PROGRESSO VISUAL
            if needed_xp > 0:
                progress_percentage = min(100, max(0, (progress_xp / needed_xp) * 100))
            else:
                progress_percentage = 100

            # Criar barra de progresso bonita
            progress_bar_length = 20
            filled_length = int((progress_percentage / 100) * progress_bar_length)

            # Usar diferentes emojis para a barra
            progress_bar = "🟩" * filled_length + "⬜" * (progress_bar_length - filled_length)

            # 🏆 BUSCAR POSIÇÃO NO RANKING
            try:
                rank_data = await database.get(
                    "SELECT COUNT(*) + 1 as position FROM user_levels WHERE guild_id = ? AND xp > ?",
                    (str(interaction.guild.id), current_xp),
                )
                rank_position = rank_data["position"] if rank_data else "N/A"
            except:
                rank_position = "N/A"

            # 🎨 CRIAR EMBED DETALHADO
            embed = discord.Embed(
                title=f"📊 Level de {target_user.display_name}",
                color=self.get_level_color(level),
                timestamp=datetime.now(),
            )

            # Adicionar medalha por level
            level_badge = self.get_level_badge(level)

            embed.description = (
                f"{level_badge} **Level {level}** • **{current_xp:,} XP Total**\n\n"
                f"**Progresso para Level {level + 1}:**\n"
                f"{progress_bar} {progress_percentage:.1f}%\n"
                f"`{progress_xp:,}/{needed_xp:,} XP` • Faltam **{needed_xp - progress_xp:,} XP**"
            )

            # 📈 ESTATÍSTICAS DETALHADAS
            embed.add_field(
                name="🏆 Ranking", value=f"**#{rank_position}** no servidor", inline=True
            )

            embed.add_field(name="💬 Mensagens", value=f"**{messages:,}** enviadas", inline=True)

            embed.add_field(
                name="⚡ XP Médio",
                value=f"**{current_xp / max(1, messages):.1f}** por msg",
                inline=True,
            )

            # 🎯 PRÓXIMOS MARCOS
            next_milestone = self.get_next_milestone(level)
            if next_milestone:
                embed.add_field(
                    name="🎯 Próximo Marco",
                    value=f"**Level {next_milestone}** ({self.get_milestone_reward(next_milestone)})",
                    inline=True,
                )

            # ⏰ TEMPO ESTIMADO
            if messages > 10:  # Só calcular se tiver dados suficientes
                try:
                    # Estimar tempo baseado na atividade recente
                    days_active = max(
                        1,
                        (
                            datetime.now()
                            - datetime.fromisoformat(
                                user_data.get("created_at", datetime.now().isoformat())
                            )
                        ).days,
                    )
                    avg_messages_per_day = messages / days_active
                    avg_xp_per_day = avg_messages_per_day * 20  # Média de 20 XP por mensagem

                    if avg_xp_per_day > 0:
                        days_to_next = max(1, (needed_xp - progress_xp) / avg_xp_per_day)

                        if days_to_next < 1:
                            time_text = "Menos de 1 dia"
                        elif days_to_next < 7:
                            time_text = f"~{days_to_next:.1f} dias"
                        else:
                            time_text = f"~{days_to_next / 7:.1f} semanas"

                        embed.add_field(
                            name="⏰ Tempo Estimado",
                            value=f"{time_text} para Level {level + 1}",
                            inline=True,
                        )
                except:
                    pass

            # 🎨 VISUAL ENHANCEMENTS
            embed.set_thumbnail(url=target_user.display_avatar.url)
            embed.set_footer(
                text=f"Solicitado por {interaction.user.display_name} • Sistema de Level",
                icon_url=interaction.user.display_avatar.url,
            )

            # Adicionar badge especial para usuário próprio
            if target_user == interaction.user:
                embed.set_author(
                    name="Seu Perfil de Level", icon_url=target_user.display_avatar.url
                )
            else:
                embed.set_author(
                    name=f"Perfil de Level de {target_user.display_name}",
                    icon_url=target_user.display_avatar.url,
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando level: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao buscar dados de level. Tente novamente.", ephemeral=True
                )
            except:
                pass

    def get_level_color(self, level: int) -> int:
        """Retorna cor baseada no level"""
        if level < 5:
            return 0x95A5A6  # Cinza (Novato)
        if level < 10:
            return 0x3498DB  # Azul (Iniciante)
        if level < 20:
            return 0x2ECC71  # Verde (Intermediário)
        if level < 35:
            return 0xF39C12  # Laranja (Avançado)
        if level < 50:
            return 0xE74C3C  # Vermelho (Expert)
        if level < 75:
            return 0x9B59B6  # Roxo (Master)
        if level < 100:
            return 0xF1C40F  # Dourado (Legend)
        return 0xFF6B9D  # Rosa (Mythic)

    def get_level_badge(self, level: int) -> str:
        """Retorna badge/emoji baseado no level"""
        if level < 5:
            return "🥉"  # Bronze
        if level < 10:
            return "🥈"  # Prata
        if level < 20:
            return "🥇"  # Ouro
        if level < 35:
            return "💎"  # Diamante
        if level < 50:
            return "👑"  # Crown
        if level < 75:
            return "⭐"  # Star
        if level < 100:
            return "🌟"  # Glowing Star
        return "💫"  # Sparkles

    def get_next_milestone(self, current_level: int) -> int:
        """Retorna o próximo marco de level"""
        milestones = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200]
        for milestone in milestones:
            if milestone > current_level:
                return milestone
        return None

    def get_milestone_reward(self, level: int) -> str:
        """Retorna recompensa do marco"""
        rewards = {
            5: "Badge Bronze",
            10: "Badge Prata",
            15: "Cor Especial",
            20: "Badge Ouro",
            25: "Título Personalizado",
            30: "Badge Diamante",
            40: "Acesso VIP",
            50: "Badge Crown",
            75: "Badge Star",
            100: "Badge Legend",
            150: "Badge Master",
            200: "Badge Mythic",
        }
        return rewards.get(level, "Conquista Especial")


async def setup(bot):
    await bot.add_cog(Level(bot))
