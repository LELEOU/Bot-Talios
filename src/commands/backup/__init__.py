"""
Sistema de Backup - Módulo completo
Sistema avançado de backup e restauração
"""

from .backup_create import ServerBackup
from .backup_manage import BackupManagement


async def setup(bot):
    await bot.add_cog(ServerBackup(bot))
    await bot.add_cog(BackupManagement(bot))
