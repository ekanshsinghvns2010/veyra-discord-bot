
import os
import time
import discord

from config import PREFIX
from ai_client import ask_veyra
from channel_manager import (
    get_chat_channels,
    remove_chat_channel,
)
from commands.ping import handle_ping
from commands.help import handle_help
from commands.setchannel import handle_setchannel
from commands.removechannel import handle_removechannel


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

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
    for start in range(0, len(content), 2000):
        await channel.send(content[start:start + 2000])


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
        await handle_setchannel(
            message, bot, is_server_admin
        )
        return

    if lowered.startswith(f"{PREFIX} removechannel"):
        COMMANDS_USED += 1
        await handle_removechannel(
            message, is_server_admin
        )
        return

    # Ignore other messages that look like Veyra commands.
    if lowered.startswith(PREFIX + " "):
        return

    # Veyra only chats in configured channels.
    if message.guild is None:
        return

    channel_ids = get_chat_channels(message.guild.id)

    if message.channel.id not in channel_ids:
        return

    try:
        async with message.channel.typing():
            response = await ask_veyra(content)

        await send_long_message(message.channel, response)

    except Exception as error:
        print(f"AI request failed: {error}")
        await message.reply(
            "I couldn't process that message right now. Please try again later."
        )


@bot.event
async def on_guild_remove(guild):
    # Remove this server's saved channel configuration.
    channel_ids = get_chat_channels(guild.id)

    for channel_id in channel_ids:
        remove_chat_channel(guild.id, channel_id)


def main():
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "Missing DISCORD_BOT_TOKEN environment variable."
        )

    bot.run(token)


if __name__ == "__main__":
    main()
