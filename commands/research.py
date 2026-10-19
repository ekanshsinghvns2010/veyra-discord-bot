
import discord

from ai_client import ask_veyra
from commands.products import get_tier, PRODUCTS

ICE_BLUE = discord.Color.from_rgb(42, 164, 255)


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

        answer = str(answer or "").strip()

        if not answer:
            answer = (
                "Veyra received an empty response. "
                "Please try again with a shorter research question."
            )

        # Discord embed descriptions have a 4096-character limit.
        chunks = [
            answer[i:i + 3900]
            for i in range(0, len(answer), 3900)
        ]

        first = discord.Embed(
            title="🔎 Veyra Research Report",
            description=chunks[0],
            color=ICE_BLUE,
        )
        first.set_footer(
            text=f"{tier.upper()} • VEYRA AI • VOLBASTY STUDIOS"
        )

        await status_message.edit(embed=first)

        for chunk in chunks[1:]:
            await message.channel.send(chunk)

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

        await status_message.edit(embed=error_embed)
