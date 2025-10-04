from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import logging
from API.ai_21 import ask_ai21_with_rag
from aiohttp import web
from rag_system import RAGSystem  # подключаем твою систему RAG

logger = logging.getLogger(__name__)
router = Router()

# Инициализация RAG
rag = RAGSystem(always_enabled=True)

# --------------------
# Mini App с закреплением
# --------------------
@router.message(F.text & F.text.startswith("/mini_app"))
async def send_mini_app_inline(message: types.Message):
    web_app = WebAppInfo(url="https://ai-mini-app.wuaze.com")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть Mini App", web_app=web_app)]
    ])
    sent_msg = await message.answer(
        "Нажми кнопку ниже, чтобы открыть Mini App:",
        reply_markup=keyboard
    )

    try:
        await message.bot.pin_chat_message(message.chat.id, sent_msg.message_id, disable_notification=True)
        logger.info(f"Mini App закреплено в чате {message.chat.id}")
    except Exception as e:
        logger.error(f"Не удалось закрепить сообщение: {e}")

# --------------------
# /start
# --------------------
@router.message(F.text & F.text.startswith("/start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я AI бот-помощник.\n\n"
        "📝 Напиши мне любой вопрос, и я отвечу!\n"
        "🚀 Или используй /mini_app для открытия Mini App"
    )

# --------------------
# Обработка обычных сообщений с RAG
# --------------------
@router.message(F.text & ~F.text.startswith("/"))
async def handle_chat_message(message: types.Message):
    user_msg = message.text

    try:
        # Отправляем "печатаю..."
        typing_msg = await message.answer("⏳ Печатаю...")

        # Получаем контекст из RAG
        context = await rag.get_relevant_context(user_msg)

        # Формируем финальный ответ через AI21 + RAG
        messages = [{"role": "user", "content": user_msg}, {"role": "system", "content": context}]
        answer = await ask_ai21_with_rag(messages, user_id=str(message.from_user.id))

        # Удаляем сообщение "печатаю..."
        await typing_msg.delete()

        # Отправляем ответ
        await message.answer(answer)

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке запроса. Попробуйте позже.")

# --------------------
# HTTP endpoint для Mini App
# --------------------
async def handle_mini_app_request(request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        user_msg = data.get("text", "")
        request_id = data.get("request_id")

        logger.info(f"📱 Mini App запрос от {user_id}: {user_msg[:50]}")

        if not user_msg:
            return web.json_response({"success": False, "error": "Missing text"}, status=400)

        # Получаем контекст через RAG
        context = await rag.get_relevant_context(user_msg)

        # Генерируем ответ через AI
        messages = [{"role": "user", "content": user_msg}, {"role": "system", "content": context}]
        answer = await ask_ai21_with_rag(messages, user_id=str(user_id))

        logger.info(f"✅ Ответ для {user_id} сформирован")
        return web.json_response({"success": True, "answer": answer, "request_id": request_id})

    except Exception as e:
        logger.error(f"❌ Ошибка Mini App: {e}", exc_info=True)
        return web.json_response({"success": False, "error": str(e)}, status=500)

# --------------------
# Настройка web routes
# --------------------
def setup_web_routes(app):
    app.router.add_post('/api/chat', handle_mini_app_request)

    # CORS middleware
    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == 'OPTIONS':
            return web.Response(headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Max-Age': '86400'
            })
        try:
            resp = await handler(request)
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return resp
        except web.HTTPException as e:
            e.headers['Access-Control-Allow-Origin'] = '*'
            raise
        except Exception as e:
            logger.error(f"Unexpected error in CORS middleware: {e}", exc_info=True)
            return web.json_response({"error": "Internal server error"}, status=500, headers={'Access-Control-Allow-Origin': '*'})

    app.middlewares.append(cors_middleware)

    logger.info("✅ Web routes настроены: /api/chat, /health, /")
