# 🎨 Sistema de Personalização Completo v2.0

## 📋 Visão Geral

Este documento descreve o novo sistema modular e personalizável implementado no bot, focado em:
- ✅ Permissões customizadas por cargo
- ✅ Embeds/Containers com preview em tempo real
- ✅ Comandos interativos e efêmeros
- ✅ Integração com dashboard web
- ✅ Sistema de analytics

---

## 🔐 Sistema de Permissões Avançado

### Localização
```
src/utils/permission_system.py
```

### Recursos

#### 1. **Configuração por Cargos**
- **Admin Roles**: Acesso total ao bot
- **Moderator Roles**: Comandos de moderação
- **DJ Roles**: Controle de música
- **Support Roles**: Comandos de suporte

#### 2. **Permissões por Comando**
```python
from utils.permission_system import require_permission

@app_commands.command(name="exemplo")
@require_permission(category="moderation", mod=True)
async def exemplo(self, interaction: discord.Interaction):
    # Apenas moderadores podem usar
    pass
```

#### 3. **Analytics Integrado**
- Rastreamento automático de uso de comandos
- Taxa de sucesso/erro
- Top comandos usados
- Estatísticas para dashboard

### Como Usar

#### Comando `/config`
```
/config
```
Interface interativa para configurar:
- 👑 Cargos de administrador
- 🛡️ Cargos de moderador  
- 🎵 Cargos de DJ
- 📊 Status da dashboard
- ⚙️ Configurações avançadas

#### Decoradores de Permissão

**Requer Moderador:**
```python
@require_permission(category="moderation", mod=True)
```

**Requer Admin:**
```python
@require_permission(category="administration", admin=True)
```

**Categoria Personalizada:**
```python
@require_permission(category="music")
```

---

## 🎨 Embed Builder Interativo

### Localização
```
src/commands/utility/embed_builder_v2.py
```

### Recursos

#### 1. **Preview em Tempo Real**
- Atualização instantânea ao editar
- Interface totalmente visual
- Mensagens efêmeras (só o criador vê)

#### 2. **Editor Completo**
- ✏️ Título (256 chars)
- 📝 Descrição (4000 chars)
- 🎨 Cor (formato HEX)
- 👤 Autor
- 📄 Rodapé
- 🖼️ Imagem grande
- 🔲 Miniatura
- ⏰ Timestamp
- ➕ Campos (até 25)

#### 3. **Importar/Exportar JSON**
- Importação de embeds existentes
- Exportação para backup
- Compartilhamento de templates

### Como Usar

#### Comando `/embed`
```
/embed
```

**Interface Interativa:**
1. Use os botões para editar cada parte
2. Veja o preview atualizar em tempo real
3. Adicione campos personalizados
4. Importe/exporte JSON quando necessário
5. Clique em "✅ Enviar" quando finalizar

**Exemplo de JSON:**
```json
{
  "title": "🎉 Bem-vindo!",
  "description": "Olá ao servidor!",
  "color": 3447003,
  "fields": [
    {
      "name": "📜 Regras",
      "value": "Leia #regras",
      "inline": true
    }
  ],
  "footer": {
    "text": "Equipe de Moderação"
  },
  "timestamp": true
}
```

---

## 🛡️ Comandos de Moderação Avançados

### Localização
```
src/commands/moderation/moderation_advanced.py
```

### Recursos

#### 1. **Sistema de Confirmação**
- Preview da ação antes de executar
- Modal para motivo obrigatório
- Verificações de segurança automáticas

#### 2. **Notificação de Usuários**
- DM automática com motivo
- Opção de desativar notificações
- Embed formatado e profissional

#### 3. **Logs Automáticos**
- Registro em canal de logs
- Informações completas da ação
- Timestamp e responsável

### Comandos Disponíveis

#### `/ban` - Banir Usuário
```
/ban membro:@Usuario deletar_mensagens:7 notificar:True
```

**Parâmetros:**
- `membro`: Usuário a ser banido
- `deletar_mensagens`: Dias de mensagens (0-7)
- `notificar`: Enviar DM ao usuário

**Verificações:**
- ✅ Hierarquia de cargos
- ✅ Permissões do bot
- ✅ Proteção do dono
- ✅ Auto-proteção

#### `/kick` - Expulsar Usuário
```
/kick membro:@Usuario notificar:True
```

**Parâmetros:**
- `membro`: Usuário a ser expulso
- `notificar`: Enviar DM

#### `/timeout` - Castigar Temporariamente
```
/timeout membro:@Usuario duração:30 tempo:minutos notificar:True
```

**Parâmetros:**
- `membro`: Usuário a receber timeout
- `duração`: Valor numérico (1-28)
- `tempo`: minutos/horas/dias
- `notificar`: Enviar DM

**Exemplos:**
- 30 minutos: `/timeout @User 30 minutos`
- 2 horas: `/timeout @User 2 horas`
- 7 dias: `/timeout @User 7 dias`

---

## 📊 Integração com Dashboard

### Analytics Disponíveis

#### 1. **Uso de Comandos**
```python
analytics = await perm_system.get_analytics(guild_id, days=7)
```

**Retorna:**
```python
{
    'top_commands': [
        {'command_name': 'play', 'category': 'music', 'count': 150},
        {'command_name': 'ban', 'category': 'moderation', 'count': 12},
        # ...
    ],
    'success_rate': 98.5,
    'total_commands': 500
}
```

#### 2. **Configurações do Servidor**
```python
config = await perm_system.get_guild_config(guild_id)
```

**Retorna:**
```python
{
    'admin_role_ids': '123456,789012',
    'mod_role_ids': '345678',
    'dj_role_ids': '567890',
    'dashboard_enabled': True,
    'require_roles_for_moderation': True,
    'custom_config': {}  # Configurações adicionais
}
```

### Endpoints Sugeridos para Dashboard

```
GET  /api/guild/{guild_id}/config
POST /api/guild/{guild_id}/config
GET  /api/guild/{guild_id}/analytics
GET  /api/guild/{guild_id}/commands
POST /api/guild/{guild_id}/commands/{command_name}/permissions
```

---

## 🎯 Fluxo de Uso Completo

### Para Administradores

1. **Configuração Inicial**
   ```
   /config
   ```
   - Defina cargos de admin
   - Defina cargos de moderador
   - Configure cargos especiais (DJ, support)

2. **Personalização de Embeds**
   ```
   /embed
   ```
   - Crie anúncios personalizados
   - Configure mensagens de boas-vindas
   - Exporte templates para reuso

3. **Gestão de Permissões**
   - Acesse a dashboard web
   - Configure permissões por comando
   - Monitore analytics de uso

### Para Moderadores

1. **Ações de Moderação**
   ```
   /ban @Usuario
   /kick @Usuario
   /timeout @Usuario 30 minutos
   ```
   - Sistema guiado com confirmação
   - Motivo obrigatório
   - Logs automáticos

2. **Verificar Permissões**
   - Sistema verifica automaticamente
   - Mensagem clara se negado
   - Orientação para resolver

### Para Usuários Comuns

1. **Comandos Liberados**
   - Todos os comandos não restritos
   - Fun commands
   - Comandos de informação

2. **Feedback Claro**
   - Mensagens efêmeras quando apropriado
   - Embeds informativos
   - Erros amigáveis

---

## 🔧 Implementação em Novos Comandos

### Template Básico

```python
"""
Novo Comando com Permissões
"""
import discord
from discord.ext import commands
from discord import app_commands
from utils.permission_system import require_permission

class MeuComando(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="meucomando")
    @require_permission(category="custom", mod=False, admin=False)
    async def meu_comando(self, interaction: discord.Interaction):
        """Descrição do comando"""
        
        # Comando será verificado automaticamente
        # Analytics registrado automaticamente
        
        embed = discord.Embed(
            title="✅ Comando Executado",
            description="Sucesso!",
            color=0x2ecc71
        )
        
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True  # Apenas o usuário vê
        )

async def setup(bot):
    await bot.add_cog(MeuComando(bot))
```

### Comando com Modal Interativo

```python
from discord.ui import Modal, TextInput

class MeuModal(Modal, title="Título do Modal"):
    campo1 = TextInput(
        label="Campo 1",
        placeholder="Digite algo...",
        max_length=100
    )
    
    campo2 = TextInput(
        label="Campo 2",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        valor1 = self.campo1.value
        valor2 = self.campo2.value
        
        # Processar dados
        await interaction.response.send_message(
            f"Recebido: {valor1}, {valor2}",
            ephemeral=True
        )

@app_commands.command(name="comando_modal")
async def comando_com_modal(self, interaction: discord.Interaction):
    await interaction.response.send_modal(MeuModal())
```

---

## 📝 Checklist de Implementação

### ✅ Concluído

- [x] Sistema de permissões por cargo
- [x] Decoradores de permissão
- [x] Analytics de comandos
- [x] Embed builder interativo
- [x] Preview em tempo real
- [x] Importar/exportar JSON
- [x] Comandos de moderação avançados
- [x] Sistema de confirmação
- [x] Notificações de usuários
- [x] Comando `/config`
- [x] Mensagens efêmeras
- [x] Cache de configurações

### 🔄 Próximos Passos Sugeridos

- [ ] Dashboard web (frontend)
- [ ] API REST para dashboard
- [ ] Sistema de templates de embed
- [ ] Galeria de embeds compartilhados
- [ ] Comandos de diversão melhorados (8ball stats, etc)
- [ ] Sistema de música com permissões DJ
- [ ] Help interativo com categorias
- [ ] Sistema de tickets
- [ ] Sistema de leveling
- [ ] Integração com banco de dados global

---

## 🐛 Troubleshooting

### Permissões não funcionando?

1. Verifique se o sistema foi inicializado:
```python
await perm_system.initialize()
```

2. Limpe o cache:
```python
perm_system._cache.clear()
```

3. Verifique o banco de dados:
```
src/data/advanced_permissions.db
```

### Embed builder não responde?

1. Verifique timeout (10 minutos padrão)
2. Apenas o criador pode interagir
3. Use `/embed` novamente se expirar

### Moderação negada?

1. Configure cargos em `/config`
2. Verifique hierarquia de cargos
3. Admins do Discord sempre têm acesso

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs do bot
2. Teste em ambiente de desenvolvimento
3. Consulte a documentação do Discord.py
4. Revise o código dos exemplos

---

## 🎉 Conclusão

O sistema está pronto para:
- ✅ Personalização completa por servidor
- ✅ Permissões granulares
- ✅ Interface moderna e interativa
- ✅ Integração com dashboard
- ✅ Experiência profissional para usuários

**Próximo Passo Recomendado:**
Teste todos os comandos em um servidor de desenvolvimento antes de deployment!
