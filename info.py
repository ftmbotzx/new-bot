import os

SESSION = "spotifydl"
API_ID = int(os.getenv("API_ID", "8012239"))
API_HASH = os.getenv("API_HASH", "171e6f1bf66ed8dcc5140fbe827b6b08")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1002284232975"))
DUMP_CHANNEL_ID = int(os.getenv("DUMP_CHANNEL_ID", "-1002702417507"))

FAILD_CHAT_ID = int(os.getenv("FAILD_CHAT_ID", "-1002590983675"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "media")
PORT = int(os.getenv("PORT", "8080"))
FORCE_CHANNEL = int(os.getenv("FORCE_CHANNEL", "-1002379643238"))
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ftmbotzx:ftmbotzx@cluster0.0b8imks.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

MONGO_NAME = os.getenv("MONGO_NAME", "SpotifyDL")
ADMINS = [5660839376, 6167872503, 5961011848, 6538627123]
DAILY_LIMITS = 20
MAINTENANCE_MODE = False  # Change to False to disable maintenance mode
USER_SESSION = "BQB6Qc8APy91zoBtQGv-O19FCUpBvrwkiwXohHi5nolHHv04HduDe6oKPaDRNvIiBfCcURe2SQYTO4oj-qWP-Cqpd5Bbq70xnIxiZsLS4-Al4fQxhl3mI59CUKxwIg0Iure6-BkkyXm7A-oLeatLz5UR7RcGBt6QdIdElHOS6cxR8DoJIwqtFfWqb9szJjsYLD-r66wMF8IrGA4aC0lcXybyf8OS5wRGNqnuq-LcvheIcy_HVSIJtDIJLsLyOsAjGlJLItKPDr_m88keBSrTDMgZEOIKqPSJoPfiqjOwYrrhC_imty5T7SUmAiFbIcP8KOxDJj0yW7e2DVUrxyg-kG3GboCDOgAAAAFY13jAAA"
USERBOT_CHAT_ID = 5785483456
OWNER_ID = 7744665378


MAINTENANCE_MESSAGE = (
    "⚠️ **Maintenance Mode Activated** ⚙️\n\n"
    "Our bot is currently undergoing scheduled maintenance to improve performance and add new features.\n\n"
    "Please check back in a while. We’ll be back soon, better than ever!\n\n"
    "💬 **Support Group:** [SUPPORT](https://t.me/AnSBotsSupports)\n\n"
    "**– Team Supportzx**"
)
