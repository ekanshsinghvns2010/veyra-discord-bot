
import discord

from channel_manager import remove_chat_channel


async def handle_removechannel(message, permission_check):
    if message.guild is None:
        await message.reply(
            "This command can only be used inside a server."
        )
        return

    if not permission_check(message.author, message.guild):
        await message.reply(
            "You need to be the server owner or an Administrator "
            "to manage Veyra's chat channels."
        )
        return

    if not message.channel_mentions:
        await message.reply(
            "**Which channel should I remove?**\n"
            "Usage: `!veyra removechannel #channel`\n"
            "Mention the specific channel you want to disable."
        )
        return

    channel = message.channel_mentions[0]

    if not isinstance(channel, discord.TextChannel):
        await message.reply(
            "Please select a text channel."
        )
        return

    if channel.guild.id != message.guild.id:
        await message.reply(
            "Please select a channel from this server."
        )
        return

    removed = remove_chat_channel(
        message.guild.id,
        channel.id
    )

    if removed:
        await message.reply(
            f"**Channel removed!**\n"
            f"Veyra will no longer respond to normal messages "
            f"in {channel.mention}.\n"
            f"Other configured channels remain enabled."
        )
    else:
        await message.reply(
            f"{channel.mention} wasn't configured as a Veyra chat channel."
        )
