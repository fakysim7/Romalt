import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import user
from utils.logger import setup_logger

logger = setup_logger()

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(user.router)

    logger.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
