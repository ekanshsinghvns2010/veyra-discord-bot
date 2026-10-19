
import os

# Veyra's prefix for all text commands
PREFIX = "!veyra"

# OpenRouter model configuration
DEFAULT_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-oss-120b"
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Brand identity
BOT_NAME = "Veyra"
BOT_STUDIO = "Volbasty Studios"

DEVELOPMENT_GUILD_ID = int(
    os.getenv("VEYRA_DEVELOPMENT_GUILD_ID", "0")
)

# AI response settings
MAX_TOKENS = 1200
TEMPERATURE = 0.7
