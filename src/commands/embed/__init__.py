"""
Carregador do Sistema de Embeds
"""

from .embed_builder import EmbedBuilder


async def setup(bot):
    await bot.add_cog(EmbedBuilder(bot))
