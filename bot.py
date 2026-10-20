
import os
import time
import traceback

import discord

from config import PREFIX
from channel_manager import (
    get_chat_channels,
    remove_guild_channels,
)
from ai_client import ask_veyra
from memory_manager import (
    get_user_memory,
    get_recent_history,
    add_message,
    set_preference,
    clear_user_memory,
)
from mode_manager import get_chat_mode, set_chat_mode

from commands.logs import handle_logs
from commands.code_pro import handle_code_pro
from commands.research import handle_ask_research
from commands.products import (
    handle_products,
    handle_product_command,
    handle_grant_pro,
    handle_ask_product,
    PRODUCTS,
)
from commands.ping import handle_ping
from commands.help import handle_help
from commands.setchannel import handle_setchannel
from commands.removechannel import handle_removechannel
from commands.memory import handle_memory

from commands.logging_service import (
    log_command,
    log_error,
    log_ai_request,
    log_memory_event,
    log_system_event,
)

from security.dev_commands import handle_dev_command

try:
    from commands.shop import handle_shop
except ImportError:
    handle_shop = None


# ==================================================
# CONFIGURATION
# ==================================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

COMMANDS_USED = 0
START_TIME = time.monotonic()
STARTUP_LOGGED = False


# ==================================================
# PERMISSIONS
# ==================================================

def is_admin(member, guild=None):
    """Check server owner, Administrator, or Manage Server."""

    if not isinstance(member, discord.Member):
        return False

    if guild is not None and member.guild.id != guild.id:
        return False

    permissions = member.guild_permissions

    return (
        member.id == member.guild.owner_id
        or permissions.administrator
        or permissions.manage_guild
    )


def is_server_manager(member, guild=None):
    """Compatibility wrapper for existing command handlers."""
    return is_admin(member, guild)


# ==================================================
# LOGGING HELPERS
# ==================================================

async def safe_log(log_function, *args, **kwargs):
    """Logging failures must never break normal bot commands."""

    try:
        await log_function(*args, **kwargs)
    except Exception as error:
        print(
            f"[LOGGING ERROR] {type(error).__name__}: "
            "logging operation failed."
        )


async def record_command(message, command_name, status="received"):
    """Record command metadata without storing message content."""

    if message.guild is None:
        return

    await safe_log(
        log_command,
        client,
        message.guild.id,
        message.author.id,
        command_name,
        status,
    )


async def record_error(message, location, error):
    """Log error metadata, not private content or tracebacks."""

    guild_id = message.guild.id if message.guild else 0

    print(
        f"[ERROR] location={location}; "
        f"type={type(error).__name__}; guild_id={guild_id}"
    )

    if guild_id:
        await safe_log(
            log_error,
            client,
            guild_id,
            location,
            type(error).__name__,
        )


# ==================================================
# GENERAL HELPERS
# ==================================================

def get_message_content(message):
    return (message.content or "").strip()


def is_command(content):
    return content.lower().startswith(PREFIX.lower())


async def safe_reply(message, content=None, **kwargs):
    """Reply without allowing a Discord send error to crash handling."""

    try:
        await message.reply(
            content or "",
            mention_author=False,
            **kwargs,
        )
    except Exception as error:
        print(f"[REPLY ERROR] {type(error).__name__}")


def looks_like_coding_request(content):
    text = content.lower()

    indicators = (
        "write code",
        "write a code",
        "python code",
        "javascript code",
        "html code",
        "coding",
        "debug this",
        "fix this code",
        "build an app",
        "make a website",
        "write a script",
        "program in python",
        "create a bot",
        "implement this function",
        "generate code",
        "code for",
    )

    return any(term in text for term in indicators)


async def send_coding_upgrade_embed(message):
    embed = discord.Embed(
        title="💻 Veyra Code",
        description=(
            "**Your next project deserves the right tools.**\n\n"
            "Choose the coding experience that fits your task."
        ),
        color=discord.Color.from_rgb(42, 164, 255),
    )

    embed.add_field(
        name="🆓 Code Free",
        value=(
            "For small coding questions, simple examples, "
            "and short snippets.\n"
            "**Target limit:** 30 generated code lines."
        ),
        inline=False,
    )

    embed.add_field(
        name="⚡ Code Pro",
        value=(
            "For larger projects, multi-file implementations, "
            "advanced debugging, and detailed code reviews."
        ),
        inline=False,
    )

    embed.add_field(
        name="🛍️ Explore the shop",
        value=f"Use `{PREFIX} shop` to explore Veyra's products.",
        inline=False,
    )

    embed.set_footer(
        text="VEYRA AI • Powered by Volbasty Studios"
    )

    await message.reply(embed=embed, mention_author=False)


async def send_long_reply(message, text):
    """Split replies into chunks below Discord's message limit."""

    text = str(text or "").strip()

    if not text:
        text = (
            "I couldn't generate a response just now. "
            "Please try again."
        )

    for start in range(0, len(text), 1900):
        chunk = text[start:start + 1900]

        if start == 0:
            await message.reply(
                chunk,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            await message.channel.send(
                chunk,
                allowed_mentions=discord.AllowedMentions.none(),
            )


def get_command_parts(content):
    """Parse !veyra <subcommand> [remaining arguments]."""

    parts = content.split(maxsplit=2)

    if not parts or parts[0].lower() != PREFIX.lower():
        return None, ""

    subcommand = parts[1].lower() if len(parts) >= 2 else ""
    arguments = parts[2] if len(parts) >= 3 else ""

    return subcommand, arguments


# ==================================================
# STARTUP
# ==================================================

@client.event
async def on_ready():
    global STARTUP_LOGGED

    print("=" * 48)
    print(f"[READY] Veyra AI connected as {client.user}")
    print(f"[READY] Bot ID: {client.user.id}")
    print(f"[READY] Prefix: {PREFIX}")
    print("[READY] Memory system: enabled")
    print("[READY] Channel configuration: file-backed")
    print("[READY] Logging command: loaded")
    print("[READY] Developer command router: loaded")
    print("[READY] Waiting for messages...")
    print("=" * 48)

    if not STARTUP_LOGGED:
        STARTUP_LOGGED = True

        for guild in client.guilds:
            await safe_log(
                log_system_event,
                client,
                guild.id,
                f"Veyra connected successfully. Bot ID: {client.user.id}",
            )


# ==================================================
# SERVER CLEANUP
# ==================================================

@client.event
async def on_guild_remove(guild):
    """Clean up saved chat-channel settings after leaving a server."""

    try:
        remove_guild_channels(guild.id)

        print(
            f"[GUILD] Removed chat-channel settings "
            f"for server {guild.id}"
        )

    except Exception as error:
        print(
            f"[GUILD ERROR] Cleanup failed: "
            f"{type(error).__name__}"
        )

    await safe_log(
        log_system_event,
        client,
        guild.id,
        "Veyra left a server; saved chat-channel settings were cleaned up.",
    )


# ==================================================
# MESSAGE HANDLER — PART 1
# ==================================================

@client.event
async def on_message(message):
    global COMMANDS_USED

    if message.author.bot:
        return

    content = get_message_content(message)

    if not content:
        return

    lowered = content.lower().strip()
    prefix = PREFIX.lower()

    try:
        # DEVELOPER-ONLY COMMANDS

        if is_command(content):
            handled = await handle_dev_command(
                message,
                client,
                PREFIX,
            )

            if handled:
                COMMANDS_USED += 1
                command_name = (
                    content.split()[1]
                    if len(content.split()) > 1
                    else "dev"
                )
                await record_command(
                    message,
                    command_name,
                    "handled",
                )
                return

        # PING

        if lowered == f"{prefix} ping":
            COMMANDS_USED += 1
            await record_command(message, "ping")

            await handle_ping(
                message,
                client,
                START_TIME,
                COMMANDS_USED,
            )
            return

        # HELP

        if lowered in (
            f"{prefix} help",
            f"{prefix} guide",
        ):
            COMMANDS_USED += 1
            await record_command(message, "help")
            await handle_help(message, PREFIX)
            return

        # LOGGING SETUP

        if lowered == f"{prefix} logs":
            COMMANDS_USED += 1
            await record_command(message, "logs")
            await handle_logs(message)
            return

        # MEMORY INFORMATION

        if lowered == f"{prefix} memory":
            COMMANDS_USED += 1
            await record_command(message, "memory")
            await handle_memory(message)
            return

        # CLEAR MEMORY

        if lowered == f"{prefix} forget":
            COMMANDS_USED += 1
            await record_command(message, "forget")

            guild_id = message.guild.id if message.guild else 0

            clear_user_memory(
                guild_id,
                message.author.id,
            )

            await safe_log(
                log_memory_event,
                client,
                guild_id,
                message.author.id,
                "User cleared their saved conversation memory.",
            )

            await safe_reply(
                message,
                "🧹 Your saved Veyra conversation memory has been cleared.",
            )
            return

        # SHOP

        if lowered == f"{prefix} shop":
            COMMANDS_USED += 1
            await record_command(message, "shop")

            if handle_shop is None:
                await safe_reply(
                    message,
                    "🛍️ The shop module isn't installed yet. "
                    "Add `commands/shop.py` first.",
                )
                return

            await handle_shop(message, PREFIX)
            return

        # SET CHAT CHANNEL

        if (
            lowered == f"{prefix} setchannel"
            or lowered.startswith(f"{prefix} setchannel ")
        ):
            COMMANDS_USED += 1
            await record_command(message, "setchannel")

            if message.guild is None:
                await safe_reply(
                    message,
                    "Run this command inside your server.",
                )
                return

            if not is_admin(message.author, message.guild):
                await safe_reply(
                    message,
                    "🔒 You need Administrator or Manage Server "
                    "permission to configure Veyra.",
                )
                return

            await handle_setchannel(
                message,
                client,
                is_admin,
            )
            return

        # REMOVE CHAT CHANNEL

        if (
            lowered == f"{prefix} removechannel"
            or lowered.startswith(f"{prefix} removechannel ")
        ):
            COMMANDS_USED += 1
            await record_command(message, "removechannel")

            if message.guild is None:
                await safe_reply(
                    message,
                    "Run this command inside your server.",
                )
                return

            if not is_admin(message.author, message.guild):
                await safe_reply(
                    message,
                    "🔒 You need Administrator or Manage Server "
                    "permission to manage Veyra's channels.",
                )
                return

            await handle_removechannel(
                message,
                is_admin,
            )
            return

        # CHAT MODE

        if lowered in (
            f"{prefix} chat",
            f"{prefix} longchat",
        ):
            COMMANDS_USED += 1
            await record_command(message, "mode")

            if message.guild is None:
                await safe_reply(
                    message,
                    "Run this command inside your server.",
                )
                return

            if not is_admin(message.author, message.guild):
                await safe_reply(
                    message,
                    "🔒 Only server administrators can change the AI mode.",
                )
                return

            new_mode = (
                "longchat"
                if lowered == f"{prefix} longchat"
                else "chat"
            )

            set_chat_mode(message.guild.id, new_mode)

            label = (
                "Detailed Chat"
                if new_mode == "longchat"
                else "Quick Chat"
            )

            await safe_reply(
                message,
                f"❄️ Veyra mode changed to **{label}**.",
            )
            return

        # PRODUCT COMMAND ROUTING

        subcommand, question = get_command_parts(content)

        if subcommand:
            # CODE PRO

            if subcommand == "codepro":
                COMMANDS_USED += 1
                await record_command(message, "codepro")

                handled = await handle_code_pro(
                    message,
                    question,
                )

                if not handled:
                    await safe_reply(
                        message,
                        f"Use `{PREFIX} code` to open the coding "
                        "workspace and learn about Code Free and Code Pro.",
                    )

                return

            # PRODUCT LIST

            if subcommand == "products":
                COMMANDS_USED += 1
                await record_command(message, "products")
                await handle_products(message)
                return

            # PRODUCT COMMANDS

            if subcommand in PRODUCTS:
                COMMANDS_USED += 1
                await record_command(message, subcommand)

                if question:
                    if subcommand == "research":
                        await handle_ask_research(
                            message,
                            question,
                        )
                    else:
                        await handle_ask_product(
                            message,
                            subcommand,
                            question,
                        )
                else:
                    await handle_product_command(
                        message,
                        subcommand,
                    )

                return

            # GRANT PRO
            # Authorization remains inside the products module.

            if subcommand == "grantpro":
                COMMANDS_USED += 1
                await record_command(message, "grantpro")
                await handle_grant_pro(message, content.split())
                return

        # IGNORE UNKNOWN PREFIX COMMANDS

        if is_command(content):
            return

        # SERVER-ONLY AI CHAT

        if message.guild is None:
            return

        guild_id = message.guild.id
        user_id = message.author.id

        chat_channels = get_chat_channels(guild_id)

        if message.channel.id not in chat_channels:
            return

        print(
            f"[CHAT] Received message in configured channel "
            f"{message.channel.id}; guild_id={guild_id}; "
            f"user_id={user_id}"
        )

        # CODING REQUEST ROUTER

        if looks_like_coding_request(content):
            await send_coding_upgrade_embed(message)
            return

        # LOAD USER MEMORY AND PREFERENCES

        memory = get_user_memory(guild_id, user_id)

        if not isinstance(memory, dict):
            memory = {}

        summary = memory.get("summary", "")
        preferences = memory.get("preferences", {})

        if not isinstance(preferences, dict):
            preferences = {}

        history = get_recent_history(guild_id, user_id)

        if not isinstance(history, list):
            history = []

        lower_content = content.lower()

        if any(
            phrase in lower_content
            for phrase in (
                "reply in hindi",
                "speak hindi",
                "hindi mein reply",
                "hindi me reply",
            )
        ):
            set_preference(
                guild_id,
                user_id,
                "language",
                "Hindi",
            )
            preferences["language"] = "Hindi"

        elif any(
            phrase in lower_content
            for phrase in (
                "reply in english",
                "speak english",
            )
        ):
            set_preference(
                guild_id,
                user_id,
                "language",
                "English",
            )
            preferences["language"] = "English"

        # SAVE USER MESSAGE

        add_message(
            guild_id,
            user_id,
            "user",
            content,
        )

        # AI REQUEST

        mode = get_chat_mode(guild_id)

        await safe_log(
            log_ai_request,
            client,
            guild_id,
            user_id,
            mode,
            "started",
        )

        try:
            async with message.channel.typing():
                reply = await ask_veyra(
                    prompt=content,
                    mode=mode,
                    memory_summary=summary,
                    preferences=preferences,
                    history=history,
                )

        except Exception as error:
            await safe_log(
                log_ai_request,
                client,
                guild_id,
                user_id,
                mode,
                "failed",
            )

            await record_error(
                message,
                "AI request",
                error,
            )
            raise

        if not reply:
            reply = (
                "I couldn't generate a response just now. "
                "Please try again."
            )

        # SAVE ASSISTANT RESPONSE

        add_message(
            guild_id,
            user_id,
            "assistant",
            str(reply),
        )

        # SEND RESPONSE

        await send_long_reply(message, reply)

        await safe_log(
            log_ai_request,
            client,
            guild_id,
            user_id,
            mode,
            "success",
        )

    except Exception as error:
        await record_error(
            message,
            "on_message",
            error,
        )

        print("[MESSAGE ERROR] Message processing failed.")

        await safe_reply(
            message,
            "I couldn't process that message right now. "
            "Please try again later.",
        )


# ==================================================
# RUN BOT
# ==================================================

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is missing from the hosting environment."
        )

    client.run(token)
