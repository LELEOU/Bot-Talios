"""
Sistema de Diversão - Comandos Fun
Bola mágica 8ball, dados, moeda, memes e mais
"""

import asyncio
import random
from datetime import datetime

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


class FunSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="8ball", description="🎱 Consulte a bola mágica")
    @app_commands.describe(pergunta="Sua pergunta para a bola mágica")
    async def eight_ball(self, interaction: discord.Interaction, pergunta: str):
        try:
            await interaction.response.defer()

            # Análise contextual da pergunta
            pergunta_lower = pergunta.lower()

            # Respostas categorizadas
            respostas_contextuais = {
                "amor": {
                    "keywords": [
                        "amor",
                        "namor",
                        "crush",
                        "gostar",
                        "paixão",
                        "beijar",
                        "casar",
                        "relacionamento",
                        "romance",
                    ],
                    "respostas": [
                        "💖 O amor está no ar! Siga seu coração!",
                        "💕 Os astros estão alinhados para o romance!",
                        "💔 Talvez seja hora de focar em você mesmo primeiro...",
                        "😍 Essa pessoa especial pode estar mais perto do que imagina!",
                        "💘 Cupido pode estar preparando sua flecha!",
                        "🌹 As melhores coisas acontecem quando menos esperamos!",
                        "💑 O tempo dirá se é destino ou apenas coincidência...",
                        "💗 Seu coração já sabe a resposta, só precisa escutar!",
                    ],
                },
                "dinheiro": {
                    "keywords": [
                        "dinheiro",
                        "grana",
                        "rico",
                        "trabalho",
                        "emprego",
                        "salário",
                        "promoção",
                        "negócio",
                        "investimento",
                    ],
                    "respostas": [
                        "💰 A fortuna favorece os corajosos!",
                        "📈 Seus investimentos podem render frutos em breve!",
                        "💸 Cuidado com gastos desnecessários nesta fase...",
                        "🏆 Seu esforço será reconhecido e recompensado!",
                        "💼 Novas oportunidades profissionais estão chegando!",
                        "📊 É hora de planejar suas finanças com mais cuidado!",
                        "🎯 Foque no que realmente importa e o sucesso virá!",
                        "💎 Nem tudo que reluz é ouro, mas sua dedicação sim!",
                    ],
                },
                "estudos": {
                    "keywords": [
                        "prova",
                        "teste",
                        "estudar",
                        "escola",
                        "faculdade",
                        "universidade",
                        "nota",
                        "passar",
                        "aprovar",
                    ],
                    "respostas": [
                        "📚 O conhecimento é poder! Continue estudando!",
                        "🎓 Sua dedicação será recompensada nos resultados!",
                        "📝 A preparação é a chave para o sucesso!",
                        "🏅 Você tem potencial para ir além do que imagina!",
                        "📖 Cada página estudada é um passo rumo ao seu objetivo!",
                        "🧠 Sua mente está absorvendo conhecimento como uma esponja!",
                        "⭐ As estrelas estão alinhadas para seu crescimento acadêmico!",
                        "🎯 Mantenha o foco e os resultados aparecerão!",
                    ],
                },
                "jogos": {
                    "keywords": [
                        "jogo",
                        "game",
                        "jogar",
                        "ganhar",
                        "perder",
                        "sorte",
                        "azar",
                        "diversão",
                        "play",
                    ],
                    "respostas": [
                        "🎮 GG! Sua próxima partida será épica!",
                        "🏆 Victory Royale está no seu futuro próximo!",
                        "🎲 Os dados da sorte estão do seu lado!",
                        "🃏 Suas cartas serão favoráveis nesta rodada!",
                        "⚡ Power-up ativado! Você está unstoppable!",
                        "🎯 Headshot garantido na próxima tentativa!",
                        "🏅 Você nasceu para ser um campeão!",
                        "🔥 Streak de vitórias incoming!",
                    ],
                },
            }

            # Respostas gerais da bola mágica
            respostas_gerais = [
                "✅ **Sim, definitivamente!**",
                "👍 **É certo que sim!**",
                "🎯 **Sem dúvida!**",
                "✨ **Sim, com certeza!**",
                "💯 **Pode apostar que sim!**",
                "🤔 **Provavelmente sim...**",
                "🌟 **As chances são boas!**",
                "📊 **Os sinais apontam para sim!**",
                "⚖️ **Talvez...**",
                "🔄 **Pergunte novamente mais tarde.**",
                "🤷 **Não consigo prever agora.**",
                "💭 **Melhor não te contar agora...**",
                "🚫 **Minha resposta é não.**",
                "❌ **Minhas fontes dizem que não.**",
                "🙅 **Não conte com isso.**",
                "⛔ **Muito duvidoso.**",
                "❗ **Não parece provável.**",
                "🔒 **As perspectivas não são boas.**",
            ]

            # Determinar categoria da pergunta
            categoria_encontrada = None
            for categoria, data in respostas_contextuais.items():
                if any(keyword in pergunta_lower for keyword in data["keywords"]):
                    categoria_encontrada = categoria
                    break

            # Selecionar resposta
            if categoria_encontrada:
                resposta = random.choice(respostas_contextuais[categoria_encontrada]["respostas"])
                cor = 0xFF69B4  # Rosa para respostas contextuais
            else:
                resposta = random.choice(respostas_gerais)
                cor = 0x8A2BE2  # Roxo para respostas gerais

            # Criar embed
            embed = discord.Embed(title="🎱 **BOLA MÁGICA**", color=cor, timestamp=datetime.now())

            embed.add_field(name="❓ Sua Pergunta", value=f"*{pergunta}*", inline=False)

            embed.add_field(name="🔮 Resposta da Bola Mágica", value=resposta, inline=False)

            if categoria_encontrada:
                embed.add_field(
                    name="🎯 Categoria",
                    value=f"Pergunta sobre **{categoria_encontrada}**",
                    inline=True,
                )

            embed.set_footer(
                text=f"Consultado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando 8ball: {e}")
            try:
                await interaction.followup.send(
                    "❌ Erro ao consultar a bola mágica.", ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="dice", description="🎲 Rolar dados")
    @app_commands.describe(
        quantidade="Quantidade de dados (1-10)",
        lados="Número de lados do dado (4, 6, 8, 10, 12, 20, 100)",
    )
    async def dice(
        self,
        interaction: discord.Interaction,
        quantidade: int | None = 1,
        lados: int | None = 6,
    ):
        try:
            # Validações
            if quantidade < 1 or quantidade > 10:
                await interaction.response.send_message(
                    "❌ **Quantidade Inválida**\nVocê pode rolar de 1 a 10 dados por vez.",
                    ephemeral=True,
                )
                return

            lados_validos = [4, 6, 8, 10, 12, 20, 100]
            if lados not in lados_validos:
                await interaction.response.send_message(
                    f"❌ **Lados Inválidos**\nLados válidos: {', '.join(map(str, lados_validos))}",
                    ephemeral=True,
                )
                return

            # Rolar dados
            resultados = [random.randint(1, lados) for _ in range(quantidade)]
            total = sum(resultados)

            # Emojis por tipo de dado
            emojis_dados = {4: "🔸", 6: "🎲", 8: "🔷", 10: "🔟", 12: "🌟", 20: "⭐", 100: "💯"}

            embed = discord.Embed(
                title=f"{emojis_dados.get(lados, '🎲')} **ROLAGEM DE DADOS**",
                color=0x00FF00 if total > (lados * quantidade * 0.7) else 0xFF6600,
                timestamp=datetime.now(),
            )

            embed.add_field(
                name="🎯 Configuração", value=f"**Dados:** {quantidade}d{lados}", inline=True
            )

            embed.add_field(name="📊 Total", value=f"**{total}**", inline=True)

            # Mostrar resultados individuais
            if quantidade > 1:
                resultados_text = " + ".join([f"**{r}**" for r in resultados])
                embed.add_field(name="🎲 Resultados", value=resultados_text, inline=False)

            # Análise do resultado
            max_possivel = lados * quantidade
            porcentagem = (total / max_possivel) * 100

            if porcentagem >= 90:
                analise = "🔥 **ROLAGEM ÉPICA!** Quase perfeita!"
            elif porcentagem >= 75:
                analise = "🌟 **Excelente rolagem!** Muito boa sorte!"
            elif porcentagem >= 60:
                analise = "👍 **Boa rolagem!** Acima da média!"
            elif porcentagem >= 40:
                analise = "😐 **Rolagem média.** Pode melhorar!"
            elif porcentagem >= 25:
                analise = "😕 **Rolagem baixa...** Tente novamente!"
            else:
                analise = "💀 **Rolagem crítica!** Que azar..."

            embed.add_field(
                name="📈 Análise", value=f"{analise}\n({porcentagem:.1f}% do máximo)", inline=False
            )

            embed.set_footer(
                text=f"Rolado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"❌ Erro no comando dice: {e}")
            try:
                await interaction.response.send_message("❌ Erro ao rolar dados.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="coinflip", description="🪙 Cara ou coroa")
    async def coinflip(self, interaction: discord.Interaction):
        try:
            # Simular "rolagem" da moeda com delay
            embed_inicial = discord.Embed(
                title="🪙 **GIRANDO A MOEDA...**",
                description="🌪️ *A moeda está girando no ar...*",
                color=0xFFD700,
                timestamp=datetime.now(),
            )

            await interaction.response.send_message(embed=embed_inicial)
            await asyncio.sleep(2)  # Suspense!

            # Resultado
            resultado = random.choice(["cara", "coroa"])

            if resultado == "cara":
                emoji = "👑"
                cor = 0xFFD700
                resultado_texto = "**CARA**"
                descricao = "A moeda caiu com a face para cima!"
            else:
                emoji = "🪙"
                cor = 0xC0C0C0
                resultado_texto = "**COROA**"
                descricao = "A moeda caiu com o verso para cima!"

            embed_final = discord.Embed(
                title=f"{emoji} **RESULTADO DA MOEDA**",
                description=descricao,
                color=cor,
                timestamp=datetime.now(),
            )

            embed_final.add_field(name="🎯 Resultado", value=resultado_texto, inline=True)

            # Estatísticas divertidas
            frases = [
                "O destino foi decidido!",
                "A sorte escolheu seu caminho!",
                "As leis da física falaram!",
                "O acaso determinou o resultado!",
                "A moeda revelou seu veredicto!",
            ]

            embed_final.add_field(name="✨ Veredicto", value=random.choice(frases), inline=True)

            embed_final.set_footer(
                text=f"Lançado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.edit_original_response(embed=embed_final)

        except Exception as e:
            print(f"❌ Erro no comando coinflip: {e}")
            try:
                await interaction.response.send_message("❌ Erro ao lançar moeda.", ephemeral=True)
            except:
                pass

    @app_commands.command(name="meme", description="😂 Buscar um meme aleatório")
    @app_commands.describe(categoria="Categoria do meme (opcional)")
    async def meme(self, interaction: discord.Interaction, categoria: str | None = None):
        try:
            await interaction.response.defer()

            # APIs de memes gratuitas
            apis_meme = [
                "https://meme-api.herokuapp.com/gimme",
                "https://some-random-api.ml/meme",
                "https://api.imgflip.com/get_memes",
            ]

            async with aiohttp.ClientSession() as session:
                for api_url in apis_meme:
                    try:
                        async with session.get(api_url, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()

                                # Parse different API formats
                                meme_url = None
                                meme_title = None

                                if "url" in data:
                                    meme_url = data["url"]
                                    meme_title = data.get("title", "Meme Aleatório")
                                elif "image" in data:
                                    meme_url = data["image"]
                                    meme_title = data.get("caption", "Meme Aleatório")

                                if meme_url:
                                    embed = discord.Embed(
                                        title="😂 **MEME ALEATÓRIO**",
                                        color=0xFF6B6B,
                                        timestamp=datetime.now(),
                                    )

                                    embed.set_image(url=meme_url)

                                    if meme_title:
                                        embed.add_field(
                                            name="📝 Título",
                                            value=meme_title[:200]
                                            + ("..." if len(meme_title) > 200 else ""),
                                            inline=False,
                                        )

                                    embed.add_field(
                                        name="🎲 Info",
                                        value="Meme buscado aleatoriamente da internet!",
                                        inline=True,
                                    )

                                    embed.set_footer(
                                        text=f"Solicitado por {interaction.user.display_name}",
                                        icon_url=interaction.user.display_avatar.url,
                                    )

                                    await interaction.followup.send(embed=embed)
                                    return

                    except Exception as e:
                        print(f"❌ Erro na API {api_url}: {e}")
                        continue

            # Fallback com memes hardcoded
            memes_fallback = [
                "https://i.imgur.com/Q3cUg29.gif",
                "https://i.imgur.com/2WfBwpA.gif",
                "https://i.imgur.com/5L40mmD.gif",
            ]

            embed_fallback = discord.Embed(
                title="😅 **MEME DE BACKUP**",
                description="Não consegui buscar um meme novo, mas aqui está um clássico!",
                color=0xFF9500,
                timestamp=datetime.now(),
            )

            embed_fallback.set_image(url=random.choice(memes_fallback))

            embed_fallback.set_footer(
                text=f"Solicitado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

            await interaction.followup.send(embed=embed_fallback)

        except Exception as e:
            print(f"❌ Erro no comando meme: {e}")
            try:
                await interaction.followup.send("❌ Erro ao buscar meme.", ephemeral=True)
            except:
                pass


async def setup(bot):
    await bot.add_cog(FunSystem(bot))
