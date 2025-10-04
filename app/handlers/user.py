from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import logging
from services.rag_system import RAGSystem  # твоя RAG система
from API.ai_21 import ask_ai21_with_rag
from aiohttp import web
import asyncio

logger = logging.getLogger(__name__)
router = Router()
rag_system = RAGSystem()

# Кнопка для открытия Mini App
@router.message(F.text & F.text.startswith("/mini_app"))
async def send_mini_app_inline(message: types.Message):
    web_app = WebAppInfo(url="https://ai-mini-app.wuaze.com")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть Mini App", web_app=web_app)]
    ])
    await message.answer(
        "Нажми кнопку ниже, чтобы открыть мини-приложение:",
        reply_markup=keyboard
    )

# /start
@router.message(F.text & F.text.startswith("/start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я AI бот-помощник.\n\n"
        "📝 Напиши мне любой вопрос, и я отвечу!\n"
        "🚀 Или используй /mini_app для открытия Mini App"
    )

# Чат в Telegram с индикатором "печатает..."
@router.message(F.text & ~F.text.startswith("/"))
async def handle_chat_message(message: types.Message):
    user_msg = message.text
    user_id = str(message.from_user.id)

    try:
        # 1. Отправляем typing
        await message.bot.send_chat_action(message.chat.id, "typing")

        # 2. Получаем релевантный контекст через RAG
        context = await rag_system.get_relevant_context(user_msg)

        # 3. Формируем сообщения для AI с контекстом
        messages = [
            {"role": "user", "content": f"{user_msg}\n\nКонтекст:\n{context}"}
        ]

        # 4. Генерируем ответ через AI21
        answer = await ask_ai21_with_rag(messages, user_id=user_id)

        # 5. Отправляем ответ пользователю
        await message.answer(answer)

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await message.answer("Произошла ошибка при обработке запроса. Попробуйте позже.")

# HTTP endpoint для Mini App
async def handle_mini_app_request(request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        user_msg = data.get("text", "")
        request_id = data.get("request_id")
        
        if not user_msg:
            return web.json_response({"success": False, "error": "Missing text parameter"}, status=400)

        # RAG контекст
        context = await rag_system.get_relevant_context(user_msg)
        messages = [{"role": "user", "content": f"{user_msg}\n\nКонтекст:\n{context}"}]

        # Получаем ответ AI
        answer = await ask_ai21_with_rag(messages, user_id=str(user_id))

        return web.json_response({
            "success": True,
            "answer": answer,
            "request_id": request_id
        })

    except Exception as e:
        logger.exception("Ошибка обработки запроса Mini App")
        return web.json_response({"success": False, "error": str(e)}, status=500)

# Настройка веб-маршрутов
def setup_web_routes(app):
    app.router.add_post('/api/chat', handle_mini_app_request)

    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == 'OPTIONS':
            return web.Response(headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Max-Age': '86400'
            })
        resp = await handler(request)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

    app.middlewares.append(cors_middleware)
    logger.info("✅ Web routes настроены: /api/chat, /health, /")
