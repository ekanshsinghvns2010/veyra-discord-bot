
import time

import discord
import psutil

from config import BOT_NAME, BOT_STUDIO
from commands.products import count_pro_users


# Animated and standard Discord emojis.
EMOJIS = {
    "ping": "<a:uptime:1560652462287753277>",
    "memory": "<a:equipment:1560654983689539676>",
    "cpu": "<:cpu:1560652822813351956>",
    "users": "👥",
    "servers": "🏠",
    "commands": "📊",
    "owner": "👑",
    "uptime": "<a:online:1560653233486045268>",
    "pro": "⚡",
}


def format_uptime(seconds: int) -> str:
    """Convert uptime seconds into a readable duration."""
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    parts.append(f"{seconds}s")

    return " ".join(parts)


async def handle_ping(
    message: discord.Message,
    bot: discord.Client,
    start_time: float,
    commands_used: int,
) -> None:
    """Display Veyra's live bot and Pro product statistics."""

    # Gateway latency
    latency_ms = round(bot.latency * 1000)

    # Process resource usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / (1024 * 1024)
    cpu_percent = process.cpu_percent(interval=None)

    # Bot uptime
    uptime_seconds = max(
        0,
        int(time.monotonic() - start_time),
    )

    # Discord application owner
    try:
        application = await bot.application_info()
        owner_name = str(application.owner)
    except Exception:
        owner_name = "Unknown"

    # Number of unique users with at least one Pro product.
    try:
        pro_users = count_pro_users()
    except Exception:
        pro_users = 0

    embed = discord.Embed(
        title=f"{EMOJIS['ping']} {BOT_NAME} • System Status",
        description="Live statistics for Veyra.",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )

    embed.add_field(
        name=f"{EMOJIS['ping']} Gateway Latency",
        value=f"`{latency_ms} ms`",
        inline=True,
    )

    embed.add_field(
        name=f"{EMOJIS['memory']} Memory Usage",
        value=f"`{memory_mb:.1f} MB`",
        inline=True,
    )

    embed.add_field(
        name=f"{EMOJIS['cpu']} CPU Usage",
        value=f"`{cpu_percent:.1f}%`",
        inline=True,
    )

    embed.add_field(
        name=f"{EMOJIS['users']} Cached Users",
        value=f"`{len(bot.users)}`",
        inline=True,
    )

    embed.add_field(
        name=f"{EMOJIS['servers']} Servers",
        value=f"`{len(bot.guilds)}`",
        inline=True,
    )

    embed.add_field(
        name=f"{EMOJIS['pro']} Pro Product Users",
        value=f"`{pro_users}` unique users",
        inline=True,
    )

    embed.add_field(
        name=f"{EMOJIS['commands']} Commands Used",
        value=f"`{commands_used}` since restart",
        inline=True,
    )

    embed.add_field(
        name=f"{EMOJIS['owner']} Application Owner",
        value=discord.utils.escape_markdown(owner_name),
        inline=True,
    )

    embed.add_field(
        name=f"{EMOJIS['uptime']} Uptime",
        value=f"`{format_uptime(uptime_seconds)}`",
        inline=True,
    )

    embed.set_footer(
        text=f"{BOT_NAME} • {BOT_STUDIO}",
    )

    await message.reply(
        embed=embed,
        mention_author=False,
    )
