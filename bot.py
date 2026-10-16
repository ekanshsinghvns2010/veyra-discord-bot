
import os
import re
import time
import discord

from config import PREFIX
from ai_client import ask_veyra, summarize_memory
from channel_manager import (
    get_chat_channels,
    remove_chat_channel,
)
from mode_manager import get_chat_mode, set_chat_mode
from memory_manager import (
    get_user_memory,
    get_recent_history,
    add_message,
    update_summary,
    set_preference,
)
from commands.ping import handle_ping
from commands.help import handle_help
from commands.setchannel import handle_setchannel
from commands.removechannel import handle_removechannel

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)

START_TIME = time.monotonic()
COMMANDS_USED = 0


def is_server_admin(member, guild):
    return (
        member.id == guild.owner_id
        or member.guild_permissions.administrator
    )


async def send_long_message(channel, content):
    content = content or "I couldn't generate a response."

    for start in range(0, len(content), 1900):
        await channel.send(content[start:start + 1900])


def detect_language_preference(content):
    """Recognize clear, explicit language preferences."""
    text = content.lower().strip()

    patterns = [
        (r"\b(?:talk|speak|reply|respond|answer|chat)\s+in\s+"
         r"(hindi|english|spanish|french|german|japanese|"
         r"korean|arabic|bengali|tamil|telugu|marathi|"
         r"urdu|gujarati|punjabi)\b", 1),

        (r"\b(?:always|please)\s+(?:use|reply in|speak in|"
         r"respond in)\s+"
         r"(hindi|english|spanish|french|german|japanese|"
         r"korean|arabic|bengali|tamil|telugu|marathi|"
         r"urdu|gujarati|punjabi)\b", 1),

        (r"\b(?:stop speaking in|don't speak in|do not speak in|"
         r"switch to)\s+"
         r"(hindi|english|spanish|french|german|japanese|"
         r"korean|arabic|bengali|tamil|telugu|marathi|"
         r"urdu|gujarati|punjabi)\b", 1),
    ]

    for pattern, group in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(group).capitalize()

    return None


async def summarize_overflow(guild_id, user_id, overflow):
    if not overflow:
        return

    try:
        memory = get_user_memory(guild_id, user_id)

        summary = await summarize_memory(
            memory.get("summary", ""),
            overflow,
        )

        update_summary(guild_id, user_id, summary)

    except Exception as error:
        print(
            "Memory summarization failed: "
            f"{type(error).__name__}: {error}"
        )


@bot.event
async def on_ready():
    print(f"Veyra is online as {bot.user}")
    print(f"Connected to {len(bot.guilds)} server(s).")


@bot.event
async def on_message(message):
    global COMMANDS_USED

    if message.author.bot:
        return

    content = message.content.strip()
    lowered = content.lower()

    if not content:
        return

    if lowered == f"{PREFIX} ping":
        COMMANDS_USED += 1
        await handle_ping(
            message, bot, START_TIME, COMMANDS_USED
        )
        return

    if lowered in (f"{PREFIX} help", f"{PREFIX} guide"):
        COMMANDS_USED += 1
        await handle_help(message, PREFIX)
        return

    if lowered.startswith(f"{PREFIX} setchannel"):
        COMMANDS_USED += 1
        await handle_setchannel(message, bot, is_server_admin)
        return

    if lowered.startswith(f"{PREFIX} removechannel"):
        COMMANDS_USED += 1
        await handle_removechannel(message, is_server_admin)
        return

    if lowered in (f"{PREFIX} chat", f"{PREFIX} longchat"):
        COMMANDS_USED += 1

        if message.guild is None:
            await message.reply(
                "This command can only be used in a server."
            )
            return

        if not is_server_admin(message.author, message.guild):
            await message.reply(
                "Only a server administrator can change this mode."
            )
            return

        mode = (
            "longchat"
            if lowered.endswith("longchat")
            else "chat"
        )

        set_chat_mode(message.guild.id, mode)
        await message.reply(f"Veyra mode set to **{mode}**.")
        return

    # Other commands must not be treated as ordinary AI messages.
    if lowered.startswith(PREFIX + " "):
        return

    if message.guild is None:
        return

    if message.channel.id not in get_chat_channels(message.guild.id):
        return

    guild_id = message.guild.id
    user_id = message.author.id

    # Save an explicit language preference for this user only.
    language = detect_language_preference(content)
    if language:
        set_preference(
            guild_id,
            user_id,
            "language",
            language,
        )

    # Store the user's message and summarize anything pushed out
    # of the 15-message rolling history.
    overflow = add_message(
        guild_id,
        user_id,
        "user",
        content,
    )

    await summarize_overflow(
        guild_id,
        user_id,
        overflow,
    )

    memory = get_user_memory(guild_id, user_id)
    history = get_recent_history(guild_id, user_id)
    mode = get_chat_mode(guild_id)

    try:
        COMMANDS_USED += 1

        async with message.channel.typing():
            response = await ask_veyra(
                content,
                mode="deep" if mode == "longchat" else "chat",
                memory_summary=memory.get("summary", ""),
                preferences=memory.get("preferences", {}),
                history=history,
            )

        await send_long_message(message.channel, response)

        # Save the assistant response too, keeping the history
        # limited to the most recent 15 messages.
        overflow = add_message(
            guild_id,
            user_id,
            "assistant",
            response,
        )

        await summarize_overflow(
            guild_id,
            user_id,
            overflow,
        )

    except Exception as error:
        print(
            f"AI request failed: {type(error).__name__}: {error}"
        )
        await message.reply(
            "I couldn't process that message right now. "
            "Please try again later."
        )


@bot.event
async def on_guild_remove(guild):
    from channel_manager import remove_guild_channels

    remove_guild_channels(guild.id)


def main():
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is not configured."
        )

    bot.run(token)


if __name__ == "__main__":
    main()
