import os
import io
import json
import re
import base64
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
from pdf_generator import generate_nutrition_pdf
from database import (
    init_db, upsert_user, get_profile, get_history,
    save_message, clear_history, save_plan,
    count_messages_last_hour, get_stats,
)
from taco_db import init_taco_db, buscar_alimento, gerar_contexto_nutricional, resumo_banco

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN     = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "40"))

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


def _build_system_with_profile(profile: dict, taco_context: str = "") -> str:
    """Injeta o perfil do usuário e dados TACO no system prompt."""
    system = SYSTEM_PROMPT

    if any(profile.get(k) for k in ["nome","peso","altura","idade","objetivo"]):
        lines = ["\n\nPERFIL DO USUÁRIO (já coletado anteriormente):"]
        for k, label in [("nome","Nome"),("peso","Peso"),("altura","Altura"),
                         ("idade","Idade"),("sexo","Sexo"),
                         ("objetivo","Objetivo"),("nivel_atividade","Nível de atividade")]:
            if profile.get(k):
                lines.append(f"- {label}: {profile[k]}")
        lines.append("Use essas informações sem perguntar de novo, a menos que o usuário queira atualizar.")
        system += "\n".join(lines)

    if taco_context:
        system += f"\n\n{taco_context}"

    return system


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
    profile = get_profile(user.id)
    if profile.get("nome") and profile.get("peso") and profile.get("objetivo"):
        trigger = (
            f"O usuário quer gerar um novo plano nutricional em PDF. "
            f"Já tenho as informações dele no perfil. Gere o JSON do plano diretamente. "
            f"Use os valores da tabela TACO para os alimentos."
        )
    else:
        trigger = (
            "Quero gerar meu plano nutricional personalizado em PDF. "
            "Se ainda não tiver minhas informações, me pergunte sobre: "
            "nome, peso, altura, idade, sexo, objetivo e nível de atividade física."
        )
    await _process_text(update, context, trigger)


async def call_claude(user_id: int, message_content: list, profile: dict, taco_context: str = "") -> str:
    history = get_history(user_id)

    # Salva mensagem do usuário no banco
    save_message(user_id, "user", message_content)

    # Adiciona a mensagem atual ao histórico para enviar à API
    history.append({
        "role": "user",
        "content": message_content,
    })

    system = _build_system_with_profile(profile, taco_context)

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        system=system,
        messages=history,
    )
    reply = response.content[0].text

    # Salva resposta no banco
    save_message(user_id, "assistant", reply)
    return reply


async def _process_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
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

        reply = await call_claude(user.id, [{"type": "text", "text": text}], profile, taco_context)

        # Detecta JSON de plano nutricional
        stripped = reply.strip()
        if stripped.startswith("{") and '"GERAR_PDF"' in stripped:
            try:
                plan_data = json.loads(stripped)
                if plan_data.get("GERAR_PDF"):
                    await update.message.reply_text("📄 Gerando seu plano NUUtri personalizado...")
                    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_document")

                    pdf_bytes = generate_nutrition_pdf(plan_data)
                    save_plan(user.id, plan_data)  # persiste no banco

                    nome = plan_data.get("user_name", "usuario").replace(" ", "_")
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=io.BytesIO(pdf_bytes),
                        filename=f"plano_nuutri_{nome}.pdf",
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
            except json.JSONDecodeError:
                pass

        await update.message.reply_text(reply, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Erro: {e}")
        await update.message.reply_text("⚠️ Ops! Tive um probleminha. Tenta de novo em instantes!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _process_text(update, context, update.message.text)


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
        reply = await call_claude(user.id, message_content, profile, taco_context)
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        await update.message.reply_text("⚠️ Não consegui analisar a imagem. Tenta de novo ou descreve por texto!")


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
    logger.info("NUUtri bot iniciado com SQLite + base TACO!")
    app.run_polling()


if __name__ == "__main__":
    main()
