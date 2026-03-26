import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
API_ID: int = int(os.environ["API_ID"])
API_HASH: str = os.environ["API_HASH"]

ADMIN_USER_IDS: list[int] = [
    int(uid.strip())
    for uid in os.getenv("ADMIN_USER_IDS", "").split(",")
    if uid.strip()
]

DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/bot.db")
SESSION_NAME: str = os.getenv("SESSION_NAME", "monitor_session")
