"""
Comando Meme - Fun
Busca memes aleatórios de subreddits
"""

import random
from typing import Literal

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


class MemeCommand(commands.Cog):
    """Comando de memes"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Lista de subreddits seguros para memes
        self.subreddits = {
            "memes": "Memes gerais",
            "dankmemes": "Memes dank",
            "wholesomememes": "Memes wholesome",
            "funny": "Conteúdo engraçado",
            "programmerhumor": "Humor de programador",
            "animemes": "Memes de anime",
            "memesbrasil": "Memes brasileiros",
        }

        # Fallback memes (caso a API falhe)
        self.fallback_memes = [
            {"title": "Meme do Drake", "url": "https://i.imgflip.com/1ur9b0.jpg", "author": "Bot"},
            {
                "title": "Distracted Boyfriend",
                "url": "https://i.imgflip.com/1ur9b0.jpg",
                "author": "Bot",
            },
            {"title": "This is Fine", "url": "https://i.imgflip.com/1ur9b0.jpg", "author": "Bot"},
        ]

    @app_commands.command(name="meme", description="Envia um meme aleatório")
    @app_commands.describe(subreddit="Subreddit específico para buscar memes")
    async def meme(
        self,
        interaction: discord.Interaction,
        subreddit: Literal[
            "memes", "dankmemes", "wholesomememes", "funny", "programmerhumor", "animemes"
        ] = "memes",
    ):
        """Buscar e enviar um meme"""

        await interaction.response.defer()

        try:
            # Tentar buscar da API do Reddit
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://meme-api.com/gimme/{subreddit}") as response:
                    if response.status == 200:
                        data = await response.json()

                        # Verificar se o meme é apropriado
                        if not data or not data.get("url") or data.get("nsfw", False):
                            raise Exception("Meme não apropriado ou não encontrado")

                        # Criar embed com dados da API
                        embed = discord.Embed(
                            title=data.get("title", "Meme Aleatório")[:256],  # Limite do Discord
                            color=0xFF6B6B,
                            timestamp=discord.utils.utcnow(),
                        )

                        embed.set_image(url=data["url"])

                        # Informações do post
                        ups = data.get("ups", 0)
                        subreddit_name = data.get("subreddit", subreddit)
                        author = data.get("author", "Desconhecido")

                        embed.set_footer(
                            text=f"👍 {ups:,} upvotes • r/{subreddit_name} • Solicitado por {interaction.user}",
                            icon_url=interaction.user.display_avatar.url,
                        )

                        if author and author != "Desconhecido":
                            embed.set_author(name=f"Por u/{author}")

                        # Adicionar link para o post original se disponível
                        if data.get("postLink"):
                            view = discord.ui.View()
                            button = discord.ui.Button(
                                label="Ver no Reddit",
                                url=data["postLink"],
                                style=discord.ButtonStyle.link,
                                emoji="🔗",
                            )
                            view.add_item(button)

                            await interaction.followup.send(embed=embed, view=view)
                        else:
                            await interaction.followup.send(embed=embed)

                        return

                    raise Exception(f"API retornou status {response.status}")

        except Exception as e:
            print(f"Erro ao buscar meme da API: {e}")

            # Usar meme fallback
            meme_data = random.choice(self.fallback_memes)

            embed = discord.Embed(
                title="🎭 Meme Offline",
                description="A API de memes está indisponível. Aqui está um meme clássico!",
                color=0xFFA500,
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(name="🎯 Título", value=meme_data["title"], inline=True)

            embed.add_field(name="👤 Autor", value=meme_data["author"], inline=True)

            embed.add_field(name="📍 Subreddit", value=f"r/{subreddit}", inline=True)

            embed.set_image(url=meme_data["url"])

            embed.set_footer(
                text=f"⚠️ Modo offline • Solicitado por {interaction.user}",
                icon_url=interaction.user.display_avatar.url,
            )

            # Botão para tentar novamente
            view = discord.ui.View(timeout=60)

            retry_button = discord.ui.Button(
                label="Tentar Novamente", style=discord.ButtonStyle.primary, emoji="🔄"
            )

            async def retry_callback(button_interaction):
                await button_interaction.response.defer()
                # Recriar o comando com uma nova tentativa
                await self.meme.callback(self, button_interaction, subreddit)

            retry_button.callback = retry_callback
            view.add_item(retry_button)

            await interaction.followup.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(MemeCommand(bot))
