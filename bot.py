import os
import io
import json
import re
import base64
import fitz  # PyMuPDF
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
from pdf_generator import generate_nutrition_pdf, generate_weekly_nutrition_pdf
from database import (
    init_db, upsert_user, get_profile, get_history,
    save_message, clear_history, save_plan,
    count_messages_last_hour, get_stats,
    save_bioimpedancia, get_bioimpedancia,
)
from taco_db import init_taco_db, buscar_alimento, gerar_contexto_nutricional, resumo_banco

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN      = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY   = os.environ["ANTHROPIC_API_KEY"]
RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "40"))
OWNER_ID            = int(os.environ.get("OWNER_ID", "0"))

MODEL_OPUS  = "claude-opus-4-5"
MODEL_HAIKU = "claude-haiku-4-5-20251001"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é o NutriIA, nutricionista esportivo e coach fitness da NUUtri. Ajude pessoas a alcançarem seus objetivos com orientação nutricional personalizada, prática e baseada em ciência.

PERSONALIDADE:
- Empático, motivador e direto ao ponto
- Linguagem acessível, sempre em português do Brasil
- Adapta o tom para o Telegram (mensagens curtas e dinâmicas)

COMPETÊNCIAS:
- Cálculo de TDEE, TMB e distribuição de macros
- Cardápios personalizados (emagrecer, hipertrofia, manutenção)
- Estratégias: deficit calórico, bulk, cut, recomposição
- Timing nutricional, suplementação, hidratação
- Dietas: low-carb, mediterrânea, vegetariana, jejum intermitente

BASE DE DADOS NUTRICIONAL:
Você tem acesso à Tabela TACO (Tabela Brasileira de Composição de Alimentos) da Unicamp.
Quando dados da TACO forem injetados no contexto, USE-OS como referência para valores nutricionais.
Sempre que possível, cite a fonte: "segundo a tabela TACO (Unicamp)".
Se os dados da TACO estiverem disponíveis, prefira-os a estimativas genéricas.

ANÁLISE DE IMAGENS:
Ao receber foto de prato, responda neste formato:
🍽️ *Análise Nutricional Estimada*
*Alimentos identificados:* • [alimento + porção estimada]
📊 *Estimativa de Macros (fonte: TACO/Unicamp)*
• 🔥 Calorias: ~X kcal  • 💪 Proteínas: ~Xg  • 🍞 Carboidratos: ~Xg  • 🥑 Gorduras: ~Xg
✅ *Avaliação:* [comentário rápido]
💡 *Dica:* [sugestão prática]
_⚠️ Estimativas visuais — podem variar conforme porções reais._

GERAÇÃO DE PLANO NUTRICIONAL EM PDF:
Quando o usuário pedir um plano nutricional (ex: /plano, "gera meu plano", "quero um PDF"), você deve:
1. Se ainda não tiver as informações necessárias, coletá-las de forma conversacional
2. Quando tiver dados suficientes (nome, peso, altura, idade, sexo, objetivo, nível de atividade), responda APENAS com um JSON válido neste formato exato, sem nenhum texto antes ou depois:

{"GERAR_PDF": true, "user_name": "nome", "objetivo": "objetivo detalhado", "peso": "Xkg", "altura": "X,XXm", "idade": "X anos", "sexo": "Masculino/Feminino", "nivel_atividade": "descrição", "calorias": "XXXX", "proteinas": "XXX", "carbs": "XXX", "gorduras": "XX", "refeicoes": [{"nome": "emoji + nome (horário)", "alimentos": ["alimento 1 + macro resumido", "alimento 2"]}], "suplementos": "lista de suplementos recomendados", "observacoes": "dicas importantes"}

Monte um plano completo com 5-6 refeições bem distribuídas, realista e detalhado.
Use os valores da tabela TACO para calcular os macros de cada alimento no plano.

NUNCA:
- Prescreva dietas abaixo de 1200 kcal sem ressalvas
- Faça promessas de resultados irreais
- Substitua consulta profissional presencial para casos clínicos"""


# ── Palavras-chave de alimentos para busca na TACO ───────────────────────────
_FOOD_KEYWORDS = [
    "arroz", "feijão", "frango", "carne", "peixe", "ovo", "leite", "queijo",
    "pão", "macarrão", "batata", "mandioca", "banana", "maçã", "laranja",
    "aveia", "whey", "iogurte", "azeite", "salmão", "atum", "tilápia",
    "brócolis", "espinafre", "tomate", "cenoura", "abóbora", "inhame",
    "lentilha", "grão-de-bico", "amendoim", "castanha", "granola",
    "tapioca", "quinoa", "abacate", "mamão", "melancia", "morango",
    "açaí", "pasta de amendoim", "cream cheese", "requeijão", "ricota",
    "cottage", "presunto", "peru", "sardinha", "camarão", "costela",
    "filé", "alcatra", "patinho", "músculo", "coxão", "maminha",
    "batata doce", "couve", "rúcula", "alface", "pepino", "beterraba",
    "chocolate", "mel", "açúcar", "pipoca", "cuscuz",
]

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


_AFIRMATIVOS = {"sim", "s", "yes", "quero", "pode", "vai", "gera", "ok", "claro", "bora", "vamos"}

def _is_affirmative(text: str) -> bool:
    """Retorna True se o texto é uma resposta afirmativa comum."""
    return text.strip().lower() in _AFIRMATIVOS


async def _safe_reply(message, text: str):
    """Envia resposta com Markdown; faz fallback para texto puro se o parse falhar."""
    try:
        await message.reply_text(text, parse_mode="Markdown")
    except Exception:
        await message.reply_text(text)


def _extrair_termos_alimentos(texto: str) -> list[str]:
    """
    Identifica menções a alimentos no texto do usuário para buscar na TACO.
    Retorna lista de termos encontrados.
    """
    texto_lower = texto.lower()
    encontrados = []
    for kw in _FOOD_KEYWORDS:
        if kw in texto_lower:
            encontrados.append(kw)
    return encontrados[:10]  # limita a 10 termos para não poluir o contexto


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, first_name=user.first_name or "", username=user.username or "")
    profile = get_profile(user.id)
    if profile.get("nome"):
        greeting = (
            f"Que bom te ver de volta, *{profile['nome']}*! 🥗\n\n"
            f"Lembro que seu objetivo é: _{profile.get('objetivo', 'não definido')}_\n\n"
            "Posso te ajudar com:\n"
            "• 💬 Dúvidas sobre dieta e alimentação\n"
            "• 📸 Análise de fotos de refeições\n"
            "• 📄 *Plano nutricional em PDF* — use /plano\n"
            "• 👤 Seu perfil — use /perfil\n"
            "• 🔍 *Consultar alimentos* — ex: \"quantas calorias tem o arroz?\"\n\n"
            "O que vamos trabalhar hoje? 💪"
        )
    else:
        greeting = (
            f"Olá, {user.first_name}! 🥗 Sou o *NutriIA* da *NUUtri*, seu coach de nutrição e fitness.\n\n"
            "Posso te ajudar com:\n"
            "• 💬 Dúvidas sobre dieta e alimentação\n"
            "• 📸 Análise de fotos de refeições\n"
            "• 📄 *Plano nutricional em PDF* — use /plano\n"
            "• 👤 Seu perfil — use /perfil\n"
            "• 🔍 *Consultar alimentos* — ex: \"quantas calorias tem o frango?\"\n\n"
            "Me conta seu objetivo ou manda uma foto do seu prato! 💪"
        )
    await update.message.reply_text(greeting, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    clear_history(user.id)
    await update.message.reply_text(
        "✅ Histórico de conversa apagado! Seu perfil foi mantido.\n"
        "Use /perfil para ver o que sei sobre você. 🎯"
    )


async def perfil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    profile = get_profile(user.id)
    if not profile:
        await update.message.reply_text("Ainda não tenho informações suas. Me conta um pouco sobre você! 😊")
        return
    fields = [("nome","Nome"),("peso","Peso"),("altura","Altura"),("idade","Idade"),
              ("sexo","Sexo"),("objetivo","Objetivo"),("nivel_atividade","Atividade")]
    lines = ["👤 *Seu perfil NUUtri*\n"]
    for k, label in fields:
        val = profile.get(k)
        lines.append(f"*{label}:* {val if val else '—'}")
    lines.append("\n_Para atualizar algum dado, é só me contar na conversa._")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando oculto /stats para o dono do bot acompanhar uso."""
    if OWNER_ID and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⚠️ Comando não disponível.")
        return
    stats = get_stats()
    taco = resumo_banco()
    msg = (
        "📊 *Estatísticas NUUtri*\n\n"
        f"👥 Usuários: {stats['total_users']}\n"
        f"💬 Mensagens: {stats['total_messages']}\n"
        f"📄 Planos gerados: {stats['total_plans']}\n"
        f"🥗 Base TACO: {taco['total_alimentos']} alimentos\n"
    )
    if stats["top_objectives"]:
        msg += "\n🎯 *Objetivos mais comuns:*\n"
        for item in stats["top_objectives"]:
            msg += f"• {item['objetivo']} ({item['count']}x)\n"
    await update.message.reply_text(msg, parse_mode="Markdown")


async def plano_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, first_name=user.first_name or "", username=user.username or "")

    semanal = bool(context.args and "semanal" in [a.lower() for a in context.args])
    context.user_data["plano_semanal"] = semanal

    profile = get_profile(user.id)
    tem_perfil = profile.get("nome") and profile.get("peso") and profile.get("objetivo")

    if semanal:
        if tem_perfil:
            trigger = (
                "O usuário quer gerar um plano nutricional SEMANAL (7 dias) em PDF. "
                "Já tenho as informações dele no perfil. Gere o JSON do plano com refeições para cada dia da semana. "
                "Use os valores da tabela TACO para os alimentos."
            )
        else:
            trigger = (
                "Quero gerar meu plano nutricional SEMANAL personalizado em PDF (7 dias completos). "
                "Se ainda não tiver minhas informações, me pergunte sobre: "
                "nome, peso, altura, idade, sexo, objetivo e nível de atividade física."
            )
    else:
        if tem_perfil:
            trigger = (
                "O usuário quer gerar um novo plano nutricional em PDF. "
                "Já tenho as informações dele no perfil. Gere o JSON do plano diretamente. "
                "Use os valores da tabela TACO para os alimentos."
            )
        else:
            trigger = (
                "Quero gerar meu plano nutricional personalizado em PDF. "
                "Se ainda não tiver minhas informações, me pergunte sobre: "
                "nome, peso, altura, idade, sexo, objetivo e nível de atividade física."
            )
    await _process_text(update, context, trigger, use_opus=True)


async def call_claude(user_id: int, message_content: list, profile: dict, taco_context: str = "", use_opus: bool = False) -> str:
    history = get_history(user_id)

    # Salva mensagem do usuário no banco
    save_message(user_id, "user", message_content)

    # Adiciona a mensagem atual ao histórico para enviar à API
    history.append({
        "role": "user",
        "content": message_content,
    })

    bio = get_bioimpedancia(user_id)
    system = _build_system_with_profile(profile, taco_context, bioimpedancia=bio or None)
    model = MODEL_OPUS if use_opus else MODEL_HAIKU
    logger.info(f"Chamando Claude com modelo: {model}")

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=history,
        timeout=60.0,
    )
    if not response.content:
        logger.error("Resposta vazia recebida da API do Claude")
        raise ValueError("Resposta vazia da API")
    reply = response.content[0].text

    # Salva resposta no banco
    save_message(user_id, "assistant", reply)
    return reply


async def _process_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, use_opus: bool = False):
    user = update.effective_user
    upsert_user(user.id, first_name=user.first_name or "", username=user.username or "")

    # Rate limiting
    msg_count = count_messages_last_hour(user.id)
    if msg_count >= RATE_LIMIT_PER_HOUR:
        await update.message.reply_text(
            f"⏳ Você enviou muitas mensagens na última hora ({msg_count}/{RATE_LIMIT_PER_HOUR}).\n"
            "Aguarde alguns minutos antes de continuar. 🙏"
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        profile = get_profile(user.id)

        # Busca dados nutricionais na TACO se o usuário mencionou alimentos
        termos = _extrair_termos_alimentos(text)
        taco_context = gerar_contexto_nutricional(termos) if termos else ""

        try:
            reply = await call_claude(user.id, [{"type": "text", "text": text}], profile, taco_context, use_opus=use_opus)
        except anthropic.APITimeoutError:
            logger.warning(f"Timeout na chamada ao Claude para user {user.id}")
            await update.message.reply_text("⏱️ O servidor demorou demais para responder. Tenta de novo em instantes!")
            return
        except anthropic.APIError as e:
            logger.error(f"Erro da API Anthropic para user {user.id}: {e}")
            await update.message.reply_text("❌ Tive um problema ao conectar com a IA. Tenta de novo em instantes!")
            return

        # Detecta JSON de plano nutricional
        if '"GERAR_PDF"' in reply:
            # Remove code fences que o Claude pode adicionar (```json ... ```)
            stripped = reply.strip()
            if stripped.startswith("```"):
                stripped = re.sub(r'^```(?:json)?\n?', '', stripped)
                stripped = re.sub(r'\n?```$', '', stripped.strip())

            json_start = stripped.find("{")
            try:
                plan_data = json.loads(stripped[json_start:]) if json_start != -1 else None
                if plan_data and plan_data.get("GERAR_PDF"):
                    semanal = context.user_data.pop("plano_semanal", False)
                    tipo = "semanal" if semanal else "diário"
                    await update.message.reply_text(f"📄 Gerando seu plano NUUtri {tipo} personalizado...")
                    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_document")

                    pdf_bytes = (
                        generate_weekly_nutrition_pdf(plan_data)
                        if semanal
                        else generate_nutrition_pdf(plan_data)
                    )
                    save_plan(user.id, plan_data)

                    nome = plan_data.get("user_name", "usuario").replace(" ", "_")
                    sufixo = "_semanal" if semanal else ""
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=io.BytesIO(pdf_bytes),
                        filename=f"plano_nuutri_{nome}{sufixo}.pdf",
                        caption=(
                            f"✅ *Seu plano NUUtri está pronto!*\n\n"
                            f"🎯 Objetivo: {plan_data.get('objetivo', '')}\n"
                            f"🔥 {plan_data.get('calorias', '')} kcal/dia • "
                            f"💪 {plan_data.get('proteinas', '')}g prot • "
                            f"🍞 {plan_data.get('carbs', '')}g carb • "
                            f"🥑 {plan_data.get('gorduras', '')}g gord\n\n"
                            "_📊 Valores baseados na Tabela TACO (Unicamp)_\n"
                            "_Qualquer dúvida, é só perguntar!_"
                        ),
                        parse_mode="Markdown"
                    )
                    return
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao parsear JSON do plano para user {user.id}: {e}\nResposta: {reply[:300]}")
                await update.message.reply_text(
                    "⚠️ Houve um problema ao gerar seu plano. Por favor, tente novamente digitando /plano."
                )
                return

        await _safe_reply(update.message, reply)

    except Exception as e:
        logger.error(f"Erro inesperado em _process_text para user {update.effective_user.id}: {e}")
        await update.message.reply_text("⚠️ Ops! Tive um probleminha. Tenta de novo em instantes!")


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


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, first_name=user.first_name or "", username=user.username or "")

    # Rate limiting também para fotos
    if count_messages_last_hour(user.id) >= RATE_LIMIT_PER_HOUR:
        await update.message.reply_text("⏳ Limite de mensagens atingido. Tenta daqui a pouco!")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        caption = update.message.caption or "Analise este prato e estime os macros e calorias."

        # Tenta extrair termos da legenda para buscar na TACO
        termos = _extrair_termos_alimentos(caption)
        taco_context = gerar_contexto_nutricional(termos) if termos else ""

        message_content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
            {"type": "text", "text": caption},
        ]
        profile = get_profile(user.id)
        reply = await call_claude(user.id, message_content, profile, taco_context, use_opus=True)
        await _safe_reply(update.message, reply)
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        await update.message.reply_text("⚠️ Não consegui analisar a imagem. Tenta de novo ou descreve por texto!")


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


def main():
    init_db()       # garante que as tabelas de usuários existem
    init_taco_db()  # inicializa a base de dados nutricional TACO
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("reset",  reset))
    app.add_handler(CommandHandler("perfil", perfil_command))
    app.add_handler(CommandHandler("plano",  plano_command))
    app.add_handler(CommandHandler("stats",  stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    logger.info("NUUtri bot iniciado com SQLite + base TACO!")
    app.run_polling()


if __name__ == "__main__":
    main()
