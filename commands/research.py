
import discord

from ai_client import ask_veyra
from commands.products import get_tier

ICE_BLUE = discord.Color.from_rgb(42, 164, 255)
MESSAGE_LIMIT = 3800


def build_research_prompt(question):
    return f"""
You are Veyra Research, an AI research assistant.

Research task:
{question}

Instructions:
- Use live web search to research the question before answering.
- Compare multiple reliable sources when appropriate.
- Include clickable Markdown links to sources actually returned by search.
- Never invent sources, URLs, publication dates, or statistics.
- Distinguish confirmed facts from estimates and predictions.
- Organize substantial research into a professional report.
- If live search fails or produces no sources, clearly disclose that.
"""


def split_message(text, limit=MESSAGE_LIMIT):
    """Split text into Discord-safe chunks without cutting words when possible."""
    text = str(text or "").strip()

    if not text:
        return ["Veyra returned an empty research report."]

    chunks = []

    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit + 1)

        if split_at < limit // 2:
            split_at = text.rfind(" ", 0, limit + 1)

        if split_at < limit // 2:
            split_at = limit

        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()

    if text:
        chunks.append(text)

    return chunks


async def handle_ask_research(message, question):
    if not question.strip():
        await message.reply(
            "Add a research question after the command.\n"
            "Example: `!veyra research Research the PlayStation brand`",
            mention_author=False,
        )
        return

    tier = get_tier(message.author.id, "research")

    status = discord.Embed(
        title="🔎 Veyra Research",
        description=(
            "Preparing your research request..."
            if tier == "pro"
            else
            "Preparing your response. Free access may not include "
            "live web search."
        ),
        color=ICE_BLUE,
    )

    status_message = await message.reply(
        embed=status,
        mention_author=False,
    )

    try:
        answer = await ask_veyra(
            prompt=build_research_prompt(question),
            mode="deep" if tier == "pro" else "chat",
            web_search=(tier == "pro"),
        )

        chunks = split_message(answer, limit=MESSAGE_LIMIT)
        total = len(chunks)

        for index, chunk in enumerate(chunks):
            title = "🔎 Veyra Research Report"

            if total > 1:
                title += f" · Part {index + 1}/{total}"

            embed = discord.Embed(
                title=title,
                description=chunk,
                color=ICE_BLUE,
            )

            embed.set_footer(
                text=f"{tier.upper()} • VEYRA AI • VOLBASTY STUDIOS"
            )

            if index == 0:
                await status_message.edit(embed=embed)
            else:
                await message.channel.send(embed=embed)

    except Exception as error:
        print(
            f"[RESEARCH ERROR] {type(error).__name__}: {error}",
            flush=True,
        )

        error_embed = discord.Embed(
            title="⚠️ Research request failed",
            description=(
                "Veyra couldn't complete this research request. "
                "Please try again later."
            ),
            color=discord.Color.orange(),
        )

        try:
            await status_message.edit(embed=error_embed)
        except discord.HTTPException:
            await message.channel.send(embed=error_embed)
