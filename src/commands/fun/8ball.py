"""
Comando 8Ball - Fun Aprimorado
Bola mágica com respostas contextuais e estatísticas
"""

import os
import random
from datetime import datetime

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands


class EightBallCommand(commands.Cog):
    """Comando da bola mágica com sistema de estatísticas"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = os.path.join("src", "data", "8ball.db")
        self.bot.loop.create_task(self.init_database())

    async def init_database(self):
        """Inicializar banco de dados de estatísticas"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    guild_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id TEXT PRIMARY KEY,
                    total_questions INTEGER DEFAULT 0,
                    positive_answers INTEGER DEFAULT 0,
                    neutral_answers INTEGER DEFAULT 0,
                    negative_answers INTEGER DEFAULT 0,
                    favorite_category TEXT
                )
            """)
            await db.commit()

    async def save_prediction(
        self, user_id: str, guild_id: str, question: str, answer: str, category: str, sentiment: str
    ):
        """Salvar predição no banco de dados"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO predictions (user_id, guild_id, question, answer, category, sentiment)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (user_id, guild_id, question, answer, category, sentiment),
            )

            # Atualizar estatísticas do usuário
            await db.execute(
                f"""
                INSERT INTO user_stats (user_id, total_questions, {sentiment}_answers, favorite_category)
                VALUES (?, 1, 1, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    total_questions = total_questions + 1,
                    {sentiment}_answers = {sentiment}_answers + 1,
                    favorite_category = ?
            """,
                (user_id, category, category),
            )

            await db.commit()

    async def get_user_stats(self, user_id: str):
        """Obter estatísticas do usuário"""
        async with aiosqlite.connect(self.db_path) as db, db.execute(
            "SELECT * FROM user_stats WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "total": row[1],
                    "positive": row[2],
                    "neutral": row[3],
                    "negative": row[4],
                    "favorite": row[5],
                }
        return None
        self.db_path = os.path.join("src", "data", "8ball.db")
        self.bot.loop.create_task(self.init_database())

        # Respostas categorizadas por tipo de pergunta
        self.respostas_contextuais = {
            # Perguntas sobre amor/relacionamento
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
            # Perguntas sobre dinheiro/trabalho
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
            # Perguntas sobre estudos/escola
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
            # Perguntas sobre jogos/diversão
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
                    "🎊 Prepare-se para uma sequência de vitórias!",
                ],
            },
            # Perguntas sobre comida
            "comida": {
                "keywords": [
                    "comer",
                    "comida",
                    "pizza",
                    "hambúrguer",
                    "doce",
                    "chocolate",
                    "fome",
                    "jantar",
                    "almoço",
                ],
                "respostas": [
                    "🍕 A pizza sempre é uma boa ideia!",
                    "🍔 Seus papilas gustativas estão pedindo por isso!",
                    "🍰 A vida é muito curta para não comer doce!",
                    "🥗 Talvez seja hora de optar por algo mais saudável...",
                    "🍜 Uma refeição quente vai aquecer seu coração!",
                    "🍫 O chocolate pode ser a resposta para todos os problemas!",
                    "🥘 Experimente algo novo e surpreenda seu paladar!",
                    "🍓 As frutas da temporada estão no ponto ideal!",
                ],
            },
        }

        # Respostas gerais (usadas quando não há contexto específico)
        self.respostas_gerais = [
            # Positivas épicas
            "🌟 Absolutamente SIM! O universo conspira a seu favor!",
            "⚡ É seu destino! Vá em frente sem medo!",
            "🚀 Prepare-se para decolar rumo ao sucesso!",
            "🎉 As energias cósmicas dizem: PODE COMEMORAR!",
            "💫 As estrelas se alinharam especialmente para este momento!",
            "🔥 Sua intuição está correta! Confie nela!",
            "🌈 O arco-íris da sorte está brilhando sobre você!",
            "👑 Você nasceu para isso! Rei/Rainha da situação!",
            # Neutras misteriosas
            "🔮 As névoas do tempo ainda não se dissiparam...",
            "🌙 A lua crescente revela apenas metade da verdade...",
            "⏳ O tempo é o melhor conselheiro... aguarde!",
            "🎭 Nem tudo é o que parece... investigue mais!",
            "🧩 Faltam algumas peças do quebra-cabeça...",
            "💭 Sua mente subconsciente já sabe a resposta...",
            "🌊 Deixe as ondas do destino te guiarem...",
            "🦋 Como uma borboleta, aguarde a transformação...",
            # Negativas criativas
            "🌧️ Até a tempestade mais forte passa... mas não agora!",
            "❄️ O inverno cósmico diz: melhor esperar a primavera!",
            "🚫 O universo está te protegendo desta decisão!",
            "⚠️ Cuidado! Os sinais alertam para mudança de rota!",
            "🔄 Talvez seja hora de reavaliar seus planos...",
            "🛑 PARE! Reconsidere antes de prosseguir!",
            "🌑 A lua nova pede paciência e reflexão...",
            "🧊 Águas congeladas... aguarde o degelo!",
        ]

    @app_commands.command(name="8ball", description="Faça uma pergunta para a bola mágica")
    @app_commands.describe(
        pergunta="Sua pergunta para a bola mágica",
        mostrar_stats="Mostrar suas estatísticas após a resposta",
    )
    async def eight_ball(
        self, interaction: discord.Interaction, pergunta: str, mostrar_stats: bool = False
    ):
        """Consultar a bola mágica"""

        await interaction.response.defer()

        pergunta_lower = pergunta.lower()

        # Detectar contexto da pergunta
        respostas_escolhidas = self.respostas_gerais
        emoji = "🎱"
        contexto = "Geral"

        for categoria, dados in self.respostas_contextuais.items():
            if any(keyword in pergunta_lower for keyword in dados["keywords"]):
                respostas_escolhidas = dados["respostas"]
                contexto = categoria.capitalize()

                # Emojis específicos por categoria
                emojis_categoria = {
                    "amor": "💕",
                    "dinheiro": "💰",
                    "estudos": "📚",
                    "jogos": "🎮",
                    "comida": "🍕",
                }

                emoji = emojis_categoria.get(categoria, "🎱")
                break

        # Adicionar aleatoriedade baseada no horário
        agora = datetime.now()
        seed = agora.hour + agora.minute + len(pergunta)
        indice_resposta = (seed * 7) % len(respostas_escolhidas)

        resposta = respostas_escolhidas[indice_resposta]

        # Determinar cor baseada no sentimento da resposta
        resposta_lower = resposta.lower()

        if any(palavra in resposta_lower for palavra in ["sim", "sucesso", "favor"]) or any(
            e in resposta for e in ["🌟", "⚡", "🚀"]
        ):
            color = 0x00FF00  # Verde para positivo
        elif any(palavra in resposta_lower for palavra in ["não", "cuidado"]) or any(
            e in resposta for e in ["🚫", "⚠️", "🛑"]
        ):
            color = 0xFF0000  # Vermelho para negativo
        else:
            color = 0xFFD700  # Dourado para neutro/misterioso

        # Adicionar mensagens especiais para certas horas
        hora = agora.hour
        if 0 <= hora <= 5:
            hora_especial = "\n🌙 *As energias noturnas intensificam a magia da resposta*"
        elif 6 <= hora <= 11:
            hora_especial = "\n☀️ *A aurora traz clareza à sua consulta*"
        elif 12 <= hora <= 17:
            hora_especial = "\n🌞 *O sol do meio-dia ilumina seu caminho*"
        else:  # 18-23
            hora_especial = "\n🌅 *O entardecer revela sabedorias ocultas*"

        embed = discord.Embed(
            title=f"{emoji} Bola Mágica Cósmica {emoji}",
            color=color,
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(name="❓ Sua Consulta", value=f'*"{pergunta}"*', inline=False)
        embed.add_field(
            name="🔮 Revelação Mística", value=f"**{resposta}**{hora_especial}", inline=False
        )
        embed.add_field(name="📊 Categoria Detectada", value=contexto, inline=True)
        embed.add_field(
            name="⭐ Nível de Confiança", value=f"{random.randint(70, 99)}%", inline=True
        )

        embed.set_footer(
            text=f"Consulta realizada por {interaction.user} • Energias cósmicas em sintonia",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Configurar o cog"""
    await bot.add_cog(EightBallCommand(bot))
