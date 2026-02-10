"""
Comandos do Bot Discord Modular - Python Version
Sistema completo de comandos organizados por categoria
"""

# Versão do sistema de comandos
__version__ = "3.0.0"
__author__ = "Discord Bot Team"

# Categorias disponíveis
CATEGORIES = [
    "admin",
    "announce",
    "antispam",
    "autorole",
    "backup",
    "ban",
    "case",
    "channel",
    "communication",
    "embed",
    "fun",
    "giveaway",
    "levelcard",
    "leveling",
    "logs",
    "moderation",
    "music",
    "mute",
    "note",
    "poll",
    "role",
    "sticky",
    "suggestion",
    "ticket",
    "user",
    "utility",
    "voice",
    "welcome",
]

# Comandos essenciais já convertidos
CONVERTED_COMMANDS = {
    "utility": ["status", "ping", "server_info", "container_builder"],
    "fun": ["8ball", "dice", "coinflip", "meme"],
    "moderation": ["kick", "warn", "purge", "slowmode"],
    "communication": ["say"],
    "music": ["play"],
}

# Total de comandos convertidos
TOTAL_CONVERTED = sum(len(cmds) for cmds in CONVERTED_COMMANDS.values())

# Sistema de comandos inicializado
# print(f"🚀 Sistema de Comandos v{__version__}")
# print(f"📊 {TOTAL_CONVERTED} comandos convertidos")
# print(f"📁 {len(CATEGORIES)} categorias disponíveis")
