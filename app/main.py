# main.py
import os
import logging
import asyncio
from aiohttp import web, ClientSession
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from handlers import user
from handlers.user import setup_web_routes
from utils.logger import setup_logger

logger = setup_logger()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://ai-sber.onrender.com")
WEBHOOK_PATH = "/webhook/bot"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT") or 8080)


PING_INTERVAL = 240  # каждые 4 минуты

async def on_startup(bot: Bot):
    info = await bot.get_webhook_info()
    logger.info(f"Webhook info: {info}")
    if info.url != WEBHOOK_URL:
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "web_app_data"]
        )
        logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}")
    else:
        logger.info(f"ℹ️ Webhook уже установлен")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("🛑 Webhook удален, бот остановлен")

async def self_ping(app: web.Application):
    """Фоновая задача для пинга самого себя каждые PING_INTERVAL секунд"""
    await asyncio.sleep(5)  # небольшая задержка после старта
    url = f"{WEBHOOK_HOST}/health"
    session = ClientSession()
    try:
        while True:
            try:
                async with session.get(url) as resp:
                    logger.info(f"Self-ping {url}: {resp.status}")
            except Exception as e:
                logger.warning(f"Self-ping failed: {e}")
            await asyncio.sleep(PING_INTERVAL)
    finally:
        await session.close()

def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(user.router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)

    setup_web_routes(app)

    async def health_check(request):
        return web.json_response({"status": "ok", "webhook": WEBHOOK_URL})

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

    if not any(r.path == '/health' for r in app.router.routes()):
        app.router.add_get('/health', health_check)
    if not any(r.path == '/' for r in app.router.routes()):
        app.router.add_get('/', root_handler)

    # запуск автопинга
    app.on_startup.append(lambda app: asyncio.create_task(self_ping(app)))

    setup_application(app, dp, bot=bot)
    logger.info(f"🚀 Запуск бота на порту {PORT}")
    logger.info(f"📡 Webhook URL: {WEBHOOK_URL}")
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()

