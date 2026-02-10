"""
Comando Ping - Utility
Verificar latência do bot
"""

import time

import discord
from discord import app_commands
from discord.ext import commands


class PingCommand(commands.Cog):
    """Comando para verificar latência"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the latency of the bot!")
    async def ping(self, interaction: discord.Interaction):
        """Verificar latência do bot"""

        # Enviar mensagem inicial
        start_time = time.time()
        await interaction.response.send_message("Calculando ping...")
        end_time = time.time()

        # Calcular latências
        roundtrip_latency = int((end_time - start_time) * 1000)
        websocket_latency = int(self.bot.latency * 1000)

        # Determinar qualidade da conexão
        if roundtrip_latency < 100:
            qualidade = "🟢 Excelente"
            color = 0x00FF00
        elif roundtrip_latency < 200:
            qualidade = "🟡 Boa"
            color = 0xFFFF00
        elif roundtrip_latency < 500:
            qualidade = "🟠 Regular"
            color = 0xFF9900
        else:
            qualidade = "🔴 Ruim"
            color = 0xFF0000

        embed = discord.Embed(title="🏓 Pong!", color=color, timestamp=discord.utils.utcnow())

        embed.add_field(name="📡 Latência da API", value=f"{roundtrip_latency}ms", inline=True)
        embed.add_field(
            name="💓 Latência do WebSocket", value=f"{websocket_latency}ms", inline=True
        )
        embed.add_field(name="📊 Qualidade", value=qualidade, inline=True)

        embed.set_footer(text=f"Solicitado por {interaction.user}")

        await interaction.edit_original_response(content="", embed=embed)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(PingCommand(bot))
