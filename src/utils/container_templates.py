"""
Container Templates - Templates para embeds e containers do bot
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class Colors:
    """Cores padrão para embeds"""

    SUCCESS = 0x00FF00
    ERROR = 0xFF0000
    WARNING = 0xFFFF00
    INFO = 0x0099FF
    PREMIUM = 0x9932CC
    DISCORD_BLURPLE = 0x5865F2
    DISCORD_DARK = 0x2F3136
    GOLD = 0xFFD700
    SILVER = 0xC0C0C0
    BRONZE = 0xCD7F32
    PRIMARY = 0x5865F2
    SECONDARY = 0x99AAB5
    ACCENT = 0x9B59B6
    DARK = 0x2C2F33
    LIGHT = 0xFFFFFF


class ContainerType(Enum):
    """Tipos de containers disponíveis"""

    SIMPLE_EMBED = "simple_embed"
    ADVANCED_EMBED = "advanced_embed"
    INTERACTIVE_DASHBOARD = "interactive_dashboard"
    ANNOUNCEMENT = "announcement"
    WELCOME_MESSAGE = "welcome_message"
    MODERATION_LOG = "moderation_log"
    TICKET_EMBED = "ticket_embed"
    GIVEAWAY_EMBED = "giveaway_embed"


# Templates disponíveis
CONTAINER_TEMPLATES = {
    # EMBED SIMPLES
    "simple_announcement": {
        "name": "📢 Anúncio Simples",
        "description": "Embed básico para anúncios gerais",
        "category": "basic",
        "type": "simple_embed",
        "premium": False,
        "config": {
            "accent_color": Colors.DISCORD_BLURPLE,
            "title": "📢 **Anúncio**",
            "description": "{content}",
            "thumbnail": None,
            "image": None,
            "footer": "Enviado por {author}",
            "timestamp": True,
            "fields": [],
        },
    },
    "professional_embed": {
        "name": "🌟 Embed Profissional",
        "description": "Container estilo profissional com layout organizado",
        "category": "professional",
        "type": "advanced_embed",
        "premium": False,
        "config": {
            "accent_color": Colors.PREMIUM,
            "title": "🎯 **Sistema Avançado de Gerenciamento**",
            "description": "**Painel de controle completo para administração do servidor**\\n\\n*Recursos disponíveis abaixo:*",
            "thumbnail": "https://cdn.discordapp.com/attachments/placeholder/image.png",
            "image": None,
            "footer": "💎 Sistema Enterprise • Desenvolvido com tecnologia avançada",
            "timestamp": True,
            "fields": [
                {
                    "name": "⚙️ **Configurações**",
                    "value": "• Moderação automática\\n• Sistema de logs\\n• Anti-spam inteligente",
                    "inline": True,
                },
                {
                    "name": "👥 **Membros**",
                    "value": "• Autorole configurado\\n• Sistema de níveis\\n• Controle de permissões",
                    "inline": True,
                },
                {
                    "name": "🛡️ **Segurança**",
                    "value": "• Proteção avançada\\n• Backup automático\\n• Monitoramento 24/7",
                    "inline": True,
                },
            ],
        },
    },
    "dashboard_style": {
        "name": "📊 Dashboard Interativo",
        "description": "Painel de controle estilo dashboard com estatísticas",
        "category": "professional",
        "type": "interactive_dashboard",
        "premium": True,
        "config": {
            "accent_color": Colors.DISCORD_DARK,
            "title": "📊 **Dashboard do Servidor**",
            "description": "**Estatísticas em tempo real e controles administrativos**",
            "thumbnail": None,
            "image": "https://cdn.discordapp.com/attachments/placeholder/dashboard.png",
            "footer": "🔄 Atualizado a cada minuto • Dashboard v2.0",
            "timestamp": True,
            "fields": [
                {
                    "name": "📈 **Estatísticas**",
                    "value": "```yml\\nMembros Online: 1,247\\nMensagens Hoje: 3,521\\nNovos Membros: 12```",
                    "inline": False,
                },
                {
                    "name": "🎮 **Atividade**",
                    "value": "**Mais Ativo:** #geral (89 msgs)\\n**Comando Mais Usado:** /level\\n**Usuário Mais Ativo:** @Usuario#1234",
                    "inline": True,
                },
                {
                    "name": "🛡️ **Moderação**",
                    "value": "**Warns Aplicados:** 3\\n**Bans Temporários:** 1\\n**Mensagens Deletadas:** 8",
                    "inline": True,
                },
            ],
        },
    },
    "welcome_premium": {
        "name": "🎉 Boas-vindas Premium",
        "description": "Sistema de boas-vindas profissional com design moderno",
        "category": "welcome",
        "type": "welcome_card",
        "premium": True,
        "config": {
            "accent_color": Colors.SUCCESS,
            "title": "🎉 **Bem-vindo(a) ao Servidor!**",
            "description": "**Olá {user}, seja muito bem-vindo(a) ao nosso servidor!**\\n\\n🌟 Você é nosso **{memberCount}º** membro!\\n\\n**📋 Próximos passos:**\\n• Leia as regras em <#rules>\\n• Pegue seus cargos em <#roles>\\n• Apresente-se em <#apresentações>\\n\\n*Divirta-se e faça novos amigos!*",
            "thumbnail": "{user.avatar}",
            "image": "https://cdn.discordapp.com/attachments/placeholder/welcome-banner.png",
            "footer": "💫 Servidor Premium • Bem-vindo à família!",
            "timestamp": True,
            "fields": [],
        },
    },
    "announcement_pro": {
        "name": "📢 Anúncio Profissional",
        "description": "Template para anúncios importantes com destaque visual",
        "category": "communication",
        "type": "announcement",
        "premium": False,
        "config": {
            "accent_color": Colors.WARNING,
            "title": "📢 **ANÚNCIO IMPORTANTE**",
            "description": "**Atenção todos os membros!**\\n\\n🔔 **Nova atualização disponível:**\\n\\n• Sistema de níveis reformulado\\n• Novos comandos de moderação\\n• Interface melhorada\\n• Correções de bugs\\n\\n**📅 Implementado:** Hoje às 15:00\\n**🔧 Tempo de manutenção:** ~30 minutos\\n\\n*Agradecemos a compreensão!*",
            "thumbnail": None,
            "image": None,
            "footer": "🚀 Equipe de Desenvolvimento • Sempre evoluindo",
            "timestamp": True,
            "fields": [
                {
                    "name": "✨ **Novidades**",
                    "value": "• Design renovado\\n• Performance aprimorada\\n• Novos recursos",
                    "inline": True,
                },
                {
                    "name": "🔧 **Correções**",
                    "value": "• Bugs corrigidos\\n• Estabilidade melhorada\\n• Otimizações gerais",
                    "inline": True,
                },
            ],
        },
    },
    "simple_container": {
        "name": "📦 Container Básico",
        "description": "Container simples com texto e cor de destaque",
        "category": "basic",
        "type": "container",
        "premium": False,
        "config": {
            "accent_color": Colors.PRIMARY,
            "title": "🎯 **Container Profissional**",
            "description": "**Bem-vindo ao Sistema Avançado!**\\n\\n**Recursos:**\\n• Layout responsivo e moderno\\n• Suporte completo a markdown\\n• Personalização avançada de cores\\n• Compatibilidade total com Discord\\n\\n*Este é um exemplo de container simples mas profissional.*",
            "footer": "Criado com Sistema Avançado",
            "timestamp": True,
        },
    },
}


class ContainerTemplateManager:
    """Gerenciador de templates de containers"""

    def __init__(self) -> None:
        self.templates: dict[str, dict[str, Any]] = CONTAINER_TEMPLATES

    def get_template(self, template_name: str) -> dict[str, Any] | None:
        """Buscar template por nome"""
        return self.templates.get(template_name)

    def get_templates_by_category(self, category: str) -> list[dict[str, Any]]:
        """Buscar templates por categoria"""
        return [
            template for template in self.templates.values() if template.get("category") == category
        ]

    def get_templates_by_type(self, container_type: ContainerType) -> list[dict[str, Any]]:
        """Buscar templates por tipo"""
        return [
            template
            for template in self.templates.values()
            if template.get("type") == container_type.value
        ]

    def create_embed_from_template(self, template_name: str, **kwargs: Any) -> Any:
        """Criar embed baseado em template"""
        import discord

        template = self.get_template(template_name)
        if not template:
            return None

        config = template["config"].copy()

        # Substituir placeholders
        for key, value in kwargs.items():
            for config_key, config_value in config.items():
                if isinstance(config_value, str):
                    config[config_key] = config_value.replace(f"{{{key}}}", str(value))
                elif isinstance(config_value, list):
                    # Substituir em fields
                    for field in config_value:
                        if isinstance(field, dict):
                            for field_key, field_value in field.items():
                                if isinstance(field_value, str):
                                    field[field_key] = field_value.replace(f"{{{key}}}", str(value))

        # Criar embed
        embed = discord.Embed(
            title=config.get("title"),
            description=config.get("description"),
            color=config.get("accent_color", Colors.PRIMARY),
        )

        # Adicionar elementos opcionais
        if config.get("thumbnail"):
            embed.set_thumbnail(url=config["thumbnail"])

        if config.get("image"):
            embed.set_image(url=config["image"])

        if config.get("footer"):
            embed.set_footer(text=config["footer"])

        if config.get("timestamp"):
            embed.timestamp = datetime.utcnow()

        # Adicionar fields
        for field in config.get("fields", []):
            embed.add_field(
                name=field.get("name", ""),
                value=field.get("value", ""),
                inline=field.get("inline", False),
            )

        return embed

    def list_templates(self, premium_only: bool = False) -> list[str]:
        """Listar nomes dos templates disponíveis"""
        if premium_only:
            return [
                name for name, template in self.templates.items() if template.get("premium", False)
            ]
        return list(self.templates.keys())

    def get_categories(self) -> list[str]:
        """Buscar todas as categorias disponíveis"""
        categories: set[str] = set()
        for template in self.templates.values():
            if template.get("category"):
                categories.add(template["category"])
        return sorted(list(categories))

    def validate_template_config(self, config: dict[str, Any]) -> dict[str, list[str]]:
        """Validar configuração de template"""
        errors: list[str] = []
        warnings: list[str] = []

        required_fields = ["accent_color", "title", "description"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Campo obrigatório ausente: {field}")

        # Validar cor
        if "accent_color" in config:
            color = config["accent_color"]
            if not isinstance(color, int) or color < 0 or color > 0xFFFFFF:
                errors.append("accent_color deve ser um valor hexadecimal válido")

        # Validar URLs
        url_fields = ["thumbnail", "image"]
        for field in url_fields:
            if config.get(field):
                if not self._is_valid_url(config[field]):
                    warnings.append(f"URL possivelmente inválida em {field}")

        return {"errors": errors, "warnings": warnings}

    def _is_valid_url(self, url: str) -> bool:
        """Validar se uma string é uma URL válida"""
        url_pattern = re.compile(
            r"^https?://"  # http:// ou https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
            r"(?::\d+)?"  # porta opcional
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        return bool(url_pattern.match(url))
