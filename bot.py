
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

from commands.ping import handle_ping
from commands.help import handle_help
from commands.setchannel import handle_setchannel
from commands.removechannel import handle_removechannel
from commands.memory import handle_memory

try:
    from commands.shop import handle_shop
except ImportError:
    handle_shop = None


# ==================================================
# DISCORD CLIENT
# ==================================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

COMMANDS_USED = 0
START_TIME = time.monotonic()


# ==================================================
# HELPERS
# ==================================================

def is_admin(member, guild=None):
    """Check server owner, Administrator, or Manage Server permission."""

    if not isinstance(member, discord.Member):
        return False

    if guild is not None and member.guild.id != guild.id:
        return False

    return (
        member.id == member.guild.owner_id
        or member.guild_permissions.administrator
        or member.guild_permissions.manage_guild
    )


def get_message_content(message):
    return (message.content or "").strip()


def is_command(content):
    return content.lower().startswith(PREFIX.lower())


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
        value="Use `!veyra shop` to explore Veyra's product options.",
        inline=False,
    )

    embed.set_footer(
        text="VEYRA AI • Powered by Volbasty Studios"
    )

    await message.reply(embed=embed, mention_author=False)


async def safe_reply(message, content):
    """Send an error or status reply without crashing the handler."""

    try:
        await message.reply(content, mention_author=False)
    except Exception as error:
        print(f"[REPLY ERROR] {error}")


# ==================================================
# STARTUP
# ==================================================

@client.event
async def on_ready():
    print("=" * 48)
    print(f"[READY] Veyra AI connected as {client.user}")
    print(f"[READY] Bot ID: {client.user.id}")
    print(f"[READY] Prefix: {PREFIX}")
    print("[READY] Memory system: enabled")
    print("[READY] Channel configuration: file-backed")
    print("[READY] Waiting for messages...")
    print("=" * 48)


# ==================================================
# SERVER CLEANUP
# ==================================================

@client.event
async def on_guild_remove(guild):
    """Delete channel settings only when Veyra leaves a server."""

    try:
        remove_guild_channels(guild.id)
        print(
            f"[GUILD] Removed saved channels for server {guild.id}"
        )
    except Exception:
        print("[GUILD ERROR] Could not clean up server settings.")
        traceback.print_exc()


# ==================================================
# MESSAGE HANDLER
# ==================================================

@client.event
async def on_message(message):
    global COMMANDS_USED

    if message.author.bot:
        return

    content = get_message_content(message)

    if not content:
        return

    lowered = content.lower()

    try:
        # ------------------------------------------
        # PING
        # ------------------------------------------

        if lowered == f"{PREFIX} ping":
            COMMANDS_USED += 1

            await handle_ping(
                message,
                client,
                START_TIME,
                COMMANDS_USED,
            )
            return

        # ------------------------------------------
        # HELP
        # ------------------------------------------

        if lowered in (
            f"{PREFIX} help",
            f"{PREFIX} guide",
        ):
            COMMANDS_USED += 1
            await handle_help(message, PREFIX)
            return

        # ------------------------------------------
        # MEMORY
        # ------------------------------------------

        if lowered == f"{PREFIX} memory":
            COMMANDS_USED += 1
            await handle_memory(message)
            return

        # ------------------------------------------
        # FORGET MEMORY
        # ------------------------------------------

        if lowered == f"{PREFIX} forget":
            COMMANDS_USED += 1

            guild_id = message.guild.id if message.guild else 0

            clear_user_memory(
                guild_id,
                message.author.id,
            )

            await safe_reply(
                message,
                "🧹 Your saved Veyra conversation memory has been cleared.",
            )
            return

        # ------------------------------------------
        # SHOP
        # ------------------------------------------

        if lowered == f"{PREFIX} shop":
            COMMANDS_USED += 1

            if handle_shop is None:
                await safe_reply(
                    message,
                    "🛍️ The shop module isn't installed yet. "
                    "Add commands/shop.py first.",
                )
                return

            await handle_shop(message, PREFIX)
            return

        # ------------------------------------------
        # SET CHAT CHANNEL
        # ------------------------------------------

        if (
            lowered == f"{PREFIX} setchannel"
            or lowered.startswith(f"{PREFIX} setchannel ")
        ):
            COMMANDS_USED += 1

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

        # ------------------------------------------
        # REMOVE CHAT CHANNEL
        # ------------------------------------------

        if (
            lowered == f"{PREFIX} removechannel"
            or lowered.startswith(f"{PREFIX} removechannel ")
        ):
            COMMANDS_USED += 1

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

        # ------------------------------------------
        # CHAT MODE
        # ------------------------------------------

        if lowered in (
            f"{PREFIX} chat",
            f"{PREFIX} longchat",
        ):
            COMMANDS_USED += 1

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
                if lowered == f"{PREFIX} longchat"
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

        # Ignore unknown commands.
        if is_command(content):
            return

        # ------------------------------------------
        # SERVER-ONLY AI CHAT
        # ------------------------------------------

        if message.guild is None:
            return

        guild_id = message.guild.id
        user_id = message.author.id

        chat_channels = get_chat_channels(guild_id)

        if message.channel.id not in chat_channels:
            return

        print(
            f"[CHAT] Message received in configured channel "
            f"{message.channel.id} (server {guild_id})"
        )

        # ------------------------------------------
        # CODING ROUTER
        # ------------------------------------------

        if looks_like_coding_request(content):
            await send_coding_upgrade_embed(message)
            return

        # ------------------------------------------
        # MEMORY AND AI
        # ------------------------------------------

        # IMPORTANT: memory_manager expects guild_id first.
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

        # Detect explicit language preferences.
        if (
            "reply in hindi" in lower_content
            or "speak hindi" in lower_content
            or "hindi mein reply" in lower_content
            or "hindi me reply" in lower_content
        ):
            set_preference(
                guild_id,
                user_id,
                "language",
                "Hindi",
            )
            preferences["language"] = "Hindi"

        elif (
            "reply in english" in lower_content
            or "speak english" in lower_content
        ):
            set_preference(
                guild_id,
                user_id,
                "language",
                "English",
            )
            preferences["language"] = "English"

        # Save the current user message.
        # The AI client also receives prompt=content and avoids
        # duplicating this message if it is already in history.
        add_message(
            guild_id,
            user_id,
            "user",
            content,
        )

        mode = get_chat_mode(guild_id)

        async with message.channel.typing():
            reply = await ask_veyra(
                prompt=content,
                mode=mode,
                memory_summary=summary,
                preferences=preferences,
                history=history,
            )

        if not reply:
            reply = (
                "I couldn't generate a response just now. "
                "Please try again."
            )

        reply = str(reply)

        # Save assistant reply using the same memory key.
        add_message(
            guild_id,
            user_id,
            "assistant",
            reply,
        )

        # Discord message length limit.
        if len(reply) <= 1900:
            await message.reply(
                reply,
                mention_author=False,
            )
        else:
            for start in range(0, len(reply), 1900):
                await message.channel.send(
                    reply[start:start + 1900]
                )

    except Exception as error:
        print(f"[MESSAGE ERROR] {type(error).__name__}: {error}")
        traceback.print_exc()

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
