
import json
import os
from pathlib import Path
from datetime import datetime, timezone

import discord


DATA_DIR = Path(os.getenv("VEYRA_DATA_DIR", "data"))
CONFIG_FILE = DATA_DIR / "logging_config.json"

# If a dedicated channel isn't available, use the server's general
# log channel or error channel instead.
FALLBACKS = {
    "veyra-system-logs": ("veyra-server-logs",),
    "veyra-ai-diagnostics": ("veyra-server-logs",),
    "veyra-memory-logs": ("veyra-server-logs",),
    "veyra-security-logs": ("veyra-server-logs",),
    "veyra-server-audit": ("veyra-server-logs",),
    "veyra-error-logs": ("veyra-server-logs",),
    "veyra-server-logs": ("veyra-error-logs",),
}

COLORS = {
    "success": discord.Color.green(),
    "warning": discord.Color.orange(),
    "error": discord.Color.red(),
    "info": discord.Color.blurple(),
    "security": discord.Color.gold(),
}


def _load_config() -> dict:
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


async def send_log(
    client: discord.Client,
    guild_id: int,
    channel_name: str,
    title: str,
    description: str,
    *,
    color=None,
    fields=None,
) -> bool:
    """Send a metadata-only log. Logging errors never crash the bot."""
    try:
        guild_config = _load_config().get(str(guild_id), {})
        if not isinstance(guild_config, dict) or not guild_config.get("enabled"):
            return False

        channels = guild_config.get("channels", {})
        if not isinstance(channels, dict):
            return False

        candidates = (channel_name,) + FALLBACKS.get(channel_name, ())
        channel = None

        for candidate in candidates:
            channel_id = channels.get(candidate)
            if not channel_id:
                continue

            try:
                channel_id = int(channel_id)
            except (TypeError, ValueError):
                continue

            found = client.get_channel(channel_id)
            if found is None:
                try:
                    found = await client.fetch_channel(channel_id)
                except (discord.HTTPException, discord.NotFound):
                    continue

            if isinstance(found, discord.TextChannel):
                channel = found
                break

        if channel is None:
            return False

        embed = discord.Embed(
            title=str(title)[:256],
            description=str(description)[:4000],
            color=color or COLORS["info"],
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Veyra • Volbasty Studios")

        for name, value, inline in (fields or [])[:10]:
            embed.add_field(
                name=str(name)[:256],
                value=str(value)[:1024],
                inline=bool(inline),
            )

        await channel.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return True

    except Exception as error:
        # Never let a failed log disrupt the main bot.
        print(f"[LOGGING ERROR] type={type(error).__name__}")
        return False


async def log_command(client, guild_id, user_id, command_name, status="received"):
    return await send_log(
        client,
        guild_id,
        "veyra-command-logs",
        "Command Activity",
        f"Command: `{str(command_name)[:150]}`\nStatus: **{status}**",
        fields=[
            ("User ID", str(user_id), True),
            ("Server ID", str(guild_id), True),
        ],
    )


async def log_error(client, guild_id, location, error_type):
    return await send_log(
        client,
        guild_id,
        "veyra-error-logs",
        "Bot Error",
        "An operation failed. Check the hosting console for diagnostics.",
        color=COLORS["error"],
        fields=[
            ("Location", str(location)[:200], True),
            ("Error type", str(error_type)[:200], True),
        ],
    )


async def log_ai_request(client, guild_id, user_id, mode, status):
    return await send_log(
        client,
        guild_id,
        "veyra-ai-diagnostics",
        "AI Request",
        f"Request status: **{str(status)[:100]}**",
        color=COLORS["success"] if status == "success" else COLORS["warning"],
        fields=[
            ("User ID", str(user_id), True),
            ("Chat mode", str(mode)[:100], True),
        ],
    )


async def log_memory_event(client, guild_id, user_id, action):
    return await send_log(
        client,
        guild_id,
        "veyra-memory-logs",
        "Memory Activity",
        f"Action: **{str(action)[:150]}**",
        fields=[("User ID", str(user_id), True)],
    )


async def log_system_event(client, guild_id, description):
    return await send_log(
        client,
        guild_id,
        "veyra-system-logs",
        "System Event",
        str(description)[:4000],
    )


async def log_security_event(client, guild_id, user_id, action):
    return await send_log(
        client,
        guild_id,
        "veyra-security-logs",
        "Security Event",
        str(action)[:1000],
        color=COLORS["security"],
        fields=[("User ID", str(user_id), True)],
    )
