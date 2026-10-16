
import os
from openai import AsyncOpenAI

from config import (
    DEFAULT_MODEL,
    OPENROUTER_BASE_URL,
    TEMPERATURE,
)

API_KEY = os.getenv("OPENROUTER_API_KEY")
OWNER_ID = os.getenv("VEYRA_OWNER_ID", "").strip()

if not API_KEY:
    raise RuntimeError("Missing OPENROUTER_API_KEY environment variable.")

client = AsyncOpenAI(
    api_key=API_KEY,
    base_url=OPENROUTER_BASE_URL,
    timeout=90.0,
    max_retries=2,
)

BASE_PROMPT = f"""
You are Veyra, an AI assistant created by Volbasty Studios.

Your creator is the Discord user with ID {OWNER_ID or "not configured"}.
If asked who created, owns, or developed you, credit Volbasty Studios
and mention your creator using Discord mention format <@{OWNER_ID}>.
Never invent a creator ID.

Be friendly, clear, helpful, and natural.
Follow the user's requested level of detail.
Do not repeat the same point unnecessarily.
"""

CHAT_PROMPT = """
CONVERSATION MODE:
Talk like a friendly person in a Discord conversation.
Usually answer in 1-2 short sentences.
For greetings and casual chat, keep it brief and natural.
Do not turn simple messages into essays.
Answer the actual question directly.
Use more detail only when the user genuinely needs it.
"""

DEEP_PROMPT = """
DETAILED MODE:
Give complete, informative answers.
Use Markdown headings, lists, examples, and steps when helpful.
Explain important details without unnecessary repetition.
Do not force every answer to be long.
Finish the explanation properly instead of stopping mid-sentence.
"""


async def ask_veyra(prompt, mode="chat"):
    mode = "deep" if mode == "deep" else "chat"

    instructions = CHAT_PROMPT if mode == "chat" else DEEP_PROMPT
    token_limit = 500 if mode == "chat" else 5000

    response = await client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "system",
                "content": BASE_PROMPT + "\n" + instructions,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        max_tokens=token_limit,
        temperature=TEMPERATURE,
    )

    choice = response.choices[0]
    answer = (choice.message.content or "").strip()

    if not answer:
        raise RuntimeError("The AI model returned an empty response.")

    if choice.finish_reason == "length":
        answer += "\n\n*Response reached the model's output limit. Ask me to continue for the rest.*"

    return answer
