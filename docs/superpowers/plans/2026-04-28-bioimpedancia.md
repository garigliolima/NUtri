# Bioimpedância Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que clientes enviem laudos de bioimpedância (PDF ou texto) via Telegram para que o bot extraia todos os dados, salve no perfil e os use na geração do plano nutricional.

**Architecture:** O PDF é convertido para JPEG em memória com PyMuPDF e enviado ao Claude Vision para extração. Texto manual é detectado por keywords e interpretado pelo Claude. Os dados são persistidos como JSON numa nova coluna `bioimpedancia` na tabela `users`. O system prompt é enriquecido com os dados de composição corporal ao gerar planos.

**Tech Stack:** Python 3.10+, python-telegram-bot 21.6, PyMuPDF (fitz), anthropic SDK, SQLite, pytest

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---------|------|-----------------|
| `requirements.txt` | Modificar | Adicionar PyMuPDF |
| `database.py` | Modificar | Coluna + funções save/get bioimpedância |
| `bot.py` | Modificar | Detecção, extração, handlers, system prompt |
| `tests/test_database.py` | Criar | Testes das funções de banco |
| `tests/test_bot_utils.py` | Criar | Testes das funções utilitárias do bot |

---

## Task 1: Adicionar PyMuPDF ao requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Adicionar dependência**

Abrir `requirements.txt` e adicionar ao final:
```
PyMuPDF>=1.24.0
```

- [ ] **Step 2: Instalar localmente para validar**

```bash
pip install PyMuPDF>=1.24.0
python -c "import fitz; print(fitz.__version__)"
```
Expected: versão >= 1.24.0 impressa sem erros.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add PyMuPDF for PDF-to-image conversion"
```

---

## Task 2: Adicionar coluna e funções de bioimpedância em database.py

**Files:**
- Modify: `database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Criar diretório de testes e arquivo de teste**

```bash
mkdir -p tests
touch tests/__init__.py
```

Criar `tests/test_database.py`:

```python
import json
import os
import pytest

os.environ.setdefault("DB_PATH", ":memory:")

from database import init_db, upsert_user, save_bioimpedancia, get_bioimpedancia


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    import database
    monkeypatch.setattr(database, "DB_PATH", db_file)
    init_db()
    upsert_user(123, first_name="Teste", username="teste")
    yield


def test_save_and_get_bioimpedancia():
    data = {
        "gordura_pct": 22.5,
        "massa_magra_kg": 58.3,
        "massa_gorda_kg": 17.2,
        "agua_corporal_pct": 55.1,
        "gordura_visceral": 8,
        "tmb_medida": 1820,
        "idade_metabolica": 34,
        "outros": {"massa_ossea_kg": 2.8},
    }
    save_bioimpedancia(123, data)
    result = get_bioimpedancia(123)
    assert result["gordura_pct"] == 22.5
    assert result["massa_magra_kg"] == 58.3
    assert result["outros"]["massa_ossea_kg"] == 2.8


def test_get_bioimpedancia_sem_dados():
    result = get_bioimpedancia(123)
    assert result == {}


def test_save_bioimpedancia_sobrescreve():
    save_bioimpedancia(123, {"gordura_pct": 20.0, "outros": {}})
    save_bioimpedancia(123, {"gordura_pct": 25.0, "outros": {}})
    result = get_bioimpedancia(123)
    assert result["gordura_pct"] == 25.0
```

- [ ] **Step 2: Rodar testes para confirmar falha**

```bash
cd /Users/Lima/Documents/Claude/Projects/NUUtri
python -m pytest tests/test_database.py -v
```
Expected: ERRORS — `save_bioimpedancia` e `get_bioimpedancia` não existem ainda.

- [ ] **Step 3: Adicionar migration da coluna em `init_db`**

Em `database.py`, dentro de `init_db()`, após o `executescript`, adicionar:

```python
def init_db():
    """Cria as tabelas se ainda não existirem."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id     INTEGER PRIMARY KEY,
                first_name      TEXT,
                username        TEXT,
                nome            TEXT,
                peso            TEXT,
                altura          TEXT,
                idade           TEXT,
                sexo            TEXT,
                objetivo        TEXT,
                nivel_atividade TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL REFERENCES users(telegram_id),
                role        TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content     TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS plans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL REFERENCES users(telegram_id),
                plan_json   TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_messages_user
                ON messages(telegram_id, created_at);
        """)
        # Migration: adiciona coluna bioimpedancia se não existir
        try:
            con.execute("ALTER TABLE users ADD COLUMN bioimpedancia TEXT")
        except Exception:
            pass  # coluna já existe
    logger.info(f"Banco de dados inicializado: {DB_PATH}")
```

- [ ] **Step 4: Adicionar funções `save_bioimpedancia` e `get_bioimpedancia`**

Ao final da seção `# ── Usuários ───` em `database.py`, após `get_profile`, adicionar:

```python
def save_bioimpedancia(telegram_id: int, data: dict) -> None:
    """Persiste dados de bioimpedância no perfil do usuário."""
    with _conn() as con:
        con.execute(
            "UPDATE users SET bioimpedancia = ?, updated_at = datetime('now') WHERE telegram_id = ?",
            (json.dumps(data, ensure_ascii=False), telegram_id),
        )


def get_bioimpedancia(telegram_id: int) -> dict:
    """Retorna dados de bioimpedância salvos ou {} se ausente."""
    with _conn() as con:
        row = con.execute(
            "SELECT bioimpedancia FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
    if row and row["bioimpedancia"]:
        return json.loads(row["bioimpedancia"])
    return {}
```

- [ ] **Step 5: Rodar testes para confirmar que passam**

```bash
python -m pytest tests/test_database.py -v
```
Expected: 3 testes PASSED.

- [ ] **Step 6: Commit**

```bash
git add database.py tests/test_database.py tests/__init__.py
git commit -m "feat: add bioimpedancia column and save/get functions to database"
```

---

## Task 3: Adicionar `_detectar_bioimpedancia` em bot.py

**Files:**
- Modify: `bot.py`
- Create: `tests/test_bot_utils.py`

- [ ] **Step 1: Criar arquivo de testes utilitários**

Criar `tests/test_bot_utils.py`:

```python
import sys
import os

# Garante que o diretório raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock das variáveis de ambiente antes de importar bot
os.environ.setdefault("TELEGRAM_TOKEN", "fake_token")
os.environ.setdefault("ANTHROPIC_API_KEY", "fake_key")
os.environ.setdefault("DB_PATH", ":memory:")


def test_detectar_bioimpedancia_por_palavra_chave():
    from bot import _detectar_bioimpedancia
    assert _detectar_bioimpedancia("minha bioimpedância chegou") is True
    assert _detectar_bioimpedancia("tenho 22% gordura e massa magra 58kg") is True
    assert _detectar_bioimpedancia("minha tmb: 1820 kcal") is True
    assert _detectar_bioimpedancia("arquivo inbody 270") is True
    assert _detectar_bioimpedancia("quero emagrecer") is False
    assert _detectar_bioimpedancia("me gera um plano") is False


def test_detectar_bioimpedancia_case_insensitive():
    from bot import _detectar_bioimpedancia
    assert _detectar_bioimpedancia("BIOIMPEDÂNCIA") is True
    assert _detectar_bioimpedancia("Massa Magra 60kg") is True
    assert _detectar_bioimpedancia("InBody 570") is True
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
python -m pytest tests/test_bot_utils.py -v
```
Expected: ERROR — `_detectar_bioimpedancia` não existe ainda.

- [ ] **Step 3: Implementar `_detectar_bioimpedancia` em bot.py**

Após a lista `_FOOD_KEYWORDS` e antes de `_safe_reply`, adicionar:

```python
_BIO_KEYWORDS = [
    "bioimpedância", "bioimpedancia", "% gordura", "% de gordura",
    "massa magra", "massa gorda", "gordura corporal", "gordura visceral",
    "água corporal", "agua corporal", "tmb medida", "tmb:", "tmb :",
    "idade metabólica", "idade metabolica", "inbody", "tanita", "omron",
    "composição corporal", "composicao corporal",
]


def _detectar_bioimpedancia(text: str) -> bool:
    """Retorna True se o texto contém dados ou menção a bioimpedância."""
    texto_lower = text.lower()
    return any(kw in texto_lower for kw in _BIO_KEYWORDS)
```

- [ ] **Step 4: Rodar testes**

```bash
python -m pytest tests/test_bot_utils.py -v
```
Expected: todos PASSED.

- [ ] **Step 5: Commit**

```bash
git add bot.py tests/test_bot_utils.py
git commit -m "feat: add _detectar_bioimpedancia keyword detection"
```

---

## Task 4: Modificar `_build_system_with_profile` para injetar bioimpedância

**Files:**
- Modify: `bot.py`
- Modify: `tests/test_bot_utils.py`

- [ ] **Step 1: Adicionar testes para injeção de bioimpedância no system prompt**

Adicionar ao final de `tests/test_bot_utils.py`:

```python
def test_build_system_with_bioimpedancia():
    from bot import _build_system_with_profile
    profile = {
        "nome": "Ana",
        "peso": "75kg",
        "altura": "1,65m",
        "idade": "30 anos",
        "objetivo": "emagrecer",
        "nivel_atividade": "moderado",
    }
    bio = {
        "gordura_pct": 30.0,
        "massa_magra_kg": 52.5,
        "massa_gorda_kg": 22.5,
        "tmb_medida": 1650,
        "gordura_visceral": 10,
        "agua_corporal_pct": 48.0,
        "idade_metabolica": 38,
        "outros": {},
    }
    result = _build_system_with_profile(profile, bioimpedancia=bio)
    assert "BIOIMPEDÂNCIA DO USUÁRIO" in result
    assert "30.0%" in result
    assert "52.5 kg" in result
    assert "1650 kcal" in result
    assert "massa magra real" in result


def test_build_system_sem_bioimpedancia():
    from bot import _build_system_with_profile
    profile = {"nome": "Ana", "peso": "75kg"}
    result = _build_system_with_profile(profile)
    assert "BIOIMPEDÂNCIA" not in result
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
python -m pytest tests/test_bot_utils.py::test_build_system_with_bioimpedancia tests/test_bot_utils.py::test_build_system_sem_bioimpedancia -v
```
Expected: FAIL — assinatura de `_build_system_with_profile` não aceita `bioimpedancia` ainda.

- [ ] **Step 3: Modificar `_build_system_with_profile` em bot.py**

Substituir a função existente por:

```python
def _build_system_with_profile(profile: dict, taco_context: str = "", bioimpedancia: dict = None) -> str:
    """Injeta o perfil do usuário, bioimpedância e dados TACO no system prompt."""
    system = SYSTEM_PROMPT

    if any(profile.get(k) for k in ["nome", "peso", "altura", "idade", "objetivo"]):
        lines = ["\n\nPERFIL DO USUÁRIO (já coletado anteriormente):"]
        for k, label in [("nome", "Nome"), ("peso", "Peso"), ("altura", "Altura"),
                         ("idade", "Idade"), ("sexo", "Sexo"),
                         ("objetivo", "Objetivo"), ("nivel_atividade", "Nível de atividade")]:
            if profile.get(k):
                lines.append(f"- {label}: {profile[k]}")
        lines.append("Use essas informações sem perguntar de novo, a menos que o usuário queira atualizar.")
        system += "\n".join(lines)

    if bioimpedancia:
        lines = ["\n\nBIOIMPEDÂNCIA DO USUÁRIO (dados medidos por aparelho):"]
        campos = [
            ("gordura_pct",       "Gordura corporal",  "%"),
            ("massa_magra_kg",    "Massa magra",       " kg"),
            ("massa_gorda_kg",    "Massa gorda",       " kg"),
            ("agua_corporal_pct", "Água corporal",     "%"),
            ("gordura_visceral",  "Gordura visceral",  " (nível)"),
            ("tmb_medida",        "TMB medida",        " kcal"),
            ("idade_metabolica",  "Idade metabólica",  " anos"),
        ]
        for campo, label, unidade in campos:
            val = bioimpedancia.get(campo)
            if val is not None:
                lines.append(f"- {label}: {val}{unidade}")
        outros = bioimpedancia.get("outros", {})
        for k, v in outros.items():
            lines.append(f"- {k}: {v}")
        lines.append(
            "Use esses dados para calcular macros com base na massa magra real. "
            "Prefira a TMB medida à TMB estimada por fórmulas."
        )
        system += "\n".join(lines)

    if taco_context:
        system += f"\n\n{taco_context}"

    return system
```

- [ ] **Step 4: Atualizar a chamada de `_build_system_with_profile` em `call_claude`**

Localizar em `bot.py` a linha:
```python
system = _build_system_with_profile(profile, taco_context)
```
Substituir por:
```python
from database import get_bioimpedancia
bio = get_bioimpedancia(user_id)
system = _build_system_with_profile(profile, taco_context, bioimpedancia=bio or None)
```

> Nota: o import de `get_bioimpedancia` deve ser adicionado ao bloco de imports no topo do arquivo junto com os outros imports de `database`:
```python
from database import (
    init_db, upsert_user, get_profile, get_history,
    save_message, clear_history, save_plan,
    count_messages_last_hour, get_stats,
    save_bioimpedancia, get_bioimpedancia,
)
```

- [ ] **Step 5: Rodar todos os testes**

```bash
python -m pytest tests/ -v
```
Expected: todos PASSED.

- [ ] **Step 6: Commit**

```bash
git add bot.py tests/test_bot_utils.py
git commit -m "feat: inject bioimpedancia data into Claude system prompt"
```

---

## Task 5: Implementar `_process_bioimpedancia` em bot.py

**Files:**
- Modify: `bot.py`

- [ ] **Step 1: Adicionar `_process_bioimpedancia` em bot.py**

Adicionar após `_build_system_with_profile` e antes de `start`:

```python
_PROMPT_EXTRAI_BIO = """Analise este laudo de bioimpedância e extraia TODOS os dados presentes.
Responda APENAS com um JSON válido, sem texto antes ou depois, no seguinte formato:
{
  "gordura_pct": número ou null,
  "massa_magra_kg": número ou null,
  "massa_gorda_kg": número ou null,
  "agua_corporal_pct": número ou null,
  "gordura_visceral": número ou null,
  "tmb_medida": número ou null,
  "idade_metabolica": número ou null,
  "outros": {}
}
Use null para campos não encontrados no laudo.
Em "outros", inclua como chaves descritivas (snake_case) qualquer dado adicional não coberto pelos campos padrão.
Converta todos os valores para número (float ou int), sem unidades na string."""


def _formatar_confirmacao_bio(data: dict) -> str:
    """Formata mensagem de confirmação dos dados extraídos."""
    linhas = ["📊 *Dados de Bioimpedância Extraídos*\n"]
    campos = [
        ("gordura_pct",       "Gordura corporal",  "%"),
        ("massa_magra_kg",    "Massa magra",       " kg"),
        ("massa_gorda_kg",    "Massa gorda",       " kg"),
        ("agua_corporal_pct", "Água corporal",     "%"),
        ("gordura_visceral",  "Gordura visceral",  " (nível)"),
        ("tmb_medida",        "TMB medida",        " kcal"),
        ("idade_metabolica",  "Idade metabólica",  " anos"),
    ]
    for campo, label, unidade in campos:
        val = data.get(campo)
        if val is not None:
            linhas.append(f"• {label}: {val}{unidade}")
    outros = data.get("outros", {})
    for k, v in outros.items():
        linhas.append(f"• {k.replace('_', ' ').title()}: {v}")
    linhas.append(
        "\n_Quer gerar seu plano nutricional agora usando esses dados?_\n"
        "Responda *sim* ou *não*."
    )
    return "\n".join(linhas)


async def _process_bioimpedancia(
    update, context, image_b64: str = None, text: str = None
):
    """Extrai dados de bioimpedância (via imagem ou texto), salva e confirma com o usuário."""
    user = update.effective_user
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    if image_b64:
        message_content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64},
            },
            {"type": "text", "text": _PROMPT_EXTRAI_BIO},
        ]
    else:
        message_content = [
            {
                "type": "text",
                "text": f"{_PROMPT_EXTRAI_BIO}\n\nTexto do usuário:\n{text}",
            }
        ]

    try:
        response = client.messages.create(
            model=MODEL_OPUS,
            max_tokens=512,
            messages=[{"role": "user", "content": message_content}],
            timeout=60.0,
        )
        raw = response.content[0].text.strip()

        # Remove code fences caso Claude as adicione
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\n?', '', raw)
            raw = re.sub(r'\n?```$', '', raw.strip())

        bio_data = json.loads(raw)
        # Remove campos nulos para não poluir o perfil
        bio_data = {k: v for k, v in bio_data.items() if v is not None or k == "outros"}
        if "outros" not in bio_data:
            bio_data["outros"] = {}

        save_bioimpedancia(user.id, bio_data)
        context.user_data["aguardando_confirmacao_bio"] = True

        confirmacao = _formatar_confirmacao_bio(bio_data)
        await update.message.reply_text(confirmacao, parse_mode="Markdown")

    except (json.JSONDecodeError, IndexError, anthropic.APIError) as e:
        logger.error(f"Erro ao extrair bioimpedância para user {user.id}: {e}")
        await update.message.reply_text(
            "⚠️ Não consegui extrair os dados da bioimpedância. "
            "Tente digitar os dados manualmente, por exemplo:\n"
            "_\"Gordura 22%, massa magra 58kg, TMB 1820 kcal\"_",
            parse_mode="Markdown",
        )
```

- [ ] **Step 2: Verificar que o bot ainda importa corretamente**

```bash
cd /Users/Lima/Documents/Claude/Projects/NUUtri
python -c "import bot; print('OK')"
```
Expected: `OK` sem erros.

- [ ] **Step 3: Commit**

```bash
git add bot.py
git commit -m "feat: add _process_bioimpedancia extraction and confirmation flow"
```

---

## Task 6: Implementar `handle_document` em bot.py

**Files:**
- Modify: `bot.py`

- [ ] **Step 1: Adicionar `import fitz` no topo de bot.py**

Localizar o bloco de imports no topo de `bot.py` e adicionar:
```python
import fitz  # PyMuPDF
```

- [ ] **Step 2: Adicionar `handle_document` em bot.py**

Adicionar após `handle_photo` e antes de `main`:

```python
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa PDF de bioimpedância enviado pelo usuário."""
    user = update.effective_user
    doc = update.message.document

    if not doc or doc.mime_type != "application/pdf":
        return

    upsert_user(user.id, first_name=user.first_name or "", username=user.username or "")

    if count_messages_last_hour(user.id) >= RATE_LIMIT_PER_HOUR:
        await update.message.reply_text("⏳ Limite de mensagens atingido. Tenta daqui a pouco!")
        return

    await update.message.reply_text(
        "📄 Recebi seu laudo de bioimpedância! Estou analisando..."
    )

    try:
        file = await context.bot.get_file(doc.file_id)
        pdf_bytes = await file.download_as_bytearray()

        pdf = fitz.open(stream=bytes(pdf_bytes), filetype="pdf")
        page = pdf[0]
        pixmap = page.get_pixmap(dpi=150)
        image_bytes = pixmap.tobytes("jpeg")
        pdf.close()

        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        await _process_bioimpedancia(update, context, image_b64=image_b64)

    except Exception as e:
        logger.error(f"Erro ao processar PDF de bioimpedância para user {user.id}: {e}")
        await update.message.reply_text(
            "⚠️ Não consegui processar o PDF. "
            "Tente enviar uma foto do laudo ou digitar os dados manualmente."
        )
```

- [ ] **Step 3: Registrar o handler em `main()`**

Em `main()`, adicionar antes de `app.run_polling()`:
```python
app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
```

- [ ] **Step 4: Verificar importação**

```bash
python -c "import bot; print('OK')"
```
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add bot.py
git commit -m "feat: add handle_document for PDF bioimpedancia processing"
```

---

## Task 7: Modificar `handle_message` para fluxo de confirmação

**Files:**
- Modify: `bot.py`
- Modify: `tests/test_bot_utils.py`

- [ ] **Step 1: Adicionar teste para lógica de confirmação**

Adicionar ao final de `tests/test_bot_utils.py`:

```python
def test_is_affirmative():
    from bot import _is_affirmative
    assert _is_affirmative("sim") is True
    assert _is_affirmative("SIM") is True
    assert _is_affirmative("s") is True
    assert _is_affirmative("quero") is True
    assert _is_affirmative("pode") is True
    assert _is_affirmative("vai") is True
    assert _is_affirmative("gera") is True
    assert _is_affirmative("ok") is True
    assert _is_affirmative("yes") is True
    assert _is_affirmative("não") is False
    assert _is_affirmative("nao") is False
    assert _is_affirmative("n") is False
    assert _is_affirmative("depois") is False
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
python -m pytest tests/test_bot_utils.py::test_is_affirmative -v
```
Expected: ERROR — `_is_affirmative` não existe.

- [ ] **Step 3: Adicionar `_is_affirmative` em bot.py**

Adicionar junto com as outras funções utilitárias (após `_detectar_bioimpedancia`):

```python
_AFIRMATIVOS = {"sim", "s", "yes", "quero", "pode", "vai", "gera", "ok", "claro", "bora", "vamos"}

def _is_affirmative(text: str) -> bool:
    """Retorna True se o texto é uma resposta afirmativa comum."""
    return text.strip().lower() in _AFIRMATIVOS
```

- [ ] **Step 4: Rodar testes**

```bash
python -m pytest tests/test_bot_utils.py -v
```
Expected: todos PASSED.

- [ ] **Step 5: Modificar `handle_message` em bot.py**

Substituir a função existente:
```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _process_text(update, context, update.message.text)
```

Por:
```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""

    # Fluxo de confirmação pós-bioimpedância
    if context.user_data.get("aguardando_confirmacao_bio"):
        context.user_data.pop("aguardando_confirmacao_bio")
        if _is_affirmative(text):
            user = update.effective_user
            profile = get_profile(user.id)
            tem_perfil = profile.get("nome") and profile.get("peso") and profile.get("objetivo")
            if tem_perfil:
                trigger = (
                    "O usuário quer gerar um novo plano nutricional em PDF. "
                    "Já tenho as informações dele no perfil, incluindo dados de bioimpedância. "
                    "Gere o JSON do plano diretamente, usando a massa magra para calcular os macros. "
                    "Use os valores da tabela TACO para os alimentos."
                )
            else:
                trigger = (
                    "Quero gerar meu plano nutricional personalizado em PDF. "
                    "Tenho dados de bioimpedância salvos no meu perfil. "
                    "Se ainda faltar alguma informação, me pergunte sobre: "
                    "nome, peso, altura, idade, sexo, objetivo e nível de atividade física."
                )
            await _process_text(update, context, trigger, use_opus=True)
        else:
            await update.message.reply_text(
                "Ok! Seus dados de bioimpedância foram salvos. 📊\n"
                "Use /plano quando quiser gerar seu plano nutricional. 💪"
            )
        return

    # Detecção de dados de bioimpedância em texto livre
    if _detectar_bioimpedancia(text):
        await _process_bioimpedancia(update, context, text=text)
        return

    await _process_text(update, context, text)
```

- [ ] **Step 6: Rodar todos os testes**

```bash
python -m pytest tests/ -v
```
Expected: todos PASSED.

- [ ] **Step 7: Verificar importação final**

```bash
python -c "import bot; print('OK')"
```
Expected: `OK`.

- [ ] **Step 8: Commit final**

```bash
git add bot.py tests/test_bot_utils.py
git commit -m "feat: add bioimpedancia confirmation flow and handle_message detection"
```

---

## Checklist de verificação manual

Após a implementação, testar manualmente no Telegram:

- [ ] Enviar PDF de bioimpedância → bot responde "Recebi seu laudo..." → exibe dados extraídos → pergunta se quer plano
- [ ] Responder "sim" → bot gera plano PDF usando composição corporal
- [ ] Responder "não" → bot confirma que dados foram salvos
- [ ] Digitar "Minha gordura é 22%, massa magra 58kg, TMB 1820" → mesmo fluxo de confirmação
- [ ] Rodar `/plano` depois → plano usa bioimpedância injetada no system prompt
- [ ] PDF inválido (não bioimpedância) → Claude tenta extrair; se falhar, orienta digitar manualmente
