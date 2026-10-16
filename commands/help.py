
import discord

from config import PREFIX


async def handle_help(message, prefix=None):
    if prefix is None:
        prefix = PREFIX

    embed = discord.Embed(
        title="❄️ VEYRA AI",
        description=(
            "**COMMAND CENTER**\n"
            "Your gateway to intelligence beyond limits.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "💠 **AI CHAT**\n"
            "Chat naturally in the configured server channel."
        ),
        color=discord.Color.from_rgb(35, 160, 255),
    )

    embed.add_field(
        name="⚡ GENERAL COMMANDS",
        value=(
            f"`{prefix} help` — Display this command guide\n"
            f"`{prefix} guide` — Open the help guide\n"
            f"`{prefix} ping` — Check latency and system stats\n"
            f"`{prefix} memory` — View your saved memory privately\n"
            f"`{prefix} forget` — Clear your saved memory"
        ),
        inline=False,
    )

    embed.add_field(
        name="🛠️ SERVER MANAGEMENT",
        value=(
            f"`{prefix} setchannel #channel` — Configure the AI chat channel\n"
            f"`{prefix} removechannel #channel` — Remove the AI chat channel\n"
            f"`{prefix} chat` — Switch to quick-response mode\n"
            f"`{prefix} longchat` — Switch to detailed-response mode"
        ),
        inline=False,
    )

    embed.add_field(
        name="🌌 HOW TO USE VEYRA",
        value=(
            " **01**  Ask questions in the configured chat channel.\n"
            " **02**  Chat naturally in your preferred language.\n"
            " **03**  Use `memory` to review saved context.\n"
            " **04**  Use `forget` to clear your saved memory."
        ),
        inline=False,
    )

    embed.add_field(
        name="🔐 PERMISSIONS",
        value=(
            "Channel configuration and response-mode changes "
            "require server owner or administrator permissions.\n\n"
            "Memory commands affect only your own saved memory."
        ),
        inline=False,
    )

    bot_member = message.guild.me if message.guild else None

    embed.set_footer(
        text="VEYRA AI • Powered by Volbasty Studios",
        icon_url=(
            bot_member.display_avatar.url
            if bot_member else None
        ),
    )

    await message.reply(embed=embed, mention_author=False)
