"""
Sistema de Notes - Módulo completo
Sistema avançado de anotações de usuários
"""

from .note_create import NotesCreation
from .note_manage import NotesManagement


async def setup(bot):
    await bot.add_cog(NotesCreation(bot))
    await bot.add_cog(NotesManagement(bot))
