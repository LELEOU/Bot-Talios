"""
Carregador do Sistema de Canais
"""

from .channel_manager import ChannelManager


async def setup(bot):
    await bot.add_cog(ChannelManager(bot))
