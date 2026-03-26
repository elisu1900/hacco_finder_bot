import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import ADMIN_USER_IDS
from database.db import (
    search_products,
    get_categories_for_brand,
    get_colors_for_brand_category,
    add_channel,
    remove_channel,
    get_channels,
)
from monitor.collector import fetch_channel_history

logger = logging.getLogger(__name__)

# Conversation states
WAIT_BRAND, WAIT_CATEGORY, WAIT_COLOR = range(3)

# Callback data prefixes
CAT_PREFIX = "cat:"
COL_PREFIX = "col:"
CANCEL_CB = "cancel"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


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
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome! Send me a brand name to search for clothing deals.\n"
        "Example: *Nike*, *Adidas*, *Zara*...",
        parse_mode="Markdown",
    )
    return WAIT_BRAND


async def receive_brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return ConversationHandler.END

    brand = update.message.text.strip()
    context.user_data["brand"] = brand

    categories = await get_categories_for_brand(brand)
    if not categories:
        await update.message.reply_text(
            f"No results found for *{brand}*. Try another brand.",
            parse_mode="Markdown",
        )
        return WAIT_BRAND

    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f"{CAT_PREFIX}{cat}")]
        for cat in categories
    ]
    keyboard.append([InlineKeyboardButton("Cancel", callback_data=CANCEL_CB)])
    await update.message.reply_text(
        f"Found categories for *{brand}*. Pick one:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return WAIT_CATEGORY


async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == CANCEL_CB:
        await query.edit_message_text("Search cancelled.")
        return ConversationHandler.END

    category = query.data.removeprefix(CAT_PREFIX)
    context.user_data["category"] = category
    brand = context.user_data["brand"]

    colors = await get_colors_for_brand_category(brand, category)
    if not colors:
        await query.edit_message_text(
            f"No results found for this combination. Try another filter."
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(col, callback_data=f"{COL_PREFIX}{col}")]
        for col in colors
    ]
    keyboard.append([InlineKeyboardButton("Cancel", callback_data=CANCEL_CB)])
    await query.edit_message_text(
        f"Pick a color for *{brand}* / *{category}*:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return WAIT_COLOR


async def receive_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == CANCEL_CB:
        await query.edit_message_text("Search cancelled.")
        return ConversationHandler.END

    color = query.data.removeprefix(COL_PREFIX)
    brand = context.user_data["brand"]
    category = context.user_data["category"]

    products = await search_products(brand, category, color)
    if not products:
        await query.edit_message_text(
            "No results found for this combination. Try another filter."
        )
        return ConversationHandler.END

    await query.edit_message_text(f"Found {len(products)} deal(s):")

    for product in products[:10]:  # cap at 10 results per search
        await query.message.reply_text(
            _format_product(product),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

    return ConversationHandler.END


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
            WAIT_CATEGORY: [CallbackQueryHandler(receive_category)],
            WAIT_COLOR: [CallbackQueryHandler(receive_color)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    app.add_handler(conversation)
    app.add_handler(CommandHandler("addchannel", cmd_addchannel))
    app.add_handler(CommandHandler("removechannel", cmd_removechannel))
    app.add_handler(CommandHandler("channels", cmd_channels))
    app.add_handler(CommandHandler("reindex", cmd_reindex))

    return app
