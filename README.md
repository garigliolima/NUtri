# NUUtri — Bot de Nutrição Inteligente para Telegram

> **Nutrição inteligente · Resultados reais**

Bot de nutrição e fitness da **NUUtri**, powered by Claude (Anthropic). Responde dúvidas, analisa fotos de refeições e gera planos nutricionais personalizados em PDF com identidade visual da marca — direto no Telegram.

---

## Identidade Visual

A NUUtri usa uma paleta **laranja e carvão** com tipografia premium:

| Token | Valor | Uso |
|-------|-------|-----|
| Laranja principal | `#FF6B1A` | Acentos, CTAs, cabeçalho |
| Laranja escuro | `#C94E00` | Labels, rodapé, hover |
| Carvão | `#1C1C1C` | Card de destaque, header art |
| Laranja suave | `#FFF0E8` | Fundos de cards e refeições |

**Fontes (empacotadas no projeto):**
- `BricolageGrotesque` — títulos e marca
- `Outfit` — corpo de texto
- `InstrumentSans` — labels e metadados

O PDF gerado pelo bot usa arte geométrica abstrata no cabeçalho (arcos de energia cinética sobre fundo carvão), cards de macros com hierarquia visual invertida e blocos de refeição com acento lateral laranja.

---

## Passo a Passo de Deploy

### 1. Criar o bot no Telegram

1. Abra o Telegram e pesquise por **@BotFather**
2. Envie `/newbot`
3. Escolha um **nome** (ex: `NUUtri`) e um **username** terminado em `bot` (ex: `nuutri_bot`)
4. Guarde o **token** enviado pelo BotFather:
   ```
   7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
   ```

### 2. Obter a chave da API Anthropic

1. Acesse [console.anthropic.com](https://console.anthropic.com)
2. Vá em **API Keys** → **Create Key**
3. Copie a chave (começa com `sk-ant-...`)

### 3. Deploy no Railway (recomendado)

1. Suba todos os arquivos do projeto em um repositório no [GitHub](https://github.com)
2. Acesse [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Selecione o repositório
4. Em **Variables**, adicione:
   ```
   TELEGRAM_TOKEN      = seu_token_do_botfather
   ANTHROPIC_API_KEY   = sua_chave_anthropic
   ```
5. Em **Settings**, defina o **Start Command**:
   ```
   python bot.py
   ```
6. Clique em **Deploy** ✅

### Opção B — Deploy no Render

1. Acesse [render.com](https://render.com) → **New** → **Background Worker**
2. Conecte o repositório GitHub
3. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
4. Em **Environment Variables**, adicione `TELEGRAM_TOKEN` e `ANTHROPIC_API_KEY`
5. Clique em **Create Background Worker** ✅

---

## Comandos do Bot

| Comando | Descrição |
|---------|-----------|
| `/start` | Apresenta o bot — reconhece usuários que voltam pelo nome e objetivo |
| `/plano` | Gera o plano nutricional personalizado em PDF |
| `/perfil` | Exibe os dados que o bot já tem sobre o usuário |
| `/reset` | Apaga o histórico de conversa (mantém o perfil) |
| `/stats` | Estatísticas de uso — total de usuários, mensagens e planos gerados *(oculto, só para o dono)* |

Além dos comandos, o bot responde qualquer mensagem de texto e analisa fotos de pratos enviadas diretamente na conversa.

---

## Estrutura do Projeto

```
nuutri-bot/
├── bot.py                          # Lógica principal do Telegram bot
├── database.py                     # Camada SQLite — usuários, histórico, planos, rate limit
├── pdf_generator.py                # Gerador de PDF com identidade NUUtri
├── BricolageGrotesque-Regular.ttf  # Fonte — títulos
├── BricolageGrotesque-Bold.ttf
├── Outfit-Regular.ttf              # Fonte — corpo
├── Outfit-Bold.ttf
├── InstrumentSans-Regular.ttf      # Fonte — labels
├── InstrumentSans-Bold.ttf
├── requirements.txt
├── Procfile
└── README.md
```

O arquivo `nuutri.db` é criado automaticamente na primeira execução no mesmo diretório.

---

## Variáveis de Ambiente

| Variável | Obrigatória | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `TELEGRAM_TOKEN` | ✅ | — | Token gerado pelo BotFather |
| `ANTHROPIC_API_KEY` | ✅ | — | Chave da API Anthropic |
| `RATE_LIMIT_PER_HOUR` | ❌ | `40` | Máximo de mensagens por usuário por hora |
| `DB_PATH` | ❌ | `nuutri.db` | Caminho do arquivo SQLite |

---

## Funcionalidades

**Conversação:**
- Responde dúvidas sobre dieta, macros, suplementação e estratégias de treino
- Histórico de conversa persistido em SQLite (sobrevive a reinicializações)
- Perfil do usuário salvo automaticamente — o bot lembra peso, objetivo e dados entre sessões
- Rate limiting configurável para controle de custos de API

**Análise de imagens:**
- Recebe fotos de pratos e estima calorias, proteínas, carboidratos e gorduras
- Avalia a qualidade nutricional da refeição e sugere melhorias
- Aceita legenda junto com a foto para contextualizar a análise

**Plano nutricional em PDF:**
- Acionado por `/plano` ou mensagem solicitando um plano
- Reutiliza dados do perfil salvo — não pergunta de novo o que já sabe
- Gera PDF com identidade visual NUUtri (arte geométrica, fontes customizadas, cards de macro, blocos de refeição)
- Envia o arquivo `.pdf` diretamente no chat e salva o plano no banco para histórico

**Analytics:**
- `/stats` exibe total de usuários, mensagens trocadas, planos gerados e objetivos mais comuns

---

## Stack Técnica

| Componente | Tecnologia |
|------------|------------|
| Bot Telegram | `python-telegram-bot 21.6` |
| IA | `Anthropic Claude claude-opus-4-5` |
| Banco de dados | `SQLite` (nativo Python — sem dependência extra) |
| Geração de PDF | `ReportLab 4.2.5` |
| Tipografia | BricolageGrotesque · Outfit · InstrumentSans |
| Hospedagem | Railway / Render (background worker) |

---

## Notas

- As fontes TTF precisam estar na **mesma pasta** que o `pdf_generator.py` para serem carregadas corretamente.
- O modelo usado é `claude-opus-4-5`. Para reduzir custos, substitua por `claude-haiku-4-5-20251001` no `bot.py`.
- No Railway, o sistema de arquivos é **efêmero** — o `nuutri.db` pode ser perdido em redeploys. Para produção com persistência garantida, defina `DB_PATH` apontando para um volume persistente ou migre para PostgreSQL.
