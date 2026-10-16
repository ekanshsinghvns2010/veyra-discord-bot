
import discord

from config import PREFIX


async def handle_help(message):
    embed = discord.Embed(
        title="❄️ VEYRA AI  |  COMMAND CENTER",
        description=(
            "Your gateway to Veyra's intelligence.\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "💠 **AI CHAT**\n"
            "Chat with Veyra in your server's configured channel."
        ),
        color=discord.Color.from_rgb(35, 160, 255),
    )

    embed.add_field(
        name="⚡  GENERAL COMMANDS",
        value=(
            f"`{PREFIX} help` — Display this command guide\n"
            f"`{PREFIX} guide` — Open the help guide\n"
            f"`{PREFIX} ping` — Check latency, uptime and system stats\n"
            f"`{PREFIX} memory` — View your saved AI memory privately\n"
            f"`{PREFIX} forget` — Clear your saved memory"
        ),
        inline=False,
    )

    embed.add_field(
        name="🛠️  SERVER MANAGEMENT",
        value=(
            f"`{PREFIX} setchannel #channel` — Set the AI chat channel\n"
            f"`{PREFIX} removechannel #channel` — Remove the AI chat channel\n"
            f"`{PREFIX} chat` — Enable quick-response mode\n"
            f"`{PREFIX} longchat` — Enable detailed-response mode"
        ),
        inline=False,
    )

    embed.add_field(
        name="🔹  HOW TO USE VEYRA",
        value=(
            "1. An admin configures the chat channel.\n"
            "2. Send a normal message in that channel.\n"
            "3. Chat naturally or ask for detailed explanations.\n"
            "4. Use the memory commands to manage your saved context."
        ),
        inline=False,
    )

    embed.add_field(
        name="🔐  PERMISSIONS",
        value=(
            "Channel setup and response-mode changes require "
            "**server owner or administrator** permissions.\n"
            "Memory commands manage only your own saved memory."
        ),
        inline=False,
    )

    embed.set_footer(
        text="VEYRA AI • Powered by Volbasty Studios",
        icon_url=message.client.user.display_avatar.url
        if message.client.user else None,
    )

    await message.reply(embed=embed, mention_author=False)
