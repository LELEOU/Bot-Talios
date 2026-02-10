"""
Carregador do Sistema de Anúncios
"""

from .announce_advanced import AnnounceSystem


async def setup(bot):
    await bot.add_cog(AnnounceSystem(bot))
