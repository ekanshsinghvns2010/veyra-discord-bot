
import discord
from discord.utils import utcnow

from config import PREFIX
from channel_manager import (
    get_chat_channels,
    remove_chat_channel,
)
from ai_client import ask_veyra
from memory_manager import (
    get_user_memory,
    get_recent_history,
    add_message,
    update_summary,
    set_preference,
    clear_user_memory,
)
from mode_manager import get_mode, set_mode

from commands.ping import handle_ping
from commands.help import handle_help
from commands.setchannel import handle_setchannel
from commands.removechannel import handle_removechannel
from commands.memory import handle_memory

try:
    from commands.shop import handle_shop
except ImportError:
    handle_shop = None


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

COMMANDS_USED = 0


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def is_admin(member):
    if not isinstance(member, discord.Member):
        return False

    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_guild
    )


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


def get_message_content(message):
    return (message.content or "").strip()


def is_command(content):
    return content.lower().startswith(PREFIX.lower())


# --------------------------------------------------
# STARTUP
# --------------------------------------------------

@client.event
async def on_ready():
    print("=" * 40)
    print(f"Veyra AI connected as {client.user}")
    print(f"Bot ID: {client.user.id}")
    print(f"Prefix: {PREFIX}")
    print("Memory system: enabled")
    print("Ready to receive messages.")
    print("=" * 40)


# --------------------------------------------------
# GUILD EVENTS
# --------------------------------------------------

@client.event
async def on_guild_remove(guild):
    try:
        remove_chat_channel(guild.id)
    except Exception as error:
        print(f"Guild cleanup error: {error}")


# --------------------------------------------------
# MESSAGE HANDLER
# --------------------------------------------------

@client.event
async def on_message(message):
    global COMMANDS_USED

    # Ignore the bot itself and other bots.
    if message.author.bot:
        return

    content = get_message_content(message)

    if not content:
        return

    lowered = content.lower()

    # ----------------------------------------------
    # COMMANDS
    # ----------------------------------------------

    if lowered == f"{PREFIX} ping":
        COMMANDS_USED += 1
        await handle_ping(message)
        return

    if lowered in (f"{PREFIX} help", f"{PREFIX} guide"):
        COMMANDS_USED += 1
        await handle_help(message, PREFIX)
        return

    if lowered == f"{PREFIX} memory":
        COMMANDS_USED += 1
        await handle_memory(message)
        return

    if lowered == f"{PREFIX} forget":
        COMMANDS_USED += 1
        try:
            clear_user_memory(
                message.author.id,
                message.guild.id if message.guild else 0,
            )
            await message.reply(
                "🧹 Your saved Veyra conversation memory has been cleared.",
                mention_author=False,
            )
        except Exception as error:
            print(f"Memory clear error: {error}")
            await message.reply(
                "I couldn't clear your memory right now. Please try again.",
                mention_author=False,
            )
        return

    if lowered == f"{PREFIX} shop":
        COMMANDS_USED += 1

        if handle_shop is None:
            await message.reply(
                "🛍️ The shop module isn't installed yet. "
                "Add `commands/shop.py` and try again.",
                mention_author=False,
            )
            return

        await handle_shop(message, PREFIX)
        return

    if lowered.startswith(f"{PREFIX} setchannel"):
        COMMANDS_USED += 1

        if message.guild is None:
            await message.reply(
                "Run this command inside your server.",
                mention_author=False,
            )
            return

        if not is_admin(message.author):
            await message.reply(
                "🔒 You need Administrator or Manage Server permission "
                "to change the AI chat channel.",
                mention_author=False,
            )
            return

        await handle_setchannel(message)
        return

    if lowered.startswith(f"{PREFIX} removechannel"):
        COMMANDS_USED += 1

        if message.guild is None:
            await message.reply(
                "Run this command inside your server.",
                mention_author=False,
            )
            return

        if not is_admin(message.author):
            await message.reply(
                "🔒 You need Administrator or Manage Server permission "
                "to remove the AI chat channel.",
                mention_author=False,
            )
            return

        await handle_removechannel(message)
        return

    # ----------------------------------------------
    # MODE COMMANDS
    # !veyra chat
    # !veyra longchat
    # ----------------------------------------------

    if lowered in (f"{PREFIX} chat", f"{PREFIX} longchat"):
        COMMANDS_USED += 1

        if message.guild is None:
            await message.reply(
                "Run this command inside your server.",
                mention_author=False,
            )
            return

        if not is_admin(message.author):
            await message.reply(
                "🔒 Only server administrators can change the AI mode.",
                mention_author=False,
            )
            return

        new_mode = (
            "deep"
            if lowered == f"{PREFIX} longchat"
            else "chat"
        )

        try:
            set_mode(message.guild.id, new_mode)

            label = (
                "Deep Chat"
                if new_mode == "deep"
                else "Standard Chat"
            )

            await message.reply(
                f"❄️ Veyra mode changed to **{label}**.",
                mention_author=False,
            )
        except Exception as error:
            print(f"Mode update error: {error}")
            await message.reply(
                "I couldn't update the mode right now.",
                mention_author=False,
            )
        return

    # Ignore any other prefix command.
    if is_command(content):
        return

    # ----------------------------------------------
    # AI CHAT CHANNEL CHECK
    # ----------------------------------------------

    if message.guild is None:
        return

    try:
        chat_channels = get_chat_channels()
    except Exception as error:
        print(f"Channel lookup error: {error}")
        return

    # Supports channel mappings keyed by guild ID.
    guild_id = message.guild.id
    configured_channel = None

    if isinstance(chat_channels, dict):
        configured_channel = (
            chat_channels.get(guild_id)
            or chat_channels.get(str(guild_id))
        )

        # Some implementations store channel IDs inside a nested object.
        if isinstance(configured_channel, dict):
            configured_channel = (
                configured_channel.get("chat_channel")
                or configured_channel.get("channel_id")
            )

    if configured_channel is None:
        return

    try:
        configured_channel = int(configured_channel)
    except (TypeError, ValueError):
        return

    if message.channel.id != configured_channel:
        return

    # ----------------------------------------------
    # CODING ROUTER
    # ----------------------------------------------

    if looks_like_coding_request(content):
        await send_coding_upgrade_embed(message)
        return

    # ----------------------------------------------
    # AI + PERSONAL MEMORY
    # ----------------------------------------------

    user_id = message.author.id

    try:
        memory = get_user_memory(user_id, guild_id)

        if not isinstance(memory, dict):
            memory = {}

        summary = memory.get("summary", "")
        preferences = memory.get("preferences", {})

        if not isinstance(preferences, dict):
            preferences = {}

        history = get_recent_history(user_id, guild_id)

        if not isinstance(history, list):
            history = []

        # Detect a simple explicit language preference.
        lower_content = content.lower()

        if (
            "reply in hindi" in lower_content
            or "speak hindi" in lower_content
            or "hindi mein reply" in lower_content
            or "hindi me reply" in lower_content
        ):
            set_preference(
                user_id,
                guild_id,
                "language",
                "Hindi",
            )
            preferences["language"] = "Hindi"

        elif (
            "reply in english" in lower_content
            or "speak english" in lower_content
        ):
            set_preference(
                user_id,
                guild_id,
                "language",
                "English",
            )
            preferences["language"] = "English"

        # Save the user's message before requesting a response.
        add_message(
            user_id,
            guild_id,
            "user",
            content,
        )

        mode = get_mode(guild_id)

        async with message.channel.typing():
            reply = await ask_veyra(
                prompt=content,
                mode=mode,
                memory_summary=summary,
                preferences=preferences,
                history=history,
            )

        if not reply:
            reply = "I couldn't generate a response just now. Please try again."

        # Save the assistant's response for future context.
        add_message(
            user_id,
            guild_id,
            "assistant",
            str(reply),
        )

        # Discord message limit is 2000 characters.
        reply = str(reply)

        if len(reply) <= 1900:
            await message.reply(
                reply,
                mention_author=False,
            )
        else:
            for start in range(0, len(reply), 1900):
                await message.channel.send(reply[start:start + 1900])

    except Exception as error:
        print(f"AI message error: {error}")

        try:
            await message.reply(
                "I couldn't process that message right now. "
                "Please try again later.",
                mention_author=False,
            )
        except Exception as send_error:
            print(f"Error sending failure message: {send_error}")


# --------------------------------------------------
# RUN BOT
# --------------------------------------------------

if __name__ == "__main__":
    import os

    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is missing from the hosting environment."
        )

    client.run(token)
