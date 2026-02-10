"""
Carregador do Sistema de Comunicação
"""

from .communication_system import CommunicationSystem


async def setup(bot):
    await bot.add_cog(CommunicationSystem(bot))
