
import discord

from memory_manager import (
    get_user_memory,
    clear_user_memory,
)


async def handle_memory(message):
    """Show the requesting user's memory privately through DMs."""
    if message.guild is None:
        await message.reply(
            "Use this command in a server where Veyra is enabled."
        )
        return

    memory = get_user_memory(
        message.guild.id,
        message.author.id,
    )

    summary = memory.get("summary", "").strip()
    preferences = memory.get("preferences", {})

    lines = []

    if summary:
        lines.append("**Saved summary**\n" + summary)

    if preferences:
        lines.append(
            "**Preferences**\n"
            + "\n".join(
                f"• {name}: {value}"
                for name, value in preferences.items()
            )
        )

    if not lines:
        lines.append(
            "Veyra hasn't saved any summary or preferences for you yet."
        )

    embed = discord.Embed(
        title="Your Veyra Memory",
        description="\n\n".join(lines),
        color=discord.Color.blurple(),
    )
    embed.set_footer(
        text="This shows saved notes and preferences, not every recent message."
    )

    try:
        await message.author.send(embed=embed)
        await message.reply("I've sent your memory to you in DMs.")
    except discord.Forbidden:
        await message.reply(
            "I couldn't DM you. Please allow direct messages from "
            "server members, then try again."
        )


async def handle_forget(message):
    """Clear only the requesting user's memory for this server."""
    if message.guild is None:
        await message.reply(
            "Use this command in the server whose memory you want to clear."
        )
        return

    removed = clear_user_memory(
        message.guild.id,
        message.author.id,
    )

    if removed:
        await message.reply(
            "Your saved memory for this server has been cleared."
        )
    else:
        await message.reply(
            "You don't have any saved memory for this server yet."
        )
