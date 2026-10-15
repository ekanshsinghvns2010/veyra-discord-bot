
import time

import discord
import psutil

from config import BOT_NAME, BOT_STUDIO


# Replace these placeholders with your server's animated emoji IDs.
# Format: "<a:emoji_name:123456789012345678>"
EMOJIS = {
    "ping": "📡",
    "memory": "🧠",
    "cpu": "⚙️",
    "users": "👥",
    "servers": "🏠",
    "commands": "📊",
    "owner": "👑",
    "uptime": "🟢",
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
    """Display Veyra's live bot statistics."""

    latency_ms = round(bot.latency * 1000)

    process = psutil.Process()
    memory_mb = process.memory_info().rss / (1024 * 1024)
    cpu_percent = process.cpu_percent(interval=None)

    uptime_seconds = max(
        0,
        int(time.monotonic() - start_time),
    )

    try:
        application = await bot.application_info()
        owner_name = str(application.owner)
    except Exception:
        owner_name = "Unknown"

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
