# main.py
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import aiohttp_cors
import aiohttp
import asyncio

from handlers import user
from handlers.user import setup_web_routes
from utils.logger import setup_logger

logger = setup_logger()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://ai-sber.onrender.com")
WEBHOOK_PATH = "/webhook/bot"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT") or 8080)


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


# === Keep-alive задача ===
async def keep_alive(app):
    async def ping():
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.get(f"http://localhost:{PORT}/health")
                    logger.debug("✅ Keep-alive ping sent")
            except Exception as e:
                logger.error(f"Keep-alive failed: {e}")
            await asyncio.sleep(240)  # каждые 4 минуты
    app['keep_alive_task'] = asyncio.create_task(ping())

async def on_cleanup(app):
    task = app.get('keep_alive_task')
    if task:
        task.cancel()


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

    # ✅ CORS для Android WebApp
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)

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

    app.router.add_get('/health', health_check)
    app.router.add_get('/', root_handler)

    setup_application(app, dp, bot=bot)

    # === Добавляем keep-alive ===
    app.on_startup.append(keep_alive)
    app.on_cleanup.append(on_cleanup)

    logger.info(f"🚀 Запуск бота на порту {PORT}")
    logger.info(f"📡 Webhook URL: {WEBHOOK_URL}")
    web.run_app(app, host="0.0.0.0", port=PORT, print=None)


if __name__ == "__main__":
    main()
