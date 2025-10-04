from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import logging
from services.rag_system import RAGSystem
from API.ai_21 import ask_ai21_with_rag
from aiohttp import web, ClientSession

logger = logging.getLogger(__name__)
router = Router()
rag_system = RAGSystem()

API_URL = "https://ai-sber.onrender.com/api/chat"  # ваш endpoint Mini App / API

# --- /mini_app ---
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

# --- /start ---
@router.message(F.text & F.text.startswith("/start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я AI бот-помощник.\n\n"
        "📝 Напиши мне любой вопрос, и я отвечу!\n"
        "🚀 Или используй /mini_app для открытия Mini App"
    )

# --- обычный чат с POST к API для пробуждения сервера ---
@router.message(F.text & ~F.text.startswith("/"))
async def handle_user_chat(message: types.Message):
    logger.info(f"Получено сообщение от {message.from_user.id}: {message.text}")
    
    # Отправляем "печатает..."
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    # POST к Mini App API
    async with ClientSession() as session:
        try:
            async with session.post(API_URL, json={"user_id": message.from_user.id, "text": message.text}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    answer = data.get("answer", "❌ Бот не смог обработать запрос.")
                else:
                    logger.warning(f"API вернул статус {resp.status}")
                    answer = "❌ Ошибка API. Попробуйте позже."
        except Exception as e:
            logger.error(f"Ошибка при POST к API: {e}")
            answer = "❌ Не удалось соединиться с сервером."

    await message.answer(answer)

# --- Mini App endpoint ---
async def handle_mini_app_request(request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        user_msg = data.get("text", "")
        request_id = data.get("request_id")

        if not user_msg:
            return web.json_response({"success": False, "error": "Missing text parameter"}, status=400)

        context = await rag_system.get_relevant_context(user_msg)
        messages = [{"role": "user", "content": f"{user_msg}\n\nКонтекст:\n{context}"}]
        answer = await ask_ai21_with_rag(messages, user_id=str(user_id))

        return web.json_response({
            "success": True,
            "answer": answer,
            "request_id": request_id
        })
    except Exception as e:
        logger.exception("Ошибка обработки запроса Mini App")
        return web.json_response({"success": False, "error": str(e)}, status=500)

def setup_web_routes(app):
    app.router.add_post('/api/chat', handle_mini_app_request)

    async def health_check(request):
        return web.json_response({"status": "ok"})

    app.router.add_get('/health', health_check)

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
    logger.info("✅ Web routes настроены: /api/chat, /health")
