
import os
import time
import discord

from security.permissions import is_developer


# ============================================================
# VEYRA DEVELOPER COMMAND ROUTER
# ============================================================

BOT_NAME = "Veyra"
BOT_STUDIO = "Volbasty Studios"
START_TIME = time.monotonic()


def _developer_embed(title: str, description: str, color=None):
    embed = discord.Embed(
        title=f"⚙️ {BOT_NAME} // {title}",
        description=description,
        color=color or discord.Color.from_rgb(54, 151, 230),
    )
    embed.set_footer(text=f"{BOT_NAME} • {BOT_STUDIO} • Developer Console")
    return embed


async def _reply(message, embed=None, content=None):
    try:
        await message.reply(
            content=content,
            embed=embed,
            mention_author=False,
        )
    except discord.HTTPException:
        pass


async def handle_dev_command(message, client, prefix="!veyra"):
    """
    Handle developer-only commands.

    Returns:
        True  -> a developer command was handled.
        False -> this is not a developer command.
    """

    content = (message.content or "").strip()
    parts = content.split(maxsplit=2)

    if not parts or parts[0].lower() != prefix.lower():
        return False

    if len(parts) < 2:
        return False

    command = parts[1].lower()

    # Only these commands are reserved for the developer router.
    dev_commands = {
        "dev",
        "devhelp",
        "status",
        "diagnostics",
        "maintenance",
    }

    if command not in dev_commands:
        return False

    # Never infer developer access from server ownership or roles.
    if not is_developer(message.author.id):
        await _reply(
            message,
            embed=_developer_embed(
                "ACCESS DENIED",
                "🛡️ This command is restricted to authorized Veyra developers.\n\n"
                "Server Administrator permissions do not grant developer access.",
                discord.Color.red(),
            ),
        )
        return True

    # --------------------------------------------------------
    # DEVELOPER HELP
    # --------------------------------------------------------

    if command in ("dev", "devhelp"):
        embed = _developer_embed(
            "DEVELOPER CONSOLE",
            "Welcome to the restricted Veyra developer interface.",
        )

        embed.add_field(
            name="📡 System",
            value=(
                f"`{prefix} status` — View bot runtime status.\n"
                f"`{prefix} diagnostics` — Check basic runtime configuration."
            ),
            inline=False,
        )

        embed.add_field(
            name="🛠️ Maintenance",
            value=(
                f"`{prefix} maintenance on` — Enable maintenance mode.\n"
                f"`{prefix} maintenance off` — Disable maintenance mode."
            ),
            inline=False,
        )

        embed.add_field(
            name="🔐 Security",
            value=(
                "Developer access is controlled by `VEYRA_DEVELOPER_IDS`.\n"
                "This console does not grant privileges to server admins."
            ),
            inline=False,
        )

        await _reply(message, embed=embed)
        return True

    # --------------------------------------------------------
    # SYSTEM STATUS
    # --------------------------------------------------------

    if command == "status":
        latency_ms = round(client.latency * 1000, 2)
        uptime_seconds = max(0, int(time.monotonic() - START_TIME))

        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        embed = _developer_embed(
            "SYSTEM STATUS",
            "🟢 Veyra is connected to Discord.",
            discord.Color.green(),
        )

        embed.add_field(
            name="🤖 Identity",
            value=f"**Bot:** {client.user}\n**ID:** {client.user.id if client.user else 'Unknown'}",
            inline=True,
        )

        embed.add_field(
            name="📶 Gateway",
            value=f"**Latency:** {latency_ms} ms\n**Servers:** {len(client.guilds)}",
            inline=True,
        )

        embed.add_field(
            name="⏱️ Runtime",
            value=f"{hours}h {minutes}m {seconds}s",
            inline=True,
        )

        await _reply(message, embed=embed)
        return True

    # --------------------------------------------------------
    # SAFE DIAGNOSTICS
    # --------------------------------------------------------

    if command == "diagnostics":
        model_configured = bool(os.getenv("OPENROUTER_MODEL"))
        token_configured = bool(os.getenv("DISCORD_BOT_TOKEN"))
        developer_ids_configured = bool(
            os.getenv("VEYRA_DEVELOPER_IDS")
        )

        embed = _developer_embed(
            "DIAGNOSTICS",
            "Basic environment checks completed. Secret values are never displayed.",
        )

        embed.add_field(
            name="Discord token",
            value="✅ Configured" if token_configured else "❌ Missing",
            inline=True,
        )

        embed.add_field(
            name="Model override",
            value="✅ Configured" if model_configured else "ℹ️ Using config default",
            inline=True,
        )

        embed.add_field(
            name="Developer allowlist",
            value="✅ Configured" if developer_ids_configured else "⚠️ Missing",
            inline=True,
        )

        await _reply(message, embed=embed)
        return True

    # --------------------------------------------------------
    # MAINTENANCE FLAG
    # --------------------------------------------------------

    if command == "maintenance":
        argument = parts[2].strip().lower() if len(parts) > 2 else ""

        if argument not in ("on", "off"):
            await _reply(
                message,
                content=(
                    f"Usage: `{prefix} maintenance on` or "
                    f"`{prefix} maintenance off`"
                ),
            )
            return True

        # This is a process-local flag for future integration.
        # It does not yet block AI chat or commands.
        global MAINTENANCE_MODE
        MAINTENANCE_MODE = argument == "on"

        status = "ENABLED" if MAINTENANCE_MODE else "DISABLED"

        await _reply(
            message,
            embed=_developer_embed(
                "MAINTENANCE MODE",
                f"Maintenance flag: **{status}**\n\n"
                "Note: this flag is not yet connected to the message handler.",
                discord.Color.orange(),
            ),
        )
        return True

    return False


MAINTENANCE_MODE = False
