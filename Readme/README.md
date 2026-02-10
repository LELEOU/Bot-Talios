# 🤖 Bot Discord Modular - Python Version

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3+-blue.svg)](https://discordpy.readthedocs.io/)
[![Status](https://img.shields.io/badge/Status-🎉%20100%25%20OPERACIONAL-brightgreen.svg)]()

## 🎯 **Sistema Completo Convertido**

**✅ CONVERSÃO 100% FINALIZADA!** Sistema enterprise completo convertido de JavaScript para Python, mantendo toda funcionalidade original com melhorias significativas.

## 🚀 Características

### ✨ Funcionalidades Principais
- **Sistema de Containers V2**: Templates profissionais inspirados em bots como Rio
- **6 Templates Profissionais**: Desde básico até enterprise
- **Interface Interativa**: Modals, botões e select menus
- **Session Management**: Gerenciamento automático de sessões
- **Validação Robusta**: Sistema completo de validação
- **Debug Avançado**: Logging detalhado para troubleshooting

### 🎯 Templates Disponíveis
1. **🌟 Embed Profissional** (`rio_embed_style`)
   - Layout inspirado no Rio Bot
   - Fields organizados e thumbnail
   - Design enterprise

2. **📊 Dashboard Interativo** (`dashboard_style`)
   - Estatísticas em tempo real
   - Dados formatados em YAML
   - Template Premium

3. **🎉 Boas-vindas Premium** (`welcome_premium`)
   - Sistema de boas-vindas profissional
   - Variáveis dinâmicas (`{user}`, `{memberCount}`)
   - Banner personalizado

4. **📢 Anúncio Profissional** (`announcement_pro`)
   - Comunicações oficiais
   - Layout chamativo
   - Seções organizadas

5. **📦 Container Básico** (`simple_container`)
   - Template simples e limpo
   - Ideal para iniciantes
   - Customizável

6. **🔘 Container Interativo** (`container_with_buttons`)
   - Botões integrados
   - Ações interativas
   - Interface moderna

## 🛠️ Instalação

### Pré-requisitos
```bash
Python 3.8+
pip (gerenciador de pacotes Python)
```

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar Token
Crie um arquivo `.env`:
```env
DISCORD_TOKEN=seu_token_aqui
```

### 3. Executar o Bot
```bash
python main.py
```

## 📋 Comandos Disponíveis

### `/container-builder`
Sistema principal de criação de containers:
- **Seleção de Template**: Choose entre 6 templates profissionais
- **Configuração Interativa**: Modals para texto, cor e imagens
- **Preview em Tempo Real**: Visualize antes de publicar
- **Envio Direto**: Publique no canal atual

## 🏗️ Estrutura do Projeto

```
python-version/
├── main.py                     # Arquivo principal do bot
├── requirements.txt            # Dependências Python
├── .env.example               # Exemplo de configuração
├── README.md                  # Documentação
└── src/
    ├── utils/
    │   └── container_templates.py    # Sistema de templates
    ├── commands/
    │   └── container_builder.py      # Comando principal
    └── events/
        └── container_handler.py      # Handler de eventos
```

## 🔧 Desenvolvimento

### Arquitetura
- **Modular**: Cada funcionalidade em arquivo separado
- **Orientada a Objetos**: Classes bem estruturadas
- **Assíncrona**: Usando asyncio para performance
- **Type Hints**: Tipagem completa para melhor IDE support

### Classes Principais
- `ContainerTemplateManager`: Gerencia templates e validações
- `ContainerBuilderCog`: Comando principal slash
- `ContainerHandler`: Handler de interações e eventos
- `ModularBot`: Classe principal do bot

### Sistema de Debug
```python
# Logging automático habilitado
print("🔧 Debug - Evento executado")
print("✅ Debug - Operação concluída")
print("❌ Debug - Erro detectado")
```

## 🎨 Personalização

### Adicionar Novo Template
1. Edite `src/utils/container_templates.py`
2. Adicione ao `CONTAINER_TEMPLATES`
3. Configure padrões em `get_default_configurations()`
4. Teste com `/container-builder`

### Customizar Cores
```python
class Colors:
    CUSTOM_COLOR = 0xFF5733  # Laranja personalizado
    BRAND_COLOR = 0x7289DA   # Cor da marca
```

## 🚀 Deploy

### Docker (Recomendado)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### Railway/Heroku
```bash
# Procfile
worker: python main.py
```

## 🐛 Troubleshooting

### Problemas Comuns
1. **ImportError discord**: `pip install discord.py`
2. **Token inválido**: Verifique o `.env`
3. **Permissões**: Bot precisa de `Manage Messages`
4. **Slash commands**: Use `!sync` se necessário

### Debug Avançado
Habilite logs detalhados:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Add nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📜 Licença

Este projeto está sob a licença MIT. Veja `LICENSE` para mais detalhes.

## 💡 Inspiração

Sistema inspirado em bots profissionais como:
- **Rio Bot**: Interface e design
- **Carl-bot**: Funcionalidades modulares
- **Dyno**: Sistema de templates

## 📞 Suporte

- **GitHub Issues**: Para bugs e sugestões
- **Discord**: [Servidor de Suporte](https://discord.gg/exemplo)
- **Email**: suporte@exemplo.com

## 🎯 Roadmap

- [ ] Sistema de templates favoritos
- [ ] Importar/exportar configurações
- [ ] Templates com animações
- [ ] API REST para templates
- [ ] Dashboard web
- [ ] Integração com banco de dados
- [ ] Sistema de plugins

---

**🌟 Desenvolvido com 💜 pela comunidade Python Discord**