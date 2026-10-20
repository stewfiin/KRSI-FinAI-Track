from enum import Enum


class WalletType(str, Enum):
    CASH = "cash"
    BANK = "bank"
    EWALLET = "ewallet"


class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class TransactionSource(str, Enum):
    MANUAL_WEB = "manual_web"
    AI_CHAT = "ai_chat"
    AI_VOICE = "ai_voice"
    TELEGRAM_BOT = "telegram_bot"


class ChatPlatform(str, Enum):
    WEB = "web"
    TELEGRAM = "telegram"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

