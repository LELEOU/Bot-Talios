"""
Sistema de Antispam - Módulo completo
Sistema avançado de proteção contra spam
"""

from .antispam_advanced import AntispamRules
from .antispam_config import AntispamConfig
from .antispam_stats import AntispamStats


async def setup(bot):
    await bot.add_cog(AntispamConfig(bot))
    await bot.add_cog(AntispamStats(bot))
    await bot.add_cog(AntispamRules(bot))
