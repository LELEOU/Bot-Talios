"""
Comando Coinflip - Fun
Cara ou coroa com apostas
"""

import random
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands


class CoinflipCommand(commands.Cog):
    """Comando cara ou coroa"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="coinflip", description="Cara ou coroa - teste sua sorte!")
    @app_commands.describe(aposta="Sua aposta (cara ou coroa)")
    async def coinflip(
        self, interaction: discord.Interaction, aposta: Literal["cara", "coroa"] = None
    ):
        """Jogar cara ou coroa"""

        # Determinar resultado
        resultado = random.choice(["cara", "coroa"])
        emoji = "🪙" if resultado == "cara" else "👑"

        # Texto do resultado
        result_text = f"{emoji} **{resultado.upper()}**!"
        color = 0x0099FF

        # Se houve aposta, verificar se ganhou
        if aposta:
            ganhou = aposta == resultado
            if ganhou:
                result_text += "\n\n🎉 **Você ganhou!** 🎉"
                color = 0x00FF00
            else:
                result_text += "\n\n😔 **Você perdeu!** 💔"
                color = 0xFF0000

        # Criar embed
        embed = discord.Embed(
            title="🪙 Cara ou Coroa",
            description=result_text,
            color=color,
            timestamp=discord.utils.utcnow(),
        )

        # Se houve aposta, mostrar detalhes
        if aposta:
            embed.add_field(name="💰 Sua Aposta", value=aposta.capitalize(), inline=True)

            embed.add_field(name="🎯 Resultado", value=resultado.capitalize(), inline=True)

            # Calcular estatísticas da "sorte"
            if ganhou:
                embed.add_field(
                    name="📊 Estatísticas",
                    value="🍀 **50%** de chance\n✅ **Acertou!**",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="📊 Estatísticas", value="💀 **50%** de chance\n❌ **Errou!**", inline=True
                )
        else:
            # Sem aposta, só mostrar informações gerais
            embed.add_field(name="🎲 Probabilidade", value="**50%** para cada lado", inline=True)

            embed.add_field(
                name="💡 Dica", value="Use `/coinflip aposta:cara` para apostar!", inline=True
            )

        # Adicionar animação visual baseada no resultado
        if resultado == "cara":
            embed.set_thumbnail(url="https://i.imgur.com/coin_heads.png")  # Placeholder
            embed.add_field(
                name="🪙 Face da Moeda", value='**CARA** - O lado "nobre" da moeda', inline=False
            )
        else:
            embed.set_thumbnail(url="https://i.imgur.com/coin_tails.png")  # Placeholder
            embed.add_field(
                name="👑 Verso da Moeda", value="**COROA** - O lado real da moeda", inline=False
            )

        # Mensagens especiais baseadas na sequência
        messages_especiais = [
            "🎪 A moeda gira no ar...",
            "✨ Os deuses da sorte decidem...",
            "🌟 O destino foi selado!",
            "🎭 A sorte está lançada!",
            "🔮 As probabilidades se alinham...",
        ]

        embed.set_footer(
            text=f"{random.choice(messages_especiais)} • Solicitado por {interaction.user}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(CoinflipCommand(bot))
