"""
Comando Dice - Fun
Rola dados personalizáveis
"""

import random

import discord
from discord import app_commands
from discord.ext import commands


class DiceCommand(commands.Cog):
    """Comando de rolagem de dados"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="dice", description="Rola um dado personalizado")
    @app_commands.describe(
        lados="Número de lados do dado (padrão: 6)", quantidade="Quantidade de dados (padrão: 1)"
    )
    async def dice(
        self,
        interaction: discord.Interaction,
        lados: app_commands.Range[int, 2, 100] = 6,
        quantidade: app_commands.Range[int, 1, 10] = 1,
    ):
        """Rolar dados"""

        resultados = []
        total = 0

        # Rolar os dados
        for _ in range(quantidade):
            resultado = random.randint(1, lados)
            resultados.append(resultado)
            total += resultado

        # Criar embed
        embed = discord.Embed(
            title="🎲 Rolagem de Dados", color=0xFF6B35, timestamp=discord.utils.utcnow()
        )

        # Configurar descrição baseada na quantidade
        if quantidade == 1:
            embed.description = f"**Dado de {lados} lados**\n\n🎯 **Resultado:** {resultados[0]}"

            # Adicionar emoji baseado no resultado
            if lados == 6:
                dice_emojis = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
                if 1 <= resultados[0] <= 6:
                    embed.description += f" {dice_emojis[resultados[0] - 1]}"
        else:
            media = round(total / quantidade, 1)
            embed.description = (
                f"**{quantidade} dados de {lados} lados**\n\n"
                f"🎯 **Resultados:** [{', '.join(map(str, resultados))}]\n"
                f"📊 **Total:** {total}\n"
                f"📈 **Média:** {media}"
            )

            # Adicionar estatísticas extras para múltiplos dados
            maior = max(resultados)
            menor = min(resultados)

            embed.add_field(
                name="📊 Estatísticas",
                value=f"**Maior:** {maior}\n**Menor:** {menor}\n**Amplitude:** {maior - menor}",
                inline=True,
            )

            # Análise de sorte
            max_possivel = quantidade * lados
            porcentagem_sorte = round((total / max_possivel) * 100, 1)

            if porcentagem_sorte >= 80:
                sorte_emoji = "🍀"
                sorte_texto = "Muita sorte!"
            elif porcentagem_sorte >= 60:
                sorte_emoji = "😊"
                sorte_texto = "Boa sorte!"
            elif porcentagem_sorte >= 40:
                sorte_emoji = "😐"
                sorte_texto = "Sorte mediana"
            elif porcentagem_sorte >= 20:
                sorte_emoji = "😕"
                sorte_texto = "Pouca sorte"
            else:
                sorte_emoji = "💀"
                sorte_texto = "Que azar!"

            embed.add_field(
                name="🍀 Análise da Sorte",
                value=f"{sorte_emoji} **{sorte_texto}**\n({porcentagem_sorte}% do máximo)",
                inline=True,
            )

        # Adicionar campo com probabilidades
        if quantidade == 1:
            probabilidade = round((1 / lados) * 100, 2)
            embed.add_field(
                name="📈 Probabilidade",
                value=f"Cada face: **{probabilidade}%**\nChance deste resultado: **1/{lados}**",
                inline=True,
            )

        # Footer
        embed.set_footer(
            text=f"Solicitado por {interaction.user}", icon_url=interaction.user.display_avatar.url
        )

        # Adicionar thumbnail baseado no tipo de dado
        if lados == 6:
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎲.png")
        elif lados == 20:
            embed.set_thumbnail(url="https://i.imgur.com/dice20.png")  # D20 para RPG

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(DiceCommand(bot))
