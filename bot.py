import os
import io
import json
import base64
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
from pdf_generator import generate_nutrition_pdf

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

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

ANÁLISE DE IMAGENS:
Ao receber foto de prato, responda neste formato:
🍽️ *Análise Nutricional Estimada*
*Alimentos identificados:* • [alimento + porção estimada]
📊 *Estimativa de Macros*
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

NUNCA:
- Prescreva dietas abaixo de 1200 kcal sem ressalvas
- Faça promessas de resultados irreais
- Substitua consulta profissional presencial para casos clínicos"""

user_histories: dict[int, list] = {}
MAX_HISTORY = 30


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_histories[user.id] = []
    await update.message.reply_text(
        f"Olá, {user.first_name}! 🥗 Sou o *NutriIA* da *NUUtri*, seu coach de nutrição e fitness.\n\n"
        "Posso te ajudar com:\n"
        "• 💬 Dúvidas sobre dieta e alimentação\n"
        "• 📸 Análise de fotos de refeições\n"
        "• 📄 *Plano nutricional em PDF* — use /plano\n\n"
        "Me conta seu objetivo ou manda uma foto do seu prato! 💪",
        parse_mode="Markdown"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_histories[user.id] = []
    await update.message.reply_text("✅ Conversa reiniciada! Bora do zero. 🎯")


async def plano_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in user_histories:
        user_histories[user.id] = []
    trigger = ("Quero gerar meu plano nutricional personalizado em PDF. "
               "Se ainda não tiver minhas informações, me pergunte sobre: nome, peso, altura, idade, sexo, objetivo e nível de atividade física.")
    await _process_text(update, context, trigger)


async def call_claude(user_id: int, message_content: list) -> str:
    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": message_content})
    if len(user_histories[user_id]) > MAX_HISTORY:
        user_histories[user_id] = user_histories[user_id][-MAX_HISTORY:]

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=user_histories[user_id],
    )
    reply = response.content[0].text
    user_histories[user_id].append({"role": "assistant", "content": reply})
    return reply


async def _process_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user = update.effective_user
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        reply = await call_claude(user.id, [{"type": "text", "text": text}])

        # Verifica se é um JSON de plano nutricional
        stripped = reply.strip()
        if stripped.startswith("{") and '"GERAR_PDF"' in stripped:
            try:
                plan_data = json.loads(stripped)
                if plan_data.get("GERAR_PDF"):
                    await update.message.reply_text("📄 Gerando seu plano NUUtri personalizado...")
                    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_document")
                    pdf_bytes = generate_nutrition_pdf(plan_data)
                    nome = plan_data.get("user_name", "usuario").replace(" ", "_")
                    filename = f"plano_nuutri_{nome}.pdf"
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=io.BytesIO(pdf_bytes),
                        filename=filename,
                        caption=(
                            f"✅ *Seu plano NUUtri está pronto!*\n\n"
                            f"🎯 Objetivo: {plan_data.get('objetivo', '')}\n"
                            f"🔥 {plan_data.get('calorias', '')} kcal/dia • "
                            f"💪 {plan_data.get('proteinas', '')}g prot • "
                            f"🍞 {plan_data.get('carbs', '')}g carb • "
                            f"🥑 {plan_data.get('gorduras', '')}g gord\n\n"
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
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        caption = update.message.caption or "Analise este prato e estime os macros e calorias."
        message_content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
            {"type": "text", "text": caption},
        ]
        reply = await call_claude(user.id, message_content)
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        await update.message.reply_text("⚠️ Não consegui analisar a imagem. Tenta de novo ou descreve o prato por texto!")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("plano", plano_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logger.info("NUUtri bot iniciado!")
    app.run_polling()


if __name__ == "__main__":
    main()
