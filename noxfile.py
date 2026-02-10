"""
🚀 Nox - Task Automation for Discord Bot
========================================

Comandos disponíveis:
    nox -s format      # Formatar código com ruff
    nox -s lint        # Verificar problemas com ruff
    nox -s typecheck   # Verificar tipos com pyright
    nox -s test        # Rodar testes com pytest
    nox -s coverage    # Rodar testes com coverage
    nox -s all         # Rodar todos os checks
    nox -s install     # Instalar dependências de dev

Uso:
    nox                # Roda session padrão (all)
    nox -s format lint # Roda múltiplas sessions
    nox -l             # Lista todas as sessions
"""

import nox

# Configuração global
nox.options.sessions = ["format", "lint", "typecheck", "test"]
nox.options.reuse_existing_virtualenvs = True

# Python versions para testar
PYTHON_VERSIONS = ["3.11"]

# Diretórios para verificar
SRC_DIRS = ["src", "main.py"]
TEST_DIRS = ["tests"]
ALL_DIRS = SRC_DIRS + TEST_DIRS


# ============================================================================
# 🎨 FORMATAÇÃO
# ============================================================================
@nox.session(name="format", python=PYTHON_VERSIONS)
def format_code(session: nox.Session) -> None:
    """Formatar código com ruff.

    Usage:
        nox -s format
    """
    session.install("ruff")

    session.log("🎨 Formatando código com ruff...")
    session.run("ruff", "format", *SRC_DIRS)

    session.log("✅ Código formatado com sucesso!")


# ============================================================================
# 🔍 LINTING
# ============================================================================
@nox.session(name="lint", python=PYTHON_VERSIONS)
def lint_code(session: nox.Session) -> None:
    """Verificar problemas no código com ruff.

    Usage:
        nox -s lint
        nox -s lint -- --fix  # Auto-fix problemas
    """
    session.install("ruff")

    # Pegar argumentos extras (ex: --fix)
    args = session.posargs or []

    session.log("🔍 Verificando código com ruff...")
    session.run("ruff", "check", *SRC_DIRS, *args)

    if not args or "--fix" not in args:
        session.log("💡 Dica: use 'nox -s lint -- --fix' para corrigir automaticamente")

    session.log("✅ Lint passou!")


# ============================================================================
# 🔬 TYPE CHECKING
# ============================================================================
@nox.session(name="typecheck", python=PYTHON_VERSIONS)
def type_check(session: nox.Session) -> None:
    """Verificar tipos com pyright.

    Usage:
        nox -s typecheck
    """
    session.install("pyright", "discord.py", "aiosqlite", "python-dotenv")

    session.log("🔬 Verificando tipos com pyright...")
    session.run("pyright", *SRC_DIRS)

    session.log("✅ Type check passou!")


@nox.session(name="mypy", python=PYTHON_VERSIONS)
def mypy_check(session: nox.Session) -> None:
    """Verificar tipos com mypy (alternativo).

    Usage:
        nox -s mypy
    """
    session.install("mypy", "discord.py", "aiosqlite", "python-dotenv")

    session.log("🔬 Verificando tipos com mypy...")
    session.run("mypy", *SRC_DIRS)

    session.log("✅ Mypy passou!")


# ============================================================================
# 🧪 TESTES
# ============================================================================
@nox.session(name="test", python=PYTHON_VERSIONS)
def run_tests(session: nox.Session) -> None:
    """Rodar testes com pytest.

    Usage:
        nox -s test
        nox -s test -- -v            # Verbose
        nox -s test -- -k test_name  # Rodar teste específico
        nox -s test -- --lf          # Last failed
    """
    session.install(
        "pytest",
        "pytest-asyncio",
        "discord.py",
        "aiosqlite",
        "python-dotenv",
    )

    # Pegar argumentos extras
    args = session.posargs or ["-v"]

    session.log("🧪 Rodando testes com pytest...")
    session.run("pytest", *TEST_DIRS, *args)

    session.log("✅ Testes passaram!")


@nox.session(name="test-coverage", python=PYTHON_VERSIONS)
def test_coverage(session: nox.Session) -> None:
    """Rodar testes com coverage.

    Usage:
        nox -s test-coverage
    """
    session.install(
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "coverage[toml]",
        "discord.py",
        "aiosqlite",
        "python-dotenv",
    )

    session.log("🧪 Rodando testes com coverage...")
    session.run(
        "pytest",
        *TEST_DIRS,
        "--cov=src",
        "--cov-report=term-missing:skip-covered",
        "--cov-report=html",
        "--cov-report=xml",
        "-v",
    )

    session.log("✅ Testes com coverage completos!")
    session.log("📊 Veja o relatório em: htmlcov/index.html")


# ============================================================================
# 📊 COVERAGE REPORT
# ============================================================================
@nox.session(name="coverage", python=PYTHON_VERSIONS)
def coverage_report(session: nox.Session) -> None:
    """Gerar relatório de coverage sem rodar testes.

    Usage:
        nox -s coverage
    """
    session.install("coverage[toml]")

    session.log("📊 Gerando relatório de coverage...")
    session.run("coverage", "report")
    session.run("coverage", "html")

    session.log("✅ Relatório gerado em: htmlcov/index.html")


# ============================================================================
# 🔧 INSTALAÇÃO
# ============================================================================
@nox.session(name="install", python=PYTHON_VERSIONS, venv_backend="none")
def install_dev(session: nox.Session) -> None:
    """Instalar dependências de desenvolvimento.

    Usage:
        nox -s install
    """
    session.log("📦 Instalando dependências de desenvolvimento...")
    session.run("pip", "install", "-e", ".[dev]", external=True)

    session.log("✅ Dependências instaladas!")
    session.log("💡 Agora configure pre-commit: pre-commit install")


# ============================================================================
# 🧹 LIMPEZA
# ============================================================================
@nox.session(name="clean", python=False)
def clean_files(session: nox.Session) -> None:
    """Limpar arquivos temporários e cache.

    Usage:
        nox -s clean
    """
    import shutil
    from pathlib import Path

    session.log("🧹 Limpando arquivos temporários...")

    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "htmlcov",
        ".coverage",
        "coverage.xml",
        "*.egg-info",
        "build",
        "dist",
    ]

    for pattern in patterns:
        for path in Path().glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                session.log(f"  🗑️  Removido: {path}")
            elif path.is_file():
                path.unlink()
                session.log(f"  🗑️  Removido: {path}")

    session.log("✅ Limpeza concluída!")


# ============================================================================
# 🚀 ALL - Rodar todos os checks
# ============================================================================
@nox.session(name="all", python=PYTHON_VERSIONS)
def run_all(session: nox.Session) -> None:
    """Rodar todos os checks (format, lint, typecheck, test).

    Usage:
        nox -s all
        nox  # all é a session padrão
    """
    session.log("🚀 Rodando todos os checks...")

    # Format
    session.log("\n" + "=" * 70)
    session.log("1/4 - 🎨 FORMATAÇÃO")
    session.log("=" * 70)
    session.notify("format")

    # Lint
    session.log("\n" + "=" * 70)
    session.log("2/4 - 🔍 LINTING")
    session.log("=" * 70)
    session.notify("lint")

    # Type check
    session.log("\n" + "=" * 70)
    session.log("3/4 - 🔬 TYPE CHECKING")
    session.log("=" * 70)
    session.notify("typecheck")

    # Tests
    session.log("\n" + "=" * 70)
    session.log("4/4 - 🧪 TESTES")
    session.log("=" * 70)
    session.notify("test")

    session.log("\n" + "=" * 70)
    session.log("✅ TODOS OS CHECKS PASSARAM!")
    session.log("=" * 70)


# ============================================================================
# 🏗️ BUILD - Construir pacote
# ============================================================================
@nox.session(name="build", python=PYTHON_VERSIONS)
def build_package(session: nox.Session) -> None:
    """Construir pacote do bot.

    Usage:
        nox -s build
    """
    session.install("build", "wheel")

    session.log("🏗️  Construindo pacote...")
    session.run("python", "-m", "build")

    session.log("✅ Pacote construído em: dist/")


# ============================================================================
# 📝 DOCS - Gerar documentação
# ============================================================================
@nox.session(name="docs", python=PYTHON_VERSIONS)
def build_docs(session: nox.Session) -> None:
    """Gerar documentação com Sphinx.

    Usage:
        nox -s docs
    """
    session.install("sphinx", "sphinx-rtd-theme", "discord.py")

    session.log("📝 Gerando documentação...")
    session.run("sphinx-build", "-b", "html", "docs", "docs/_build/html")

    session.log("✅ Documentação gerada em: docs/_build/html/index.html")


# ============================================================================
# 🔒 SECURITY - Verificar vulnerabilidades
# ============================================================================
@nox.session(name="security", python=PYTHON_VERSIONS)
def security_check(session: nox.Session) -> None:
    """Verificar vulnerabilidades de segurança.

    Usage:
        nox -s security
    """
    session.install("pip-audit")

    session.log("🔒 Verificando vulnerabilidades...")
    session.run("pip-audit")

    session.log("✅ Nenhuma vulnerabilidade encontrada!")


# ============================================================================
# 📋 INFO - Mostrar informações
# ============================================================================
@nox.session(name="info", python=False)
def show_info(session: nox.Session) -> None:
    """Mostrar informações sobre o projeto.

    Usage:
        nox -s info
    """
    session.log("=" * 70)
    session.log("📋 INFORMAÇÕES DO PROJETO")
    session.log("=" * 70)
    session.log("Nome: Discord Bot Modular")
    session.log("Versão: 3.0.0")
    session.log("Python: 3.11+")
    session.log("")
    session.log("🛠️  COMANDOS DISPONÍVEIS:")
    session.log("  nox -s format      # Formatar código")
    session.log("  nox -s lint        # Verificar problemas")
    session.log("  nox -s typecheck   # Verificar tipos")
    session.log("  nox -s test        # Rodar testes")
    session.log("  nox -s all         # Rodar tudo")
    session.log("")
    session.log("📚 MAIS COMANDOS:")
    session.log("  nox -l             # Listar todas as sessions")
    session.log("  nox -s clean       # Limpar cache")
    session.log("  nox -s install     # Instalar deps de dev")
    session.log("=" * 70)
