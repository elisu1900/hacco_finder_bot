import asyncio
import logging

from telethon import TelegramClient

from config import BOT_TOKEN, API_ID, API_HASH, SESSION_NAME
from database.db import init_db
from bot.handlers import build_application
from monitor.collector import run_monitor

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _run_bot(telethon_client: TelegramClient) -> None:
    app = build_application(BOT_TOKEN)
    app.bot_data["telethon_client"] = telethon_client

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Bot is running.")
        # Block forever — cancelled only when the process exits
        await asyncio.get_running_loop().create_future()


async def main() -> None:
    logger.info("Initializing database...")
    await init_db()

    # Create and start a single shared Telethon client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    logger.info("Telethon client connected.")

    # Run bot and monitor concurrently
    await asyncio.gather(
        _run_bot(client),
        run_monitor(client),
    )


if __name__ == "__main__":
    asyncio.run(main())
