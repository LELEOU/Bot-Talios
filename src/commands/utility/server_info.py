"""
Comando Server Info - Utility
Exibe informações detalhadas do servidor
"""


import discord
from discord import app_commands
from discord.ext import commands


class ServerInfoCommand(commands.Cog):
    """Comando de informações do servidor"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="server-info", description="Exibe informações detalhadas do servidor"
    )
    async def server_info(self, interaction: discord.Interaction):
        """Mostrar informações do servidor"""

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em servidores!", ephemeral=True
            )
            return

        # Contadores de canais por tipo
        text_channels = len([ch for ch in guild.channels if isinstance(ch, discord.TextChannel)])
        voice_channels = len([ch for ch in guild.channels if isinstance(ch, discord.VoiceChannel)])
        stage_channels = len([ch for ch in guild.channels if isinstance(ch, discord.StageChannel)])
        forum_channels = len([ch for ch in guild.channels if isinstance(ch, discord.ForumChannel)])
        categories = len([ch for ch in guild.channels if isinstance(ch, discord.CategoryChannel)])

        # Contadores de membros
        total_members = guild.member_count
        bots = len([m for m in guild.members if m.bot])
        humans = total_members - bots

        # Status dos membros
        online = len([m for m in guild.members if m.status == discord.Status.online])
        idle = len([m for m in guild.members if m.status == discord.Status.idle])
        dnd = len([m for m in guild.members if m.status == discord.Status.dnd])
        offline = len([m for m in guild.members if m.status == discord.Status.offline])

        # Níveis de verificação
        verification_levels = {
            discord.VerificationLevel.none: "Nenhum",
            discord.VerificationLevel.low: "Baixo",
            discord.VerificationLevel.medium: "Médio",
            discord.VerificationLevel.high: "Alto",
            discord.VerificationLevel.highest: "Máximo",
        }

        # Filtro de conteúdo
        content_filter = {
            discord.ContentFilter.disabled: "Desabilitado",
            discord.ContentFilter.no_role: "Membros sem cargo",
            discord.ContentFilter.all_members: "Todos os membros",
        }

        # Boost info
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count or 0

        # Criar embed
        embed = discord.Embed(
            title="📊 Informações do Servidor",
            description=f"**{guild.name}**",
            color=0x00BFFF,
            timestamp=discord.utils.utcnow(),
        )

        # Ícone do servidor
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Banner se existir
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        # Informações básicas
        embed.add_field(
            name="🆔 Informações Básicas",
            value=f"**ID:** `{guild.id}`\n"
            f"**Proprietário:** <@{guild.owner_id}>\n"
            f"**Criado em:** <t:{int(guild.created_at.timestamp())}:F>\n"
            f"**Região:** {guild.preferred_locale}",
            inline=False,
        )

        # Membros
        embed.add_field(
            name="👥 Membros",
            value=f"**Total:** {total_members:,}\n"
            f"**Humanos:** {humans:,}\n"
            f"**Bots:** {bots:,}\n"
            f"**Máximo:** {guild.max_members:,}",
            inline=True,
        )

        # Status dos membros
        embed.add_field(
            name="📊 Status",
            value=f"🟢 Online: {online}\n"
            f"🟡 Ausente: {idle}\n"
            f"🔴 Ocupado: {dnd}\n"
            f"⚫ Offline: {offline}",
            inline=True,
        )

        # Canais
        embed.add_field(
            name="📺 Canais",
            value=f"**Total:** {len(guild.channels)}\n"
            f"📝 Texto: {text_channels}\n"
            f"🔊 Voz: {voice_channels}\n"
            f"🎭 Palco: {stage_channels}\n"
            f"💬 Fórum: {forum_channels}\n"
            f"📁 Categorias: {categories}",
            inline=True,
        )

        # Cargos e emojis
        embed.add_field(
            name="🎭 Recursos",
            value=f"**Cargos:** {len(guild.roles)}\n"
            f"**Emojis:** {len(guild.emojis)}/{guild.emoji_limit}\n"
            f"**Stickers:** {len(guild.stickers)}\n"
            f"**Recursos:** {len(guild.features)}",
            inline=True,
        )

        # Boost e segurança
        embed.add_field(
            name="🚀 Boost & Segurança",
            value=f"**Nível:** {boost_level}/3\n"
            f"**Boosts:** {boost_count}\n"
            f"**Verificação:** {verification_levels.get(guild.verification_level, 'Desconhecido')}\n"
            f"**Filtro:** {content_filter.get(guild.explicit_content_filter, 'Desconhecido')}",
            inline=True,
        )

        # Recursos especiais se existirem
        if guild.features:
            features_display = []
            feature_names = {
                "ANIMATED_ICON": "🎬 Ícone Animado",
                "BANNER": "🖼️ Banner",
                "COMMERCE": "🛒 Loja",
                "COMMUNITY": "🌐 Comunidade",
                "DISCOVERABLE": "🔍 Descobrível",
                "FEATURABLE": "⭐ Destacável",
                "INVITE_SPLASH": "🎨 Splash de Convite",
                "MEMBER_VERIFICATION_GATE_ENABLED": "🚪 Verificação de Membros",
                "NEWS": "📰 Canais de Notícias",
                "PARTNERED": "🤝 Parceiro",
                "PREVIEW_ENABLED": "👀 Preview Habilitado",
                "VANITY_URL": "🔗 URL Personalizada",
                "VERIFIED": "✅ Verificado",
                "VIP_REGIONS": "🌍 Regiões VIP",
                "WELCOME_SCREEN_ENABLED": "🎊 Tela de Boas-vindas",
            }

            for feature in guild.features[:8]:  # Limitar para não ficar muito longo
                if feature in feature_names:
                    features_display.append(feature_names[feature])

            if features_display:
                embed.add_field(
                    name="✨ Recursos Especiais", value="\n".join(features_display), inline=False
                )

        embed.set_footer(
            text=f"Solicitado por {interaction.user}", icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(ServerInfoCommand(bot))
