
import discord

from memory_manager import get_user_memory


async def handle_memory(message):
    if message.guild is None:
        await message.reply(
            "❄️ Use this command inside a server to view your memory."
        )
        return

    memory = get_user_memory(
        message.guild.id,
        message.author.id,
    )

    summary = memory.get("summary", "").strip()
    preferences = memory.get("preferences", {})
    language = preferences.get("language", "Not set")

    embed = discord.Embed(
        title="❄️ VEYRA AI",
        description=(
            "**YOUR MEMORY PROFILE**\n"
            "What Veyra currently remembers about you."
        ),
        color=discord.Color.from_rgb(35, 160, 255),
    )

    embed.add_field(
        name="🧠 MEMORY SUMMARY",
        value=(
            summary[:4000]
            if summary
            else "No memory summary yet. Chat with Veyra to build one."
        ),
        inline=False,
    )

    embed.add_field(
        name="🌐 LANGUAGE PREFERENCE",
        value=f"**{discord.utils.escape_markdown(str(language))}**",
        inline=False,
    )

    embed.set_footer(
        text="VEYRA AI • Your memory, your control"
    )

    try:
        await message.author.send(embed=embed)
        await message.reply(
            "❄️ I've sent your memory profile to your DMs.",
            mention_author=False,
        )
    except discord.Forbidden:
        await message.reply(
            "I couldn't DM you. Please enable direct messages "
            "from server members and try again.",
            mention_author=False,
        )


async def handle_forget(message):
    if message.guild is None:
        await message.reply(
            "Please use this command inside a server."
        )
        return

    from memory_manager import clear_user_memory

    removed = clear_user_memory(
        message.guild.id,
        message.author.id,
    )

    if removed:
        await message.reply(
            "🧹 Your saved memory for this server has been cleared.",
            mention_author=False,
        )
    else:
        await message.reply(
            "You don't have any saved memory to clear.",
            mention_author=False,
        )
