import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import ADMIN_USER_IDS
import secrets

from database.db import (
    search_products_by_brand,
    add_channel,
    remove_channel,
    get_channels,
    add_allowed_user,
    remove_allowed_user,
    is_allowed_user,
    get_allowed_users,
    create_invite_code,
    use_invite_code,
)
from monitor.collector import fetch_channel_history

logger = logging.getLogger(__name__)

# Conversation states
WAIT_BRAND = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


async def _can_use_bot(user_id: int) -> bool:
    if user_id in ADMIN_USER_IDS:
        return True
    return await is_allowed_user(user_id)


def _format_product(product) -> str:
    lines = [f"*{product.title}*"]
    if product.description:
        lines.append(product.description[:200])
    lines.append(f"[Telegram post]({product.telegram_post_link})")
    if product.external_product_link:
        lines.append(f"[Product link]({product.external_product_link})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# User conversation handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user

    # Handle invite code: /start <code>
    if context.args:
        code = context.args[0]
        if await is_allowed_user(user.id) or _is_admin(user.id):
            await update.message.reply_text("You already have access.")
        else:
            registered = await use_invite_code(code, user.id, user.username)
            if registered:
                await update.message.reply_text("Access granted! Send me a brand name to start searching.")
                return WAIT_BRAND
            else:
                await update.message.reply_text("Invalid or already used invite link.")
        return ConversationHandler.END

    if not await _can_use_bot(user.id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome! Send me a brand name to search for clothing deals.\n"
        "Example: *Nike*, *Adidas*, *Zara*...",
        parse_mode="Markdown",
    )
    return WAIT_BRAND


async def receive_brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _can_use_bot(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return ConversationHandler.END

    brand = update.message.text.strip()
    products = await search_products_by_brand(brand, limit=10)

    if not products:
        await update.message.reply_text(
            f"No results found for *{brand}* in the last 3 months.",
            parse_mode="Markdown",
        )
        return WAIT_BRAND

    await update.message.reply_text(f"Found {len(products)} deal(s) for *{brand}*:", parse_mode="Markdown")
    for product in products:
        await update.message.reply_text(
            _format_product(product),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    return WAIT_BRAND


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Search cancelled.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Admin commands
# ---------------------------------------------------------------------------

async def cmd_addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addchannel @username")
        return

    username = context.args[0]
    if not username.startswith("@"):
        username = f"@{username}"

    added = await add_channel(username)
    if added:
        await update.message.reply_text(f"Channel {username} added to monitoring.")
    else:
        await update.message.reply_text(f"Channel {username} is already being monitored.")


async def cmd_removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /removechannel @username")
        return

    username = context.args[0]
    if not username.startswith("@"):
        username = f"@{username}"

    removed = await remove_channel(username)
    if removed:
        await update.message.reply_text(f"Channel {username} removed from monitoring.")
    else:
        await update.message.reply_text(f"Channel {username} was not found in the monitored list.")


async def cmd_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    channels = await get_channels()
    if not channels:
        await update.message.reply_text("No channels are currently being monitored.")
        return

    lines = [f"• {ch.channel_username}" for ch in channels]
    await update.message.reply_text("Monitored channels:\n" + "\n".join(lines))


async def cmd_gencode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    code = secrets.token_urlsafe(16)
    await create_invite_code(code)
    bot_username = (await context.bot.get_me()).username
    await update.message.reply_text(
        f"Invite link (one-time use):\nhttps://t.me/{bot_username}?start={code}"
    )


async def cmd_adduser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /adduser <user_id>")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("User ID must be a number.")
        return

    added = await add_allowed_user(user_id, username=None)
    if added:
        await update.message.reply_text(f"User {user_id} added.")
    else:
        await update.message.reply_text(f"User {user_id} is already allowed.")


async def cmd_removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /removeuser <user_id>")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("User ID must be a number.")
        return

    removed = await remove_allowed_user(user_id)
    if removed:
        await update.message.reply_text(f"User {user_id} removed.")
    else:
        await update.message.reply_text(f"User {user_id} not found.")


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    users = await get_allowed_users()
    if not users:
        await update.message.reply_text("No users registered.")
        return

    lines = [f"• {u.user_id}" + (f" (@{u.username})" if u.username else "") for u in users]
    await update.message.reply_text("Allowed users:\n" + "\n".join(lines))


async def cmd_reindex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    channels = await get_channels()
    if not channels:
        await update.message.reply_text("No channels to reindex.")
        return

    await update.message.reply_text(f"Re-indexing {len(channels)} channel(s)... this may take a moment.")

    telethon_client = context.bot_data.get("telethon_client")
    if telethon_client is None:
        await update.message.reply_text("Monitor client is not available.")
        return

    for ch in channels:
        await fetch_channel_history(telethon_client, ch.channel_username)

    await update.message.reply_text("Re-index complete.")


# ---------------------------------------------------------------------------
# Application builder
# ---------------------------------------------------------------------------

def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()

    conversation = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_brand),
        ],
        states={
            WAIT_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_brand)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    app.add_handler(conversation)
    app.add_handler(CommandHandler("addchannel", cmd_addchannel))
    app.add_handler(CommandHandler("removechannel", cmd_removechannel))
    app.add_handler(CommandHandler("channels", cmd_channels))
    app.add_handler(CommandHandler("reindex", cmd_reindex))
    app.add_handler(CommandHandler("gencode", cmd_gencode))
    app.add_handler(CommandHandler("adduser", cmd_adduser))
    app.add_handler(CommandHandler("removeuser", cmd_removeuser))
    app.add_handler(CommandHandler("users", cmd_users))

    return app
