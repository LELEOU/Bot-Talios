"""
Utilitários de Permissões - Sistema completo
Funções para verificar permissões, roles, hierarquia
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import database


class PermissionChecker:
    """Classe para verificação de permissões avançadas"""

    @staticmethod
    def is_admin(member: discord.Member) -> bool:
        """Verificar se membro é administrador - IGUAL AO JS"""
        return member.guild_permissions.administrator

    @staticmethod
    def is_moderator(member: discord.Member) -> bool:
        """Verificar se membro é moderador"""
        mod_permissions = [
            "kick_members",
            "ban_members",
            "manage_messages",
            "manage_roles",
            "moderate_members",
        ]

        return any(getattr(member.guild_permissions, perm, False) for perm in mod_permissions)

    @staticmethod
    def has_permission(member: discord.Member, permission: str) -> bool:
        """Verificar se membro tem permissão específica"""
        try:
            return getattr(member.guild_permissions, permission, False)
        except AttributeError:
            return False

    @staticmethod
    def has_any_permission(member: discord.Member, permissions: list[str]) -> bool:
        """Verificar se membro tem qualquer uma das permissões"""
        return any(PermissionChecker.has_permission(member, perm) for perm in permissions)

    @staticmethod
    def has_all_permissions(member: discord.Member, permissions: list[str]) -> bool:
        """Verificar se membro tem todas as permissões"""
        return all(PermissionChecker.has_permission(member, perm) for perm in permissions)

    @staticmethod
    def can_manage_member(moderator: discord.Member, target: discord.Member) -> bool:
        """Verificar se moderador pode gerenciar membro alvo"""
        # Não pode gerenciar a si mesmo
        if moderator == target:
            return False

        # Não pode gerenciar o dono do servidor
        if target == target.guild.owner:
            return False

        # Admin pode gerenciar qualquer um (exceto owner)
        if moderator.guild_permissions.administrator:
            return True

        # Verificar hierarquia de roles
        return moderator.top_role > target.top_role

    @staticmethod
    def can_manage_role(member: discord.Member, role: discord.Role) -> bool:
        """Verificar se membro pode gerenciar role"""
        # Precisa de permissão manage_roles
        if not member.guild_permissions.manage_roles:
            return False

        # Não pode gerenciar roles acima da sua hierarquia
        return member.top_role > role

    @staticmethod
    def can_manage_channel(member: discord.Member, channel: discord.abc.GuildChannel) -> bool:
        """Verificar se membro pode gerenciar canal"""
        permissions = channel.permissions_for(member)
        return permissions.manage_channels

    @staticmethod
    async def has_staff_role(member: discord.Member) -> bool:
        """Verificar se membro tem role de staff configurada"""
        try:
            settings = await database.get_guild_settings(str(member.guild.id))

            if not settings or not settings.get("staff_role_ids"):
                # Fallback para roles padrão
                staff_role_names = ["Staff", "Moderator", "Admin", "Suporte", "Helper"]
                return any(role.name in staff_role_names for role in member.roles)

            staff_role_ids = settings["staff_role_ids"]
            return any(role.id in staff_role_ids for role in member.roles)

        except Exception as e:
            print(f"❌ Erro verificando staff role: {e}")
            return False

    @staticmethod
    def is_bot_owner(user: discord.User, bot_owner_ids: list[int] = None) -> bool:
        """Verificar se usuário é owner do bot"""
        if bot_owner_ids:
            return user.id in bot_owner_ids
        return False

    @staticmethod
    def get_permission_level(member: discord.Member) -> int:
        """Retornar nível de permissão (0-4)"""
        if member == member.guild.owner:
            return 4  # Owner
        if member.guild_permissions.administrator:
            return 3  # Admin
        if PermissionChecker.is_moderator(member):
            return 2  # Moderador
        if any(role.name.lower() in ["helper", "suporte", "staff"] for role in member.roles):
            return 1  # Staff
        return 0  # Usuário comum

    @staticmethod
    def format_permissions(permissions: discord.Permissions) -> list[str]:
        """Formatar permissões para lista legível"""
        perm_names = {
            "administrator": "Administrador",
            "kick_members": "Expulsar Membros",
            "ban_members": "Banir Membros",
            "manage_channels": "Gerenciar Canais",
            "manage_guild": "Gerenciar Servidor",
            "manage_messages": "Gerenciar Mensagens",
            "manage_nicknames": "Gerenciar Apelidos",
            "manage_roles": "Gerenciar Cargos",
            "manage_webhooks": "Gerenciar Webhooks",
            "moderate_members": "Moderar Membros",
            "send_messages": "Enviar Mensagens",
            "embed_links": "Inserir Links",
            "attach_files": "Anexar Arquivos",
            "read_message_history": "Ler Histórico",
            "mention_everyone": "Mencionar Everyone",
            "use_external_emojis": "Usar Emojis Externos",
            "add_reactions": "Adicionar Reações",
            "connect": "Conectar em Voz",
            "speak": "Falar em Voz",
            "stream": "Transmitir",
            "use_voice_activation": "Usar Ativação por Voz",
            "mute_members": "Mutar Membros",
            "deafen_members": "Ensurdecer Membros",
            "move_members": "Mover Membros",
            "use_slash_commands": "Usar Comandos Slash",
        }

        active_perms = []
        for perm, value in permissions:
            if value and perm in perm_names:
                active_perms.append(perm_names[perm])

        return sorted(active_perms)


class CommandPermissions:
    """Sistema de permissões para comandos"""

    @staticmethod
    def admin_only() -> commands.Check[Any]:
        """Decorator para comandos apenas de admin"""

        def predicate(interaction: discord.Interaction) -> bool:
            if not interaction.user.guild_permissions.administrator:
                return False
            return True

        return commands.check(predicate)

    @staticmethod
    def moderator_only() -> commands.Check[Any]:
        """Decorator para comandos apenas de moderadores"""

        def predicate(interaction: discord.Interaction) -> bool:
            return PermissionChecker.is_moderator(interaction.user)

        return commands.check(predicate)

    @staticmethod
    def staff_only() -> commands.Check[Any]:
        """Decorator para comandos apenas de staff"""

        async def predicate(interaction: discord.Interaction) -> bool:
            return await PermissionChecker.has_staff_role(interaction.user)

        return commands.check(predicate)

    @staticmethod
    def requires_permissions(*permissions: str) -> commands.Check[Any]:
        """Decorator para comandos que requerem permissões específicas"""

        def predicate(interaction: discord.Interaction) -> bool:
            return PermissionChecker.has_all_permissions(interaction.user, list(permissions))

        return commands.check(predicate)

    @staticmethod
    def bot_owner_only(owner_ids: list[int]) -> commands.Check[Any]:
        """Decorator para comandos apenas do owner do bot"""

        def predicate(interaction: discord.Interaction) -> bool:
            return interaction.user.id in owner_ids

        return commands.check(predicate)


class ChannelPermissions:
    """Utilitários para permissões de canal"""

    @staticmethod
    def can_send_messages(member: discord.Member, channel: discord.TextChannel) -> bool:
        """Verificar se pode enviar mensagens no canal"""
        permissions = channel.permissions_for(member)
        return permissions.send_messages

    @staticmethod
    def can_embed_links(member: discord.Member, channel: discord.TextChannel) -> bool:
        """Verificar se pode inserir links no canal"""
        permissions = channel.permissions_for(member)
        return permissions.embed_links

    @staticmethod
    def can_attach_files(member: discord.Member, channel: discord.TextChannel) -> bool:
        """Verificar se pode anexar arquivos no canal"""
        permissions = channel.permissions_for(member)
        return permissions.attach_files

    @staticmethod
    def can_manage_messages(member: discord.Member, channel: discord.TextChannel) -> bool:
        """Verificar se pode gerenciar mensagens no canal"""
        permissions = channel.permissions_for(member)
        return permissions.manage_messages

    @staticmethod
    def can_use_external_emojis(member: discord.Member, channel: discord.TextChannel) -> bool:
        """Verificar se pode usar emojis externos no canal"""
        permissions = channel.permissions_for(member)
        return permissions.use_external_emojis

    @staticmethod
    def get_missing_permissions(
        member: discord.Member, channel: discord.TextChannel, required_perms: list[str]
    ) -> list[str]:
        """Retornar permissões faltantes para o canal"""
        permissions = channel.permissions_for(member)
        missing = []

        for perm in required_perms:
            if not getattr(permissions, perm, False):
                missing.append(perm)

        return missing


class RoleHierarchy:
    """Utilitários para hierarquia de roles"""

    @staticmethod
    def get_highest_role(member: discord.Member) -> discord.Role:
        """Retornar role mais alta do membro"""
        return member.top_role

    @staticmethod
    def compare_hierarchy(member1: discord.Member, member2: discord.Member) -> int:
        """Comparar hierarquia entre membros (-1, 0, 1)"""
        if member1.top_role.position > member2.top_role.position:
            return 1
        if member1.top_role.position < member2.top_role.position:
            return -1
        return 0

    @staticmethod
    def can_assign_role(moderator: discord.Member, role: discord.Role) -> bool:
        """Verificar se pode atribuir role"""
        if not moderator.guild_permissions.manage_roles:
            return False

        # Não pode atribuir roles acima da sua hierarquia
        return moderator.top_role > role

    @staticmethod
    def get_assignable_roles(member: discord.Member) -> list[discord.Role]:
        """Retornar roles que o membro pode atribuir"""
        if not member.guild_permissions.manage_roles:
            return []

        assignable = []
        for role in member.guild.roles:
            if role < member.top_role and not role.is_default():
                assignable.append(role)

        return assignable


# Instâncias globais para uso fácil
permission_checker = PermissionChecker()
command_permissions = CommandPermissions()
channel_permissions = ChannelPermissions()
role_hierarchy = RoleHierarchy()


# Funções de conveniência (compatibilidade com JS)
def is_admin(member: discord.Member) -> bool:
    """Função de conveniência para compatibilidade"""
    return PermissionChecker.is_admin(member)


def is_moderator(member: discord.Member) -> bool:
    """Função de conveniência para compatibilidade"""
    return PermissionChecker.is_moderator(member)


def can_manage_member(moderator: discord.Member, target: discord.Member) -> bool:
    """Função de conveniência para compatibilidade"""
    return PermissionChecker.can_manage_member(moderator, target)
