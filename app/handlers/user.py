from aiogram import Router, types, F
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
import json
import logging
from API.ai_21 import ask_ai21_with_rag
from aiohttp import web
import asyncio

logger = logging.getLogger(__name__)
router = Router()

# Словарь для хранения ожидающих запросов из Mini App
pending_requests = {}

# Кнопка для открытия Mini App через inline
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
        
        if not user_msg or not user_id:
            return web.json_response({"error": "Missing parameters"}, status=400)
        
        messages = [{"role": "user", "content": user_msg}]
        
        # Получаем ответ от AI
        answer = await ask_ai21_with_rag(messages, user_id=str(user_id))
        
        return web.json_response({
            "success": True,
            "answer": answer,
            "request_id": request_id
        })
        
    except Exception as e:
        logger.error(f"Ошибка обработки запроса Mini App: {e}")
        return web.json_response({"error": str(e)}, status=500)

# Функция для настройки веб-сервера (вызывается в main.py)
def setup_web_routes(app):
    app.router.add_post('/api/chat', handle_mini_app_request)
    # Добавляем CORS headers
    async def cors_middleware(app, handler):
        async def middleware(request):
            if request.method == 'OPTIONS':
                return web.Response(
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    }
                )
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        return middleware
    app.middlewares.append(cors_middleware)