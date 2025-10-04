from aiogram import Router, types, F
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
import json
import logging
from API.ai_21 import ask_ai21_with_rag
from aiohttp import web

logger = logging.getLogger(__name__)
router = Router()

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

# Обработка команды /start
@router.message(F.text & F.text.startswith("/start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я AI бот-помощник.\n\n"
        "📝 Напиши мне любой вопрос, и я отвечу!\n"
        "🚀 Или используй /mini_app для открытия Mini App"
    )

# Обработка обычных сообщений в Telegram чате
@router.message(F.text & ~F.text.startswith("/"))
async def handle_chat_message(message: types.Message):
    try:
        user_msg = message.text
        messages = [{"role": "user", "content": user_msg}]
        
        # Отправляем индикатор "печатает..."
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Получаем ответ от AI
        answer = await ask_ai21_with_rag(messages, user_id=str(message.from_user.id))
        
        # Отправляем ответ в чат
        await message.answer(answer)
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await message.answer("Произошла ошибка при обработке запроса. Попробуйте позже.")

# HTTP endpoint для получения запросов из Mini App
async def handle_mini_app_request(request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        user_msg = data.get("text", "")
        request_id = data.get("request_id")
        
        logger.info(f"📱 Получен запрос из Mini App от {user_id}: {user_msg[:50]}...")
        
        if not user_msg:
            return web.json_response(
                {"success": False, "error": "Missing text parameter"}, 
                status=400
            )
        
        messages = [{"role": "user", "content": user_msg}]
        
        # Получаем ответ от AI
        answer = await ask_ai21_with_rag(messages, user_id=str(user_id))
        
        logger.info(f"✅ Ответ для {user_id} отправлен: {answer[:50]}...")
        
        return web.json_response({
            "success": True,
            "answer": answer,
            "request_id": request_id
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки запроса Mini App: {e}", exc_info=True)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)

# Функция для настройки веб-сервера
def setup_web_routes(app):
    """Настройка API endpoints для Mini App"""
    
    # Добавляем endpoint для чата
    app.router.add_post('/api/chat', handle_mini_app_request)
    
    # CORS middleware для работы с Mini App
    @web.middleware
    async def cors_middleware(request, handler):
        # Обработка preflight запросов
        if request.method == 'OPTIONS':
            return web.Response(
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Max-Age': '86400'
                }
            )
        
        # Обработка обычных запросов
        try:
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        except web.HTTPException as e:
            # Это нормальные HTTP исключения (404, 405 и т.д.)
            e.headers['Access-Control-Allow-Origin'] = '*'
            raise
        except Exception as e:
            logger.error(f"Unexpected error in CORS middleware: {e}", exc_info=True)
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500,
                headers={'Access-Control-Allow-Origin': '*'}
            )
    
    # Добавляем middleware
    app.middlewares.append(cors_middleware)
    
    # Логирование всех запросов
    @web.middleware
    async def logging_middleware(request, handler):
        logger.info(f"📨 {request.method} {request.path} from {request.remote}")
        try:
            response = await handler(request)
            logger.info(f"✅ {request.method} {request.path} -> {response.status}")
            return response
        except Exception as e:
            logger.error(f"❌ {request.method} {request.path} -> Error: {e}")
            raise
    
    app.middlewares.insert(0, logging_middleware)
    
    logger.info("✅ Web routes настроены:")
    logger.info("   📡 POST /api/chat - Mini App API")
    logger.info("   🔧 GET /health - Health check")
    logger.info("   🏠 GET / - Root endpoint")
