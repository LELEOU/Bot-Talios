# 🚀 Guia Rápido de Início

## ⚡ Start em 5 Minutos

### 1️⃣ Instalar Dependências
```bash
pip install discord.py aiosqlite python-dotenv
```

### 2️⃣ Executar o Bot
```bash
python main.py
```

### 3️⃣ Configurar Permissões
```
/config
```
Selecione os cargos de admin, moderador e DJ.

### 4️⃣ Testar Comandos
```
/embed          # Criar embed interativo
/ban @User      # Testar moderação
/kick @User     # Testar expulsão
/timeout @User  # Testar castigo
```

---

## 🎯 Comandos Principais

### 👑 Administração
| Comando | Descrição | Permissão |
|---------|-----------|-----------|
| `/config` | Configurar bot | Admin Discord |

### 🛡️ Moderação
| Comando | Descrição | Permissão |
|---------|-----------|-----------|
| `/ban @user` | Banir membro | Mod/Admin |
| `/kick @user` | Expulsar membro | Mod/Admin |
| `/timeout @user` | Castigar temporariamente | Mod/Admin |

### 🎨 Utilitários
| Comando | Descrição | Permissão |
|---------|-----------|-----------|
| `/embed` | Criar embed visual | Todos |

---

## 📊 Recursos Principais

### ✅ Sistema de Permissões
- Cargos customizados por função
- Verificação automática
- Analytics integrado

### ✅ Mensagens Efêmeras
- Privacidade garantida
- Menos poluição no chat
- Experiência profissional

### ✅ Interface Interativa
- Botões e menus
- Modais para entrada
- Preview em tempo real

### ✅ Moderação Avançada
- Sistema de confirmação
- Motivos obrigatórios
- Logs automáticos

---

## 🎨 Exemplo: Criar Embed

```
1. Use: /embed

2. Clique em: ✏️ Título
3. Digite: "Bem-vindo!"

4. Clique em: 📝 Descrição
5. Digite: "Olá ao servidor!"

6. Clique em: 🎨 Cor
7. Digite: "#3498db"

8. Clique em: ➕ Campo
9. Nome: "Regras"
10. Valor: "Leia #regras"

11. Preview atualiza automaticamente!

12. Clique em: ✅ Enviar
```

---

## 🛡️ Exemplo: Banir Usuário

```
1. Use: /ban @Infrator

2. Bot mostra preview:
   ⚠️ Confirmar Banimento
   👤 @Infrator
   📅 Conta criada há...
   
3. Clique: [✅ Confirmar]

4. Modal aparece
5. Digite motivo: "Spam"
6. Clique: [Enviar]

7. ✅ Banimento executado!
   - DM enviado ao usuário
   - Log registrado
   - Confirmação mostrada
```

---

## ⚙️ Configuração Inicial

### Definir Cargos

```
/config
```

**1. Cargos Admin (👑)**
- Acesso total ao bot
- Todos os comandos
- Dashboard completa

**2. Cargos Mod (🛡️)**
- Comandos de moderação
- Ban, kick, timeout
- Logs de moderação

**3. Cargos DJ (🎵)**
- Controle de música
- Fila de músicas
- Ajustes de volume

---

## 🎯 Dicas Importantes

### ✅ Fazer
- Testar em servidor de desenvolvimento primeiro
- Configurar cargos antes de usar
- Usar mensagens efêmeras para privacidade
- Sempre fornecer motivos claros

### ❌ Evitar
- Dar permissões admin sem necessidade
- Esquecer de configurar logs
- Ignorar hierarquia de cargos
- Banir sem motivo documentado

---

## 📚 Documentação Completa

Para detalhes completos, consulte:
- `SISTEMA_PERSONALIZACAO.md` - Guia técnico completo
- `MELHORIAS_IMPLEMENTADAS.md` - Resumo das features
- Código fonte com docstrings

---

## 🐛 Problemas Comuns

### "Sem permissão"
**Solução:** Configure cargos em `/config`

### "Embed não atualiza"
**Solução:** Aguarde alguns segundos ou use `/embed` novamente

### "Comando não funciona"
**Solução:** Verifique logs do bot e permissões do Discord

---

## 🎉 Pronto para Usar!

Seu bot agora tem:
- ✅ Sistema de permissões completo
- ✅ Embeds interativos com preview
- ✅ Moderação profissional
- ✅ Preparação para dashboard
- ✅ Analytics integrado

**Bom uso! 🚀**
