# NUUtri — Bot de Nutrição Inteligente

## Visão Geral

Bot de Telegram em Python que funciona como nutricionista virtual powered by Claude (Anthropic). Conversa com usuários, analisa fotos de refeições, salva perfis/histórico em SQLite e gera planos nutricionais personalizados em PDF com identidade visual própria.

## Stack Técnica

- **Linguagem:** Python 3.10+
- **Bot Framework:** python-telegram-bot 21.6 (async)
- **IA:** Anthropic Claude (`claude-opus-4-5`) via SDK `anthropic`
- **Banco de dados:** SQLite com WAL mode (arquivo `nuutri.db`)
- **PDF:** ReportLab 4.2.5 com fontes customizadas (BricolageGrotesque, Outfit, InstrumentSans)
- **Deploy:** Railway ou Render (background worker)

## Arquitetura

```
bot.py              → Lógica principal: handlers do Telegram, chamadas ao Claude, detecção de JSON de plano
database.py         → Camada de dados SQLite: usuários, histórico, planos, rate limiting, analytics
pdf_generator.py    → Geração de PDF com identidade NUUtri: banner, macro cards, donut chart, meal blocks
```

O fluxo principal é: usuário envia mensagem → bot.py processa → chama Claude com histórico + perfil → se resposta contém JSON com `GERAR_PDF: true`, gera PDF e envia; senão, responde texto.

## Estrutura do Banco de Dados

Três tabelas em SQLite:
- `users` — perfil do usuário (nome, peso, altura, idade, sexo, objetivo, nível de atividade)
- `messages` — histórico de conversa (máximo 30 mensagens por usuário, FIFO)
- `plans` — planos nutricionais gerados (JSON completo + timestamp)

## Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `TELEGRAM_TOKEN` | Sim | Token do BotFather |
| `ANTHROPIC_API_KEY` | Sim | Chave da API Anthropic |
| `RATE_LIMIT_PER_HOUR` | Não (default: 40) | Limite de mensagens por usuário/hora |
| `DB_PATH` | Não (default: `nuutri.db`) | Caminho do arquivo SQLite |

## Comandos do Bot

- `/start` — Boas-vindas (reconhece usuários recorrentes)
- `/plano` — Gera plano nutricional em PDF
- `/perfil` — Exibe dados salvos do usuário
- `/reset` — Apaga histórico de conversa (mantém perfil)
- `/stats` — Analytics de uso (comando oculto)

## Identidade Visual

Paleta laranja e carvão:
- Laranja principal: `#FF6B1A` — acentos, CTAs
- Laranja escuro: `#C94E00` — labels, rodapé
- Carvão: `#1C1C1C` — headers, cards de destaque
- Laranja suave: `#FFF0E8` — fundos de cards

Fontes TTF (devem estar na mesma pasta que `pdf_generator.py`):
- `BricolageGrotesque` — títulos e marca
- `Outfit` — corpo de texto
- `InstrumentSans` — labels e metadados

## Convenções de Código

- Código e comentários em português do Brasil
- Funções async para todos os handlers do Telegram
- Funções privadas prefixadas com `_` (ex: `_build_system_with_profile`, `_process_text`)
- Logging via módulo `logging` padrão do Python
- Context manager `_conn()` para conexões SQLite (auto-commit/rollback)
- Sem frameworks web — bot roda em polling mode

## Padrões Importantes

- **Detecção de plano:** A resposta do Claude é verificada por `stripped.startswith("{") and '"GERAR_PDF"' in stripped`. Se for JSON válido com `GERAR_PDF: true`, gera PDF ao invés de enviar texto.
- **Perfil automático:** Quando um plano é gerado, os dados do usuário são extraídos do JSON e salvos no perfil via `update_profile()`.
- **Histórico:** Imagens são descartadas do histórico persistido (apenas texto é salvo). Máximo de 30 mensagens por usuário.
- **Rate limiting:** Baseado em contagem de mensagens na última hora via SQLite.
- **Fallback de fontes:** O PDF generator funciona com fontes nativas (Helvetica) caso as TTF não estejam disponíveis.

## Como Rodar Localmente

```bash
export TELEGRAM_TOKEN="seu_token"
export ANTHROPIC_API_KEY="sua_chave"
pip install -r requirements.txt
python bot.py
```

## Pontos de Atenção

- O SQLite é efêmero em plataformas como Railway — para produção com persistência, usar volume persistente ou migrar para PostgreSQL.
- O modelo `claude-opus-4-5` é o mais caro. Para reduzir custos, substituir por `claude-haiku-4-5-20251001` em `bot.py`.
- As fontes TTF não estão no repositório — precisam ser adicionadas manualmente ao ambiente de deploy.
- O system prompt em `bot.py` contém toda a lógica de comportamento do bot, incluindo formato de resposta JSON para geração de PDF.
