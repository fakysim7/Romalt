import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from config import BOT_TOKEN
from handlers import user
from handlers.user import setup_web_routes
from utils.logger import setup_logger
import os

logger = setup_logger()

# Конфигурация webhook
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://your-domain.com")  # Замените на ваш домен
WEBHOOK_PATH = "/webhook/bot"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Для локальной разработки с ngrok используйте:
# WEBHOOK_HOST = "https://abc123.ngrok-free.app"

# Порт
PORT = int(os.getenv("PORT", 8080))

async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    # Устанавливаем webhook
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "web_app_data"]
        )
        logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}")
    else:
        logger.info(f"ℹ️ Webhook уже установлен: {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("🛑 Webhook удален, бот остановлен")

def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Подключаем роутеры
    dp.include_router(user.router)
    
    # Регистрируем startup и shutdown хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Создаем aiohttp приложение
    app = web.Application()
    
    # Настраиваем webhook handler для Telegram
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)
    
    # Добавляем роуты для Mini App API
    setup_web_routes(app)
    
    # Настраиваем приложение
    setup_application(app, dp, bot=bot)
    
    # Health check endpoint
    async def health_check(request):
        return web.json_response({
            "status": "ok", 
            "webhook": WEBHOOK_URL,
            "version": "1.0.0"
        })
    
    # Favicon handler (чтобы браузер не выдавал ошибки)
    async def favicon_handler(request):
        return web.Response(status=204)
    
    # Root endpoint
    async def root_handler(request):
        return web.json_response({
            "bot": "Telegram AI Bot",
            "status": "running",
            "endpoints": {
                "webhook": WEBHOOK_PATH,
                "api": "/api/chat",
                "health": "/health"
            }
        })
    
    app.router.add_get('/health', health_check)
    app.router.add_get('/favicon.ico', favicon_handler)
    app.router.add_get('/', root_handler)
    
    # Запускаем веб-сервер
    logger.info(f"🚀 Запуск бота на порту {PORT}")
    logger.info(f"📡 Webhook URL: {WEBHOOK_URL}")
    logger.info(f"🔧 API endpoint: http://0.0.0.0:{PORT}/api/chat")
    logger.info(f"❤️ Health check: http://0.0.0.0:{PORT}/health")
    
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
