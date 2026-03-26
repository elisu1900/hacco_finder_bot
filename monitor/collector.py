import logging
from telethon import TelegramClient, events
from telethon.tl.types import Message

from config import API_ID, API_HASH, SESSION_NAME
from database.db import add_product, get_channels
from monitor.parser import parse_post

logger = logging.getLogger(__name__)


def _build_post_link(channel_username: str, message_id: int) -> str:
    username = channel_username.lstrip("@")
    return f"https://t.me/{username}/{message_id}"


async def _process_message(message: Message, channel_username: str) -> None:
    text = message.text or message.message or ""
    if not text.strip():
        return

    parsed = parse_post(text)
    post_link = _build_post_link(channel_username, message.id)

    inserted = await add_product(
        brand=parsed.brand,
        category=parsed.category,
        color=parsed.color,
        title=parsed.title,
        description=parsed.description,
        telegram_post_link=post_link,
        external_product_link=parsed.external_link,
        channel_id=channel_username,
        message_id=message.id,
    )
    if inserted:
        logger.info("Indexed post: %s", post_link)


async def fetch_channel_history(client: TelegramClient, channel_username: str, limit: int = 200) -> None:
    logger.info("Fetching history for %s (limit=%d)", channel_username, limit)
    try:
        async for message in client.iter_messages(channel_username, limit=limit):
            if isinstance(message, Message):
                await _process_message(message, channel_username)
    except Exception as exc:
        logger.error("Error fetching history for %s: %s", channel_username, exc)


async def run_monitor(client: TelegramClient | None = None) -> None:
    """Start the Telethon monitor.

    If *client* is provided (already started), it will be reused.
    Otherwise a new client is created and started here.
    """
    owns_client = client is None
    if owns_client:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.start()
        logger.info("Telethon monitor started (own client).")

    # Fetch history for all currently monitored channels
    channels = await get_channels()
    for ch in channels:
        await fetch_channel_history(client, ch.channel_username)

    @client.on(events.NewMessage)
    async def _on_new_message(event: events.NewMessage.Event) -> None:
        try:
            chat = await event.get_chat()
            username = getattr(chat, "username", None)
            if username is None:
                return
            channel_username = f"@{username}"

            monitored = await get_channels()
            monitored_usernames = {ch.channel_username.lower() for ch in monitored}
            if channel_username.lower() not in monitored_usernames:
                return

            message: Message = event.message
            await _process_message(message, channel_username)
        except Exception as exc:
            logger.error("Error handling new message: %s", exc)

    logger.info("Monitor listening for new posts...")
    await client.run_until_disconnected()
