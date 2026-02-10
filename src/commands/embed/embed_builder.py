"""
Sistema Avançado de Embeds
Editor e construtor de embeds com import/export JSON
"""

import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands


class EmbedBuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed-builder", description="🎨 Construtor avançado de embeds")
    @app_commands.describe(
        titulo="Título do embed",
        descricao="Descrição do embed",
        cor="Cor em hexadecimal (ex: #0099ff)",
        url="URL do título (clicável)",
        author="Nome do autor",
        author_icon="URL do ícone do autor",
        author_url="URL do autor (clicável)",
        thumbnail="URL do thumbnail (imagem pequena)",
        imagem="URL da imagem principal",
        footer="Texto do footer",
        footer_icon="URL do ícone do footer",
        canal="Canal onde enviar o embed",
        timestamp="Adicionar timestamp atual",
    )
    async def embed_builder(
        self,
        interaction: discord.Interaction,
        titulo: str | None = None,
        descricao: str | None = None,
        cor: str | None = None,
        url: str | None = None,
        author: str | None = None,
        author_icon: str | None = None,
        author_url: str | None = None,
        thumbnail: str | None = None,
        imagem: str | None = None,
        footer: str | None = None,
        footer_icon: str | None = None,
        canal: discord.TextChannel | None = None,
        timestamp: bool = False,
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message(
                    "❌ **Permissão Insuficiente**\n"
                    "Você precisa da permissão `Gerenciar Mensagens` para usar este comando.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Verificar se pelo menos algum conteúdo foi fornecido
            if not any([titulo, descricao, author, footer, imagem, thumbnail]):
                await interaction.followup.send(
                    "❌ **Embed Vazio**\n"
                    "Forneça pelo menos um dos seguintes: título, descrição, autor, footer ou imagem.",
                    ephemeral=True,
                )
                return

            # Validar cor
            color_int = 0x0099FF  # Cor padrão
            if cor:
                color_match = re.match(r"^#?([0-9a-fA-F]{6})$", cor)
                if color_match:
                    color_int = int(color_match.group(1), 16)
                else:
                    await interaction.followup.send(
                        "❌ **Cor Inválida**\n"
                        "Use formato hexadecimal válido: `#0099ff` ou `0099ff`",
                        ephemeral=True,
                    )
                    return

            # Validar URLs
            urls_to_validate = [
                ("URL do título", url),
                ("Ícone do autor", author_icon),
                ("URL do autor", author_url),
                ("Thumbnail", thumbnail),
                ("Imagem", imagem),
                ("Ícone do footer", footer_icon),
            ]

            for url_name, url_value in urls_to_validate:
                if url_value and not self._is_valid_url(url_value):
                    await interaction.followup.send(
                        f"❌ **{url_name} Inválida**\nA URL fornecida não é válida: `{url_value}`",
                        ephemeral=True,
                    )
                    return

            # Verificar menções perigosas
            text_content = " ".join(filter(None, [titulo, descricao, author, footer]))
            has_dangerous_mentions = "@everyone" in text_content or "@here" in text_content

            if has_dangerous_mentions and not interaction.user.guild_permissions.mention_everyone:
                await interaction.followup.send(
                    "❌ **Menções Não Permitidas**\n"
                    "Você não tem permissão para incluir @everyone/@here em embeds.",
                    ephemeral=True,
                )
                return

            # Criar embed
            try:
                embed = discord.Embed(color=color_int)

                if titulo:
                    embed.title = titulo

                if descricao:
                    embed.description = descricao

                if url:
                    embed.url = url

                if author:
                    embed.set_author(name=author, icon_url=author_icon, url=author_url)

                if thumbnail:
                    embed.set_thumbnail(url=thumbnail)

                if imagem:
                    embed.set_image(url=imagem)

                if footer:
                    embed.set_footer(text=footer, icon_url=footer_icon)

                if timestamp:
                    embed.timestamp = datetime.now()

            except Exception as e:
                await interaction.followup.send(
                    f"❌ **Erro na Criação do Embed**\nErro: {e!s}", ephemeral=True
                )
                return

            # Determinar canal de destino
            target_channel = canal or interaction.channel

            # Verificar se é um canal de texto
            if not isinstance(target_channel, discord.TextChannel):
                await interaction.followup.send(
                    "❌ **Canal Inválido**\nEmbeds só podem ser enviados em canais de texto.",
                    ephemeral=True,
                )
                return

            # Verificar permissões do bot
            bot_perms = target_channel.permissions_for(interaction.guild.me)
            if not (bot_perms.send_messages and bot_perms.embed_links):
                await interaction.followup.send(
                    f"❌ **Sem Permissões**\n"
                    f"Não tenho permissão para enviar embeds em {target_channel.mention}.\n"
                    f"Permissões necessárias: `Enviar Mensagens`, `Inserir Links`",
                    ephemeral=True,
                )
                return

            try:
                # Enviar embed
                allowed_mentions = discord.AllowedMentions(
                    everyone=has_dangerous_mentions and "@everyone" in text_content,
                    here=has_dangerous_mentions and "@here" in text_content,
                    users=True,
                    roles=True,
                )

                sent_message = await target_channel.send(
                    embed=embed, allowed_mentions=allowed_mentions
                )

            except discord.HTTPException as e:
                await interaction.followup.send(
                    f"❌ **Erro do Discord**\n"
                    f"Não consegui enviar o embed: {e!s}\n"
                    "Verifique se o conteúdo está dentro dos limites do Discord.",
                    ephemeral=True,
                )
                return
            except Exception as e:
                print(f"❌ Erro ao enviar embed: {e}")
                await interaction.followup.send(
                    "❌ **Erro do Sistema**\nOcorreu um erro ao enviar o embed.", ephemeral=True
                )
                return

            # Embed de confirmação
            success_embed = discord.Embed(
                title="✅ **EMBED CRIADO**",
                description=f"Embed enviado com sucesso{'!' if target_channel == interaction.channel else f' para {target_channel.mention}!'}",
                color=0x00FF00,
                timestamp=datetime.now(),
            )

            # Estatísticas do embed
            embed_stats = []
            if titulo:
                embed_stats.append(f"📝 Título: {len(titulo)} chars")
            if descricao:
                embed_stats.append(f"📄 Descrição: {len(descricao)} chars")
            if author:
                embed_stats.append(f"👤 Autor: {author}")
            if footer:
                embed_stats.append(f"📋 Footer: {footer}")
            if imagem:
                embed_stats.append("🖼️ Imagem principal")
            if thumbnail:
                embed_stats.append("🔸 Thumbnail")
            if timestamp:
                embed_stats.append("⏰ Timestamp")

            if embed_stats:
                success_embed.add_field(
                    name="📊 Componentes do Embed", value="\n".join(embed_stats), inline=False
                )

            success_embed.add_field(
                name="🎨 Detalhes Técnicos",
                value=f"**Cor:** #{format(color_int, '06x').upper()}\n"
                f"**Canal:** {target_channel.mention}\n"
                f"**ID da Mensagem:** `{sent_message.id}`",
                inline=False,
            )

            # Link direto
            message_link = f"https://discord.com/channels/{interaction.guild.id}/{target_channel.id}/{sent_message.id}"
            success_embed.add_field(
                name="🔗 Link Direto", value=f"[Ir para embed]({message_link})", inline=False
            )

            success_embed.set_footer(
                text=f"Criado por {interaction.user}", icon_url=interaction.user.display_avatar.url
            )

            # Adicionar preview do JSON
            json_data = self._embed_to_json(embed)
            if len(json_data) < 1000:
                success_embed.add_field(
                    name="📄 Código JSON (para reutilizar)",
                    value=f"```json\n{json_data}\n```",
                    inline=False,
                )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Erro no embed-builder: {e}")
            try:
                await interaction.followup.send(
                    "❌ **Erro Crítico**\nOcorreu um erro inesperado ao criar o embed.",
                    ephemeral=True,
                )
            except:
                try:
                    await interaction.response.send_message(
                        "❌ Erro ao processar comando.", ephemeral=True
                    )
                except:
                    pass

    @app_commands.command(name="embed-json", description="📋 Criar embed a partir de código JSON")
    @app_commands.describe(json_code="Código JSON do embed", canal="Canal onde enviar o embed")
    async def embed_json(
        self,
        interaction: discord.Interaction,
        json_code: str,
        canal: discord.TextChannel | None = None,
    ):
        try:
            # Verificar permissões
            if not interaction.user.guild_permissions.manage_messages:
                await interaction.response.send_message(
                    "❌ **Permissão Insuficiente**\n"
                    "Você precisa da permissão `Gerenciar Mensagens` para usar este comando.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Tentar decodificar JSON
            try:
                cleaned_json = json_code.strip()
                if cleaned_json.startswith("```json"):
                    cleaned_json = cleaned_json[7:]
                if cleaned_json.endswith("```"):
                    cleaned_json = cleaned_json[:-3]
                cleaned_json = cleaned_json.strip()

                embed_data = json.loads(cleaned_json)

            except json.JSONDecodeError as e:
                await interaction.followup.send(
                    f"❌ **JSON Inválido**\n"
                    f"Erro ao decodificar JSON: {e!s}\n"
                    "Certifique-se de que o JSON está bem formatado.",
                    ephemeral=True,
                )
                return

            # Criar embed a partir dos dados JSON
            try:
                embed = self._json_to_embed(embed_data)

            except Exception as e:
                await interaction.followup.send(
                    f"❌ **Erro na Criação do Embed**\nErro ao processar dados do JSON: {e!s}",
                    ephemeral=True,
                )
                return

            # Verificar menções perigosas
            embed_json = embed.to_dict()
            text_content = " ".join(
                filter(
                    None,
                    [
                        embed_json.get("title", ""),
                        embed_json.get("description", ""),
                        embed_json.get("author", {}).get("name", ""),
                        embed_json.get("footer", {}).get("text", ""),
                    ],
                )
            )

            if embed_json.get("fields"):
                for field in embed_json["fields"]:
                    text_content += " " + field.get("name", "") + " " + field.get("value", "")

            has_dangerous_mentions = "@everyone" in text_content or "@here" in text_content

            if has_dangerous_mentions and not interaction.user.guild_permissions.mention_everyone:
                await interaction.followup.send(
                    "❌ **Menções Não Permitidas**\n"
                    "O embed contém @everyone/@here e você não tem permissão para isso.",
                    ephemeral=True,
                )
                return

            # Determinar canal de destino
            target_channel = canal or interaction.channel

            # Verificar permissões do bot
            bot_perms = target_channel.permissions_for(interaction.guild.me)
            if not (bot_perms.send_messages and bot_perms.embed_links):
                await interaction.followup.send(
                    f"❌ **Sem Permissões**\n"
                    f"Não tenho permissão para enviar embeds em {target_channel.mention}.",
                    ephemeral=True,
                )
                return

            try:
                # Enviar embed
                allowed_mentions = discord.AllowedMentions(
                    everyone=has_dangerous_mentions and "@everyone" in text_content,
                    here=has_dangerous_mentions and "@here" in text_content,
                    users=True,
                    roles=True,
                )

                sent_message = await target_channel.send(
                    embed=embed, allowed_mentions=allowed_mentions
                )

                # Confirmação
                success_embed = discord.Embed(
                    title="✅ **EMBED JSON PROCESSADO**",
                    description=f"Embed criado a partir do JSON e enviado{'!' if target_channel == interaction.channel else f' para {target_channel.mention}!'}",
                    color=0x00FF00,
                    timestamp=datetime.now(),
                )

                success_embed.add_field(
                    name="📊 Informações",
                    value=f"**Canal:** {target_channel.mention}\n"
                    f"**ID da Mensagem:** `{sent_message.id}`\n"
                    f"**Tamanho do JSON:** {len(json_code)} caracteres",
                    inline=False,
                )

                # Link direto
                message_link = f"https://discord.com/channels/{interaction.guild.id}/{target_channel.id}/{sent_message.id}"
                success_embed.add_field(
                    name="🔗 Link Direto", value=f"[Ir para embed]({message_link})", inline=False
                )

                success_embed.set_footer(
                    text=f"Importado por {interaction.user}",
                    icon_url=interaction.user.display_avatar.url,
                )

                await interaction.followup.send(embed=success_embed, ephemeral=True)

            except discord.HTTPException as e:
                await interaction.followup.send(
                    f"❌ **Erro do Discord**\nNão consegui enviar o embed: {e!s}", ephemeral=True
                )
                return

        except Exception as e:
            print(f"❌ Erro no embed-json: {e}")
            try:
                await interaction.followup.send(
                    "❌ **Erro Crítico**\nOcorreu um erro inesperado ao processar o JSON.",
                    ephemeral=True,
                )
            except:
                try:
                    await interaction.response.send_message(
                        "❌ Erro ao processar comando.", ephemeral=True
                    )
                except:
                    pass

    def _is_valid_url(self, url: str) -> bool:
        """Validar se a URL é válida"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _embed_to_json(self, embed: discord.Embed) -> str:
        """Converter embed para JSON"""
        try:
            embed_dict = embed.to_dict()
            return json.dumps(embed_dict, ensure_ascii=False, indent=2)
        except Exception:
            return "{}"

    def _json_to_embed(self, data: dict[str, Any]) -> discord.Embed:
        """Converter JSON para embed"""
        embed = discord.Embed()

        if "title" in data:
            embed.title = data["title"]

        if "description" in data:
            embed.description = data["description"]

        if "color" in data:
            embed.color = data["color"]

        if "url" in data:
            embed.url = data["url"]

        if "timestamp" in data:
            embed.timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

        if "author" in data:
            author = data["author"]
            embed.set_author(
                name=author.get("name"), icon_url=author.get("icon_url"), url=author.get("url")
            )

        if "thumbnail" in data:
            embed.set_thumbnail(url=data["thumbnail"]["url"])

        if "image" in data:
            embed.set_image(url=data["image"]["url"])

        if "footer" in data:
            footer = data["footer"]
            embed.set_footer(text=footer.get("text"), icon_url=footer.get("icon_url"))

        if "fields" in data:
            for field in data["fields"]:
                embed.add_field(
                    name=field.get("name", "\u200b"),
                    value=field.get("value", "\u200b"),
                    inline=field.get("inline", False),
                )

        return embed


async def setup(bot):
    await bot.add_cog(EmbedBuilder(bot))
