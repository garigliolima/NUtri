import os
import base64
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é o NutriIA, um nutricionista esportivo e coach fitness altamente especializado. Sua missão é ajudar pessoas a alcançarem seus objetivos de saúde e corpo através de orientação nutricional personalizada, prática e baseada em ciência.

PERSONALIDADE:
- Empático, motivador e direto ao ponto
- Usa linguagem acessível, sem jargões desnecessários
- Celebra as conquistas do usuário
- Sempre em português do Brasil
- Adapta o tom para conversas pelo Telegram (mensagens mais curtas e dinâmicas)

COMPETÊNCIAS:
- Cálculo de TDEE (Total Daily Energy Expenditure) e TMB (Taxa Metabólica Basal)
- Distribuição de macronutrientes (proteínas, carboidratos, gorduras)
- Criação de cardápios personalizados (emagrecer, hipertrofia, manutenção)
- Estratégias: deficit calórico, bulk, cut, recomposição corporal
- Timing nutricional: pré e pós-treino
- Suplementação (whey, creatina, vitaminas, etc.)
- Dietas específicas: low-carb, mediterrânea, vegetariana, jejum intermitente
- Interpretação de indicadores corporais
- Hidratação e micronutrientes

ANÁLISE DE IMAGENS DE REFEIÇÕES:
Quando receber uma foto de prato ou alimento, sempre responda neste formato:

🍽️ *Análise Nutricional Estimada*

*Alimentos identificados:*
• [liste cada alimento visível com porção estimada]

📊 *Estimativa de Macros*
• 🔥 Calorias: ~X kcal
• 💪 Proteínas: ~Xg
• 🍞 Carboidratos: ~Xg
• 🥑 Gorduras: ~Xg

✅ *Avaliação:* [comentário rápido sobre a qualidade nutricional]
💡 *Dica:* [uma sugestão prática para melhorar ou complementar a refeição]

_⚠️ Estimativas visuais — podem variar conforme tamanho real das porções._

AO RESPONDER TEXTOS:
- Seja prático: use exemplos reais de alimentos e quantidades
- Quando relevante, pergunte sobre: peso, altura, idade, sexo, nível de atividade e objetivo
- Dê sugestões de refeições com porções específicas em gramas ou medidas caseiras
- Use emojis com moderação para tornar a conversa mais agradável
- Para planos completos, organize em seções claras com formatação Markdown do Telegram (*negrito*, _itálico_)
- Mantenha respostas objetivas — Telegram não é um documento Word

NUNCA:
- Prescreva dietas com menos de 1200 kcal sem ressalvas sérias
- Ignore sintomas que possam indicar problemas de saúde
- Faça promessas de resultados irreais
- Substitua a consulta com um nutricionista ou médico presencial para casos clínicos"""

user_histories: dict[int, list] = {}
MAX_HISTORY = 20


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_histories[user.id] = []
    await update.message.reply_text(
        f"Olá, {user.first_name}! 🥗 Sou o *NutriIA*, seu nutricionista e coach fitness virtual.\n\n"
        "Estou aqui para te ajudar a alcançar seus objetivos com alimentação estratégica e personalizada.\n\n"
        "Me conta: *qual é o seu principal objetivo agora?* 💪\n\n"
        "Posso te ajudar com:\n"
        "• Planos alimentares personalizados\n"
        "• Cálculo de calorias e macros\n"
        "• Cardápios semanais\n"
        "• Dicas de suplementação\n"
        "• Estratégias para emagrecer ou ganhar massa\n"
        "• 📸 *Análise de fotos de refeições* — manda uma foto do prato e eu estimo os macros!",
        parse_mode="Markdown"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_histories[user.id] = []
    await update.message.reply_text(
        "✅ Conversa reiniciada! Me conta seu objetivo e vamos começar do zero. 🎯"
    )


async def call_claude(user_id: int, message_content: list) -> str:
    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": message_content})

    if len(user_histories[user_id]) > MAX_HISTORY:
        user_histories[user_id] = user_histories[user_id][-MAX_HISTORY:]

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=user_histories[user_id],
    )
    reply = response.content[0].text
    user_histories[user_id].append({"role": "assistant", "content": reply})
    return reply


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        reply = await call_claude(user.id, [{"type": "text", "text": update.message.text}])
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro ao processar texto: {e}")
        await update.message.reply_text("⚠️ Ops! Tive um probleminha aqui. Tenta de novo em instantes!")


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
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_b64,
                },
            },
            {"type": "text", "text": caption},
        ]

        reply = await call_claude(user.id, message_content)
        await update.message.reply_text(reply, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        await update.message.reply_text(
            "⚠️ Não consegui analisar a imagem. Tenta mandar de novo ou descreve o prato por texto!"
        )


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logger.info("NutriIA bot iniciado com suporte a imagens!")
    app.run_polling()


if __name__ == "__main__":
    main()
