
import discord

from channel_manager import set_chat_channel


async def handle_setchannel(message, bot, permission_check):
    if message.guild is None:
        await message.reply(
            "This command can only be used inside a server."
        )
        return

    if not permission_check(message.author, message.guild):
        await message.reply(
            "You need to be the server owner or an Administrator "
            "to configure Veyra's chat channels."
        )
        return

    if not message.channel_mentions:
        await message.reply(
            "**Choose a channel first!**\n"
            "Usage: `!veyra setchannel #channel`\n"
            "Mention the channel you want Veyra to answer in."
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

    bot_member = message.guild.me

    if bot_member is None:
        await message.reply(
            "I couldn't verify my permissions. Please try again."
        )
        return

    permissions = channel.permissions_for(bot_member)

    if not (
        permissions.view_channel
        and permissions.send_messages
        and permissions.read_message_history
    ):
        await message.reply(
            f"I need **View Channel**, **Send Messages**, and "
            f"**Read Message History** permissions in {channel.mention}."
        )
        return

    set_chat_channel(message.guild.id, channel.id)

    await message.reply(
        f"**Veyra channel configured!**\n"
        f"I can now respond to normal messages in {channel.mention}.\n"
        f"Other configured channels will remain enabled."
    )
