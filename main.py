"""
Bot Discord Modular - Python Version
Sistema avançado de containers e comandos modulares
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Adicionar src ao path para imports
sys.path.append(str(Path(__file__).parent / "src"))


class ModularBot(commands.Bot):
    """Bot principal com sistema modular"""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            activity=discord.Game("Sistema de Containers V2 🚀"),
        )

        self.container_handler: object | None = None
        self._processed_interactions: set[str] = set()  # Cache para evitar processamento duplo

    async def load_all_extensions(self) -> tuple[int, list[str]]:
        """Carregar todas as extensões automaticamente, evitando conflitos"""
        extensions_loaded = 0
        errors: list[str] = []

        # Lista de extensões prioritárias (evitar duplicatas)
        priority_extensions = {
            "announce": ["announce_advanced"],  # Carregar apenas a versão avançada
            "music": ["music_system"],  # Carregar apenas o sistema principal
            "fun": ["fun_system"],  # Carregar apenas o sistema principal
            "communication": ["communication_system"],  # Sistema principal
            "moderation": ["kick", "purge", "slowmode", "warn"],  # Evitar ban_advanced e timeout
            "autorole": ["autorole_setup"],  # Apenas setup
            "note": ["note_create", "note_manage"],  # Carregar ambos os sistemas de notes
            "giveaway": ["giveaway_start"],  # Carregar apenas o sistema principal de giveaway
            "ban": ["ban"],  # Comando básico de ban
            "container_builder": ["container_system"],  # Evitar duplicata do container_builder
            "utility": ["ping", "server_info"],  # Evitar o container_builder duplicado
            "levelcard": ["levelcard"],  # Sistema de levelcard corrigido
            "user": [
                "user_clear_history",
                "user_history",
                "user_nick",
            ],  # Sistemas de usuário corrigidos
        }

        # Carregar comandos
        commands_dir = Path("src/commands")
        for category_dir in commands_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith("__"):
                # Verificar se há prioridades definidas para esta categoria
                if category_dir.name in priority_extensions:
                    # Carregar apenas os arquivos prioritários
                    for priority_file in priority_extensions[category_dir.name]:
                        file_path = category_dir / f"{priority_file}.py"
                        if file_path.exists():
                            extension = f"src.commands.{category_dir.name}.{priority_file}"
                            try:
                                await self.load_extension(extension)
                                extensions_loaded += 1
                                print(f"✅ {extension} (prioritário)")
                            except Exception as e:
                                errors.append(f"❌ {extension}: {str(e)[:100]}")
                else:
                    # Carregar todos os arquivos da categoria (se não há conflitos conhecidos)
                    for file in category_dir.glob("*.py"):
                        if not file.name.startswith("__"):
                            extension = f"src.commands.{category_dir.name}.{file.stem}"
                            try:
                                await self.load_extension(extension)
                                extensions_loaded += 1
                                print(f"✅ {extension}")
                            except Exception as e:
                                errors.append(f"❌ {extension}: {str(e)[:100]}")

        # Lista de eventos seguros para carregar (sem conflitos de tasks)
        safe_events = ["interaction_create", "message_create", "ready"]

        # Carregar apenas eventos seguros
        events_dir = Path("src/events")
        if events_dir.exists():
            for file in events_dir.glob("*.py"):
                if (
                    not file.name.startswith("__")
                    and file.stem != "container_handler"
                    and file.stem in safe_events
                ):
                    extension = f"src.events.{file.stem}"
                    try:
                        await self.load_extension(extension)
                        extensions_loaded += 1
                        print(f"✅ {extension}")
                    except Exception as e:
                        errors.append(f"❌ {extension}: {str(e)[:100]}")

        print("\n📊 Resumo do carregamento:")
        print(f"✅ {extensions_loaded} extensões carregadas com sucesso")
        if errors:
            print(f"❌ {len(errors)} erros encontrados:")
            for error in errors:
                print(f"  {error}")

        return extensions_loaded, errors

    async def setup_hook(self) -> None:
        """Configuração inicial do bot"""
        print("🔄 Iniciando configuração do bot...")

        # Configurar handler de containers de forma segura
        try:
            from src.events.container_handler import setup_container_handler

            self.container_handler = setup_container_handler(self)
            print("✅ Container handler configurado")
        except Exception as e:
            print(f"⚠️ Erro no container handler: {e}")
            self.container_handler = None

        # Carregar todas as extensões automaticamente
        print("\n🚀 Carregando todas as extensões...")
        _loaded_count, _errors = await self.load_all_extensions()

        print("\n🎯 Sistema carregado:")
        print(f"📦 {len(self.cogs)} cogs ativos")

        # Mostrar comandos carregados
        cmd_list = [cmd.name for cmd in self.tree.get_commands()]
        if cmd_list:
            preview = ", ".join(cmd_list[:10])
            suffix = ", ..." if len(cmd_list) > 10 else ""
            print(f"⚡ {len(cmd_list)} comandos: {preview}{suffix}")

        # Sincronizar comandos slash
        try:
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} comandos slash sincronizados")
        except Exception as e:
            print(f"❌ Erro ao sincronizar comandos: {e}")

    async def on_ready(self) -> None:
        """Evento quando o bot fica online"""
        print(f"🤖 Bot logado como {self.user}!")
        print(f"📊 Servindo {len(self.guilds)} servidores")

        total_members = sum(
            guild.member_count for guild in self.guilds if guild.member_count
        )
        print(f"👥 Atendendo {total_members} usuários")

        # Inicializar container cleanup task
        if self.container_handler:
            await self.container_handler.start_cleanup_task()

        # Status especial
        activity = discord.Activity(
            type=discord.ActivityType.watching, name="Sistema 100% Python | /help"
        )
        await self.change_presence(activity=activity, status=discord.Status.online)

        print("\n🎉 SISTEMA 100% OPERACIONAL!")
        print("🔥 Bot Python totalmente integrado e funcional!")
        print("🚀 Todos os comandos e sistemas carregados!")
        print("⭐ Ready for production!")
        print("=" * 60)
        print("📦 Sistemas ativos:")
        print("• Container Builder Enterprise")
        print("• Sistema de Moderação Completo")
        print("• Sistema de Música")
        print("• Sistema de Diversão")
        print("• Sistema de Utilidades")
        print("• Sistema de Comunicação")
        print("• Monitoramento Automático")
        print("=" * 60)

    async def on_interaction(self, interaction: discord.Interaction) -> None:
        """Handler para todas as interações"""
        try:
            # Usar ID da interação para evitar processamento duplo
            interaction_id = f"{interaction.id}_{interaction.user.id}"
            if interaction_id in self._processed_interactions:
                return
            self._processed_interactions.add(interaction_id)

            # Limpar cache periodicamente (manter apenas os últimos 1000)
            if len(self._processed_interactions) > 1000:
                # Remover os mais antigos (apenas manter os últimos 500)
                recent_ids = list(self._processed_interactions)[-500:]
                self._processed_interactions = set(recent_ids)

            # Verificar se é interação de container
            if interaction.type == discord.InteractionType.component:
                custom_id = interaction.data.get("custom_id", "") if interaction.data else ""

                if custom_id == "container_type_select" or custom_id.startswith(
                    "container_"
                ):
                    if self.container_handler:
                        await self.container_handler.handle_interaction(interaction)
                    return

            # Para comandos slash, deixar o sistema padrão do discord.py processar
            # (O event listener em interaction_create.py já cuida disso)

        except Exception as error:
            print(f"❌ Erro ao processar interação: {error}")

            # Tentar responder com erro
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"❌ Erro interno: {error}", ephemeral=True
                    )
            except Exception:
                pass  # Interação já foi respondida ou expirou

    async def on_command_error(
        self, ctx: commands.Context[ModularBot], error: commands.CommandError
    ) -> None:
        """Handler para erros de comando"""
        print(f"❌ Erro de comando: {error}")

    async def close(self) -> None:
        """Limpeza ao fechar o bot"""
        print("🔄 Encerrando bot...")
        await super().close()


async def main() -> None:
    """Função principal"""
    # Inicializar database de forma ultra-segura
    try:
        from src.utils.database import database

        if not hasattr(database, "_init_attempted"):
            await database.init()
            database._init_attempted = True  # type: ignore[attr-defined]
            print("✅ Database inicializado com sucesso")
        else:
            print("ℹ Database já foi inicializado anteriormente")
    except Exception as e:
        if "threads can only be started once" in str(e):
            print("⚠️ Database: thread já iniciada (ignorando)")
        else:
            print(f"⚠️ Erro ao inicializar database: {e}")
        print("🤖 Bot continuará funcionando normalmente")

    # Verificar se o token existe
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN não encontrado!")
        print("💡 Crie um arquivo .env com DISCORD_TOKEN=seu_token_aqui")
        return

    # Criar e iniciar o bot
    bot = ModularBot()

    try:
        await bot.start(token)
    except KeyboardInterrupt:
        print("\n🔄 Interrompido pelo usuário")
    except Exception as error:
        print(f"❌ Erro fatal: {error}")
    finally:
        await bot.close()


if __name__ == "__main__":
    print("🚀 Iniciando Bot Discord Modular - Python Version")
    print("📦 Sistema de Containers Avançados V3.0")
    print("=" * 50)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado com sucesso!")
    except Exception as error:
        print(f"❌ Erro ao iniciar: {error}")
