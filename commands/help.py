
import discord

from config import PREFIX, BOT_NAME, BOT_STUDIO


# Replace these with your custom animated Discord emoji IDs later.
EMOJIS = {
    "brand": "✦",
    "chat": "💬",
    "general": "🌐",
    "admin": "🛡️",
    "status": "📡",
    "settings": "⚙️",
    "help": "📖",
    "lock": "🔒",
    "online": "🟢",
}


def make_help_embed() -> discord.Embed:
    """Build Veyra's branded help menu."""

    embed = discord.Embed(
        title=f"{EMOJIS['brand']}  VEYRA  |  COMMAND CENTER",
        description=(
            "Your AI companion, powered by **Volbasty Studios**.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{EMOJIS['online']} **SYSTEM ONLINE**\n"
            "Chat naturally in a channel configured for AI conversations.\n\n"
            f"{EMOJIS['lock']} Commands use the prefix `{PREFIX}`."
        ),
        color=discord.Color.from_rgb(91, 76, 255),
    )

    embed.add_field(
        name=f"{EMOJIS['general']}  GENERAL COMMANDS",
        value=(
            f"`{PREFIX} ping`\n"
            "└ Check latency, memory, CPU and uptime\n\n"
            f"`{PREFIX} help`\n"
            "└ Open this command guide\n\n"
            f"`{PREFIX} guide`\n"
            "└ Another way to open this guide"
        ),
        inline=False,
    )

    embed.add_field(
        name=f"{EMOJIS['settings']}  CHANNEL MANAGEMENT",
        value=(
            f"`{PREFIX} setchannel #channel`\n"
            "└ Enable AI replies in the selected channel\n\n"
            f"`{PREFIX} removechannel #channel`\n"
            "└ Disable AI replies in that selected channel"
        ),
        inline=False,
    )

    embed.add_field(
        name=f"{EMOJIS['chat']}  HOW TO CHAT",
        value=(
            "① Ask the server owner or an Administrator to configure "
            "your channel.\n"
            "② Open that channel.\n"
            "③ Send a normal message — no mention required!\n\n"
            f"{EMOJIS['chat']} Veyra stays quiet in unconfigured channels."
        ),
        inline=False,
    )

    embed.add_field(
        name=f"{EMOJIS['admin']}  PERMISSIONS",
        value=(
            "Channel configuration is restricted to the **server owner** "
            "and members with Discord's **Administrator** permission.\n"
            "General commands are available to everyone."
        ),
        inline=False,
    )

    embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")

    embed.set_footer(
        text=f"{BOT_NAME} • {BOT_STUDIO}  |  Prefix commands only",
    )

    return embed


async def handle_help(
    message: discord.Message,
    prefix: str = PREFIX,
) -> None:
    """Send the branded help embed."""

    embed = make_help_embed()

    await message.reply(
        embed=embed,
        mention_author=False,
    )
