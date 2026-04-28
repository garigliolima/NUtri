# Bioimpedância — Design Spec
**Data:** 2026-04-28  
**Projeto:** NUUtri (bot Telegram de nutrição)  
**Status:** Aprovado

---

## Objetivo

Permitir que clientes enviem laudos de bioimpedância (PDF ou texto manual) para que o plano nutricional seja gerado com base na composição corporal real — usando massa magra, % de gordura, TMB medida, entre outros dados — em vez de apenas peso e altura.

---

## Fluxo

### Via PDF
1. Cliente envia PDF no chat do Telegram
2. `handle_document` detecta `mimetype == application/pdf`
3. PyMuPDF converte página 1 em JPEG em memória
4. `_process_bioimpedancia(image_b64=...)` chama Claude Vision para extração
5. Claude retorna JSON com todos os dados encontrados no laudo
6. Bot salva no perfil e envia confirmação formatada ao cliente
7. Bot pergunta: "Quer gerar seu plano agora com esses dados?"
8. Se confirmado → chama `_process_text` com trigger igual ao de `plano_command` (bioimpedância já está no perfil, então é injetada via `_build_system_with_profile`)

### Via texto manual
1. Cliente digita dados no chat (ex: "minha gordura é 22%, massa magra 58kg, TMB 1820")
2. `handle_message` chama `_detectar_bioimpedancia(text)` antes de `_process_text`
3. Se detectado → `_process_bioimpedancia(text=...)` chama Claude para normalizar os dados
4. Mesmo fluxo de confirmação e pergunta acima

---

## Banco de Dados

### Alteração em `database.py`
- Nova coluna `bioimpedancia TEXT` (JSON) na tabela `users`
- Migration automática: `ALTER TABLE users ADD COLUMN bioimpedancia TEXT` dentro de `init_db()`, com `IF NOT EXISTS` ou `try/except`

### Funções novas
```python
def save_bioimpedancia(user_id: int, data: dict) -> None
def get_bioimpedancia(user_id: int) -> dict  # retorna {} se ausente
```

### Estrutura do JSON salvo
```json
{
  "gordura_pct": 22.5,
  "massa_magra_kg": 58.3,
  "massa_gorda_kg": 17.2,
  "agua_corporal_pct": 55.1,
  "gordura_visceral": 8,
  "tmb_medida": 1820,
  "idade_metabolica": 34,
  "outros": {}
}
```

O campo `outros` captura qualquer dado adicional que o Claude extrair do laudo e não se encaixe nos campos padrão, garantindo que nenhuma informação seja descartada.

---

## Código — `bot.py`

### `_detectar_bioimpedancia(text: str) -> bool`
Verifica presença de keywords: `"bioimpedância"`, `"bioimpedancia"`, `"% gordura"`, `"massa magra"`, `"massa gorda"`, `"inbody"`, `"tanita"`, `"omron"`, `"água corporal"`, `"gordura visceral"`, `"tmb medida"`, `"tmb:"`, `"idade metabólica"`.

### `_process_bioimpedancia(update, context, image_b64=None, text=None)`
- Monta `message_content` para Claude: imagem (Vision) ou texto, com prompt de extração
- Prompt ao Claude: extrair TODOS os dados da bioimpedância e retornar JSON com campos padrão + `outros` para o restante
- Salva resultado via `save_bioimpedancia(user_id, data)`
- Envia mensagem de confirmação formatada com os dados extraídos
- Pergunta ao usuário se quer gerar o plano agora
- Seta `context.user_data["aguardando_confirmacao_bio"] = True` para capturar a resposta

### `handle_document(update, context)`
- Filtra `document.mime_type == "application/pdf"`
- Baixa o arquivo com `bot.get_file` + `download_as_bytearray`
- Converte com `fitz.open(stream=bytes, filetype="pdf")[0].get_pixmap().tobytes("jpeg")`
- Encoda em base64 e chama `_process_bioimpedancia(image_b64=...)`

### `handle_message` — alteração
Antes de chamar `_process_text`, verifica:
1. Se `context.user_data.get("aguardando_confirmacao_bio")` → trata resposta de confirmação: afirmativos aceitos = `{"sim", "s", "yes", "quero", "pode", "vai", "gera", "ok"}` (case-insensitive, strip). Se afirmativo, limpa a flag e chama `_process_text` com trigger de plano. Se negativo, limpa a flag e responde "Ok! Seus dados foram salvos. Use /plano quando quiser gerar."
2. Se `_detectar_bioimpedancia(text)` → chama `_process_bioimpedancia(text=...)`

### `_build_system_with_profile` — alteração
Quando `bioimpedancia` estiver presente no perfil, injeta bloco adicional no system prompt:

```
BIOIMPEDÂNCIA DO USUÁRIO (dados medidos):
- Gordura corporal: X%
- Massa magra: Xkg
- TMB medida: X kcal
...
Use esses dados para calcular macros com base na massa magra real.
Prefira a TMB medida à TMB estimada por fórmulas.
```

### `main()` — alteração
Registra novo handler:
```python
app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
```

---

## Dependências

`requirements.txt`:
```
PyMuPDF>=1.24.0
```

---

## O que não muda

- `pdf_generator.py` — sem alterações
- `taco_db.py` — sem alterações
- Sistema de rate limiting — PDFs contam como 1 mensagem, mesmo fluxo
- Geração de PDF — o `/plano` continua igual; a bioimpedância entra via system prompt

---

## Critérios de sucesso

- Cliente envia PDF de balança InBody, Tanita ou Omron → bot extrai dados e confirma
- Cliente digita dados manualmente → bot detecta e normaliza
- Dados salvos persistem entre sessões (próximo `/plano` já os usa)
- Plano gerado após bioimpedância menciona cálculo baseado em massa magra
