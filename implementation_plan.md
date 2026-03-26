# Telegram Clothing Deals Bot

A Python-based Telegram bot that helps users find clothing deals by filtering brand → category → color, returning links to original Telegram channel posts.

## User Review Required

> [!IMPORTANT]
> **Two Telegram API credentials are needed:**
> 1. **Bot Token** (from @BotFather) — for the user-facing bot
> 2. **Telegram API ID + API Hash** (from https://my.telegram.org) — for the channel monitor (Telethon client) that reads messages from channels
>
> You'll need to provide these values in a `.env` file before running.

> [!WARNING]
> The channel monitor uses a **Telethon user session** (not a bot). This means it logs in as your personal Telegram account to read channel messages. On first run, you'll be asked to enter a phone number and verification code.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐
│  User (Telegram) │────▶│  Bot (PTB v22)   │
│  /start, brands  │◀────│  Inline Keyboards│
└─────────────────┘     └────────┬─────────┘
                                 │ queries
                        ┌────────▼─────────┐
                        │   SQLite DB      │
                        │   (products)     │
                        └────────▲─────────┘
                                 │ inserts
                        ┌────────┴─────────┐
                        │ Channel Monitor  │
                        │ (Telethon)       │
                        └──────────────────┘
```

**Two processes run concurrently:**
1. **Bot process** — handles user interactions via `python-telegram-bot`
2. **Monitor process** — watches Telegram channels via Telethon, parses posts, stores in DB

---

## Proposed Changes

### Project Structure

```
hacoo_bot/
├── .env.example          # Template for credentials
├── requirements.txt      # Dependencies
├── main.py               # Entry point — runs bot + monitor
├── config.py             # Loads .env, constants
├── database/
│   ├── __init__.py
│   ├── models.py         # SQLAlchemy models (Product, MonitoredChannel)
│   └── db.py             # Session factory, init_db()
├── bot/
│   ├── __init__.py
│   └── handlers.py       # ConversationHandler, callbacks, admin commands
├── monitor/
│   ├── __init__.py
│   ├── collector.py      # Telethon channel listener
│   └── parser.py         # Extract brand/category/color from text
└── data/
    └── bot.db            # SQLite database (auto-created)
```

---

### Dependencies

#### [NEW] [requirements.txt](file:///c:/Users/Elias/Desktop/hacoo_bot/requirements.txt)

| Package | Purpose |
|---------|---------|
| `python-telegram-bot[ext]~=22.7` | Bot API, ConversationHandler, InlineKeyboards |
| `telethon~=1.37` | Read messages from Telegram channels (user API) |
| `sqlalchemy~=2.0` | ORM for SQLite database |
| `aiosqlite~=0.20` | Async SQLite driver |
| `python-dotenv~=1.0` | Load `.env` config |

---

### Configuration

#### [NEW] [.env.example](file:///c:/Users/Elias/Desktop/hacoo_bot/.env.example)

Template with placeholders for:
- `BOT_TOKEN` — from @BotFather
- `API_ID` / `API_HASH` — from my.telegram.org (for Telethon)
- `ADMIN_USER_IDS` — comma-separated Telegram user IDs for admin access

#### [NEW] [config.py](file:///c:/Users/Elias/Desktop/hacoo_bot/config.py)

Loads `.env` and exposes configuration constants.

---

### Database Layer

#### [NEW] [database/models.py](file:///c:/Users/Elias/Desktop/hacoo_bot/database/models.py)

**Product** table:
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto-increment |
| brand | String | e.g. "Nike" |
| category | String | e.g. "Hoodies" |
| color | String | e.g. "Blue" |
| title | String | Product title |
| description | Text | Short description |
| telegram_post_link | String (unique) | `https://t.me/channel/postid` |
| external_product_link | String (nullable) | Store/Hacoo link |
| channel_id | String | Source channel |
| message_id | Integer | Telegram message ID |
| created_at | DateTime | Timestamp |

**MonitoredChannel** table:
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto-increment |
| channel_username | String (unique) | e.g. `@deals_channel` |
| added_at | DateTime | When added |

#### [NEW] [database/db.py](file:///c:/Users/Elias/Desktop/hacoo_bot/database/db.py)

- `init_db()` — creates tables
- `get_session()` — returns SQLAlchemy session
- Query helpers: `search_products(brand, category, color)`, `add_product(...)`, `add_channel(...)`, `remove_channel(...)`, `get_channels()`

---

### Channel Monitor

#### [NEW] [monitor/parser.py](file:///c:/Users/Elias/Desktop/hacoo_bot/monitor/parser.py)

Keyword-based classifier that extracts:
- **Brand**: matches against a predefined list (Nike, Adidas, Puma, etc.)
- **Category**: matches keywords (hoodie→Hoodies, sneaker/shoe→Shoes, etc.)
- **Color**: matches color words
- **External link**: extracts URLs from message text

#### [NEW] [monitor/collector.py](file:///c:/Users/Elias/Desktop/hacoo_bot/monitor/collector.py)

- Connects via Telethon as a user client
- On startup: fetches recent message history from all monitored channels
- Listens for new messages in monitored channels via event handler
- Parses each message → inserts into DB (skips duplicates by `telegram_post_link`)

---

### Bot Handlers

#### [NEW] [bot/handlers.py](file:///c:/Users/Elias/Desktop/hacoo_bot/bot/handlers.py)

**User Flow** (ConversationHandler):
1. `/start` → Welcome message + "Type a brand name to search"
2. User types brand → Bot queries DB for available categories for that brand → shows inline keyboard
3. User taps category → Bot queries DB for available colors → shows inline keyboard
4. User taps color → Bot searches DB → returns formatted results or "No results" message

**Admin Commands** (restricted to `ADMIN_USER_IDS`):
- `/addchannel @username` — adds a channel to monitor
- `/removechannel @username` — removes a channel
- `/channels` — lists monitored channels
- `/reindex` — triggers a re-fetch of recent posts from all channels

---

### Entry Point

#### [NEW] [main.py](file:///c:/Users/Elias/Desktop/hacoo_bot/main.py)

- Initializes database
- Starts Telethon monitor in a background thread/task
- Starts the bot (polling mode)
- Both run concurrently in the same process using `asyncio`

---

## Verification Plan

### Automated Tests

Since this is an integration-heavy project (Telegram APIs), automated unit tests have limited value. Instead, verification will focus on runtime checks.

**Startup verification:**
```bash
cd c:\Users\Elias\Desktop\hacoo_bot
pip install -r requirements.txt
python main.py
```
- Verify no import errors or crash on startup
- Verify `data/bot.db` is created with correct schema

### Manual Verification

> [!NOTE]
> These steps require valid Telegram credentials in `.env`.

1. **Bot conversation flow:**
   - Open the bot in Telegram → send `/start`
   - Type a brand name (e.g., "nike")
   - Verify category buttons appear
   - Tap a category → verify color buttons appear
   - Tap a color → verify results are shown (or "no results" message)

2. **Admin commands:**
   - Send `/addchannel @somechannel` → verify confirmation
   - Send `/channels` → verify channel listed
   - Send `/removechannel @somechannel` → verify removal

3. **Channel monitoring:**
   - Add a test channel with `/addchannel`
   - Post a deal message in that channel
   - Verify the message appears in search results after a moment

> [!TIP]
> For initial testing without real channels, you can manually add test product data to the database using a provided seed script, or I can include a `/seedtest` admin command.
