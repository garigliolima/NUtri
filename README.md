# 🥗 NutriIA — Bot de Nutrição e Fitness para Telegram

Bot inteligente de nutrição e fitness powered by Claude (Anthropic), rodando no Telegram.

---

## 📋 Passo a Passo Completo

### 1. Criar o bot no Telegram (BotFather)

1. Abra o Telegram e pesquise por **@BotFather**
2. Envie `/newbot`
3. Escolha um **nome** para o bot (ex: `NutriIA`)
4. Escolha um **username** (deve terminar em `bot`, ex: `nutria_fitness_bot`)
5. O BotFather vai te enviar um **token** parecido com:
   ```
   7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
   ```
6. **Guarde esse token** — você vai precisar dele.

---

### 2. Obter a chave da API Anthropic

1. Acesse [console.anthropic.com](https://console.anthropic.com)
2. Vá em **API Keys** → **Create Key**
3. Copie a chave (começa com `sk-ant-...`)

---

### 3. Deploy no Railway (gratuito)

#### Opção A — Via GitHub (recomendado)

1. Crie um repositório no [GitHub](https://github.com) e suba os arquivos:
   - `bot.py`
   - `requirements.txt`
   - `Procfile`

2. Acesse [railway.app](https://railway.app) e faça login com GitHub

3. Clique em **New Project** → **Deploy from GitHub repo**

4. Selecione seu repositório

5. Vá em **Variables** e adicione:
   ```
   TELEGRAM_TOKEN = seu_token_do_botfather
   ANTHROPIC_API_KEY = sua_chave_anthropic
   ```

6. Vá em **Settings** → mude o **Start Command** para:
   ```
   python bot.py
   ```

7. Clique em **Deploy** ✅

#### Opção B — Deploy no Render

1. Acesse [render.com](https://render.com) e crie uma conta

2. Clique em **New** → **Background Worker**

3. Conecte seu repositório GitHub

4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`

5. Em **Environment Variables**, adicione:
   ```
   TELEGRAM_TOKEN = seu_token_do_botfather
   ANTHROPIC_API_KEY = sua_chave_anthropic
   ```

6. Clique em **Create Background Worker** ✅

---

## 💬 Comandos do Bot

| Comando | Descrição |
|---------|-----------|
| `/start` | Inicia o bot e apresenta o NutriIA |
| `/reset` | Apaga o histórico e começa nova conversa |

---

## 🗂️ Estrutura dos arquivos

```
nutria-bot/
├── bot.py            # Código principal do bot
├── requirements.txt  # Dependências Python
├── Procfile          # Configuração para Railway
└── README.md         # Este arquivo
```

---

## ⚙️ Variáveis de Ambiente necessárias

| Variável | Descrição |
|----------|-----------|
| `TELEGRAM_TOKEN` | Token do BotFather |
| `ANTHROPIC_API_KEY` | Chave da API Anthropic |

---

## 🧠 O que o NutriIA sabe fazer

- Calcular TDEE e TMB personalizados
- Distribuição de macronutrientes (proteínas, carbs, gorduras)
- Montar cardápios semanais completos
- Estratégias de emagrecimento, hipertrofia e recomposição
- Timing nutricional (pré e pós-treino)
- Orientações sobre suplementação
- Dietas low-carb, jejum intermitente, vegetariana, mediterrânea
- Dicas de hidratação e micronutrientes

---

## 📝 Notas

- O histórico de conversa é mantido **em memória** (reseta se o bot reiniciar)
- Limite de 20 mensagens por usuário no histórico (para controlar custos)
- Para histórico persistente, adicione um banco de dados (Redis, SQLite, etc.)
