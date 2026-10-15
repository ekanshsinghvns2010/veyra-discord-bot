
import os
import time
import logging

import discord

from config import PREFIX
from ai_client import ask_veyra
from channel_manager import get_chat_channel, remove_chat_channel
from commands.ping import handle_ping
from commands.help import handle_help
from commands.setchannel import handle_setchannel
from commands.removechannel import handle_removechannel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Veyra")

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_BOT_TOKEN environment variable.")

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


@bot.event
async def on_ready():
    logger.info("Veyra is online as %s", bot.user)
    logger.info("Connected to %s server(s)", len(bot.guilds))


@bot.event
async def on_guild_remove(guild):
    remove_chat_channel(guild.id)


@bot.event
async def on_message(message):
    global COMMANDS_USED

    if message.author.bot or message.guild is None:
        return

    content = message.content.strip()
    lowered = content.lower()

    if not lowered:
        return

    command = lowered.split(maxsplit=1)[0]

    # Prefix commands work in any server text channel.
    if command == f"{PREFIX}ping":
        COMMANDS_USED += 1
        await handle_ping(
            message, bot, START_TIME, COMMANDS_USED
        )
        return

    if command in (f"{PREFIX}help", f"{PREFIX}guide"):
        COMMANDS_USED += 1
        await handle_help(message, PREFIX)
        return

    if command == f"{PREFIX}setchannel":
        await handle_setchannel(
            message, bot, is_server_admin
        )
        return

    if command == f"{PREFIX}removechannel":
        await handle_removechannel(
            message, is_server_admin
        )
        return

    # Ignore unknown prefix commands.
    if content.startswith(PREFIX):
        return

    # AI chat works ONLY in the configured channel.
    channel_id = get_chat_channel(message.guild.id)

    if channel_id is None:
        return

    if message.channel.id != channel_id:
        return

    try:
        async with message.channel.typing():
            answer = await ask_veyra(content)

        if not answer:
            answer = "I couldn't generate a response. Please try again."

        # Keep messages below Discord's character limit.
        for start in range(0, len(answer), 1900):
            chunk = answer[start:start + 1900]
            await message.reply(
                chunk,
                mention_author=False
            )

    except Exception:
        logger.exception("Veyra AI response failed")

        await message.reply(
            "⚠️ I'm having trouble reaching my AI model. "
            "Please try again shortly.",
            mention_author=False
        )


bot.run(DISCORD_TOKEN)
