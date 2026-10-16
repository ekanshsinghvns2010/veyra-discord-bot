
import os
import time
import discord

from config import PREFIX
from ai_client import ask_veyra
from channel_manager import get_chat_channels, remove_chat_channel
from mode_manager import get_chat_mode, set_chat_mode

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

    # Keep each Discord message below the 2,000-character limit.
    for start in range(0, len(content), 1900):
        await channel.send(content[start:start + 1900])


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

    # Commands are handled before normal chat.
    if lowered == f"{PREFIX} ping":
        COMMANDS_USED += 1
        await handle_ping(message, bot, START_TIME, COMMANDS_USED)
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
        if message.guild is None:
            await message.reply("These settings can only be changed inside a server.")
            return

        if not is_server_admin(message.author, message.guild):
            await message.reply("Only the server owner or an Administrator can change Veyra's response mode.")
            return

        mode = "longchat" if lowered.endswith("longchat") else "chat"
        set_chat_mode(message.guild.id, mode)
        COMMANDS_USED += 1

        if mode == "chat":
            await message.reply(
                "**Chat mode enabled!** I'll keep replies short and conversational."
            )
        else:
            await message.reply(
                "**Longchat mode enabled!** I'll provide more detailed, formatted answers."
            )
        return

    # Ignore other Veyra-prefixed commands.
    if lowered.startswith(PREFIX + " "):
        return

    if message.guild is None:
        return

    channel_ids = get_chat_channels(message.guild.id)

    if message.channel.id not in channel_ids:
        return

    mode = get_chat_mode(message.guild.id)

    try:
        async with message.channel.typing():
            response = await ask_veyra(
                content,
                mode="deep" if mode == "longchat" else "chat",
            )

        await send_long_message(message.channel, response)

    except Exception as error:
        print(f"AI request failed: {type(error).__name__}: {error}")
        await message.reply(
            "I couldn't process that message right now. Please try again later."
        )



@bot.event
async def on_guild_remove(guild):
    from channel_manager import remove_guild_channels

    remove_guild_channels(guild.id)


def main():
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN environment variable.")

    bot.run(token)


if __name__ == "__main__":
    main()
