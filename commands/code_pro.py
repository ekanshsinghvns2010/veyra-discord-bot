
import asyncio
import json
from pathlib import Path

import discord

from ai_client import ask_veyra
from commands.products import get_tier


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_FILE = DATA_DIR / "code_projects.json"

MAX_CHUNK = 1800


def load_projects():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with PROJECTS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_projects(projects):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = PROJECTS_FILE.with_suffix(".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(projects, file, ensure_ascii=False, indent=2)

    temporary.replace(PROJECTS_FILE)


def get_project(message):
    guild_id = message.guild.id if message.guild else 0
    key = f"{guild_id}:{message.author.id}"

    projects = load_projects()
    return key, projects, projects.get(key, {})


def update_project(message, prompt, response):
    key, projects, project = get_project(message)

    # Preserve the original project goal instead of replacing it
    # with every follow-up message.
    if not project:
        project = {
            "name": "My coding project",
            "goal": prompt[:500],
            "files": [],
            "progress": "Started",
            "notes": "",
        }

    project["last_request"] = prompt[:500]
    project["notes"] = response[:1500]
    project["progress"] = "Latest response generated"

    projects[key] = project
    save_projects(projects)


def split_output(text, limit=MAX_CHUNK):
    """Split long text at line boundaries."""
    remaining = text.strip()
    chunks = []

    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        cut = remaining.rfind("\n", 0, limit)

        if cut < limit // 2:
            cut = limit

        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()

    return chunks or ["Veyra couldn't generate a response."]


async def send_output(message, response):
    chunks = split_output(response)

    embed = discord.Embed(
        title="Veyra Code Pro",
        description=chunks[0],
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="Generated code • Review before running")

    await message.reply(embed=embed, mention_author=False)

    for chunk in chunks[1:]:
        await message.channel.send(chunk)


async def handle_code_pro(message, prompt):
    """
    Returns True when Code Pro handled the request.
    Returns False for Code Free users so the existing handler can run.
    """
    tier = get_tier(str(message.author.id), "code")

    if tier != "pro":
        return False

    prompt = prompt.strip()

    if not prompt:
        await message.reply(
            "Tell me what you want to build.\n"
            "Example: `!veyra code build a Python calculator`",
            mention_author=False,
        )
        return True

    _, _, project = get_project(message)

    context = f"""
PROJECT NAME: {project.get('name', 'Not set')}
PROJECT GOAL: {project.get('goal', 'Not set')}
PROJECT FILES: {', '.join(project.get('files', [])) or 'Not recorded'}
PREVIOUS PROGRESS: {project.get('progress', 'Not started')}
PREVIOUS NOTES: {project.get('notes', 'None')}

You are Veyra Code Pro, created by Volbasty Studios.

Help with planning, writing, explaining, and debugging software.
Support websites, Android apps, Discord bots, Python projects,
robotics software, and space-technology software.

Rules:
- Return copy-ready code in language-labelled Markdown fences.
- Label every file with its exact path when generating multiple files.
- Explain where each file belongs and what to do next.
- Keep project decisions consistent with the saved context.
- Do not claim code was executed, tested, or deployed unless it was.
- Never execute generated code on the bot host.
- Never expose secrets, API keys, or private credentials.
- Do not provide malware or code intended to harm others.
"""

    status = await message.reply(
        "🧊 **Veyra Code Pro is working...**",
        mention_author=False,
    )

    try:
        response = await asyncio.wait_for(
            ask_veyra(
                prompt=f"{context}\n\nUSER REQUEST:\n{prompt}",
                mode="deep",
                web_search=False,
            ),
            timeout=280,
        )

        if not isinstance(response, str) or not response.strip():
            response = "I couldn't generate a response. Please try again."

        update_project(message, prompt, response)

        try:
            await status.delete()
        except discord.HTTPException:
            pass

        await send_output(message, response)

    except asyncio.TimeoutError:
        await status.edit(
            content="⏳ Code Pro timed out. Please try again shortly."
        )

    except Exception as exc:
        print(f"[CODE PRO ERROR] {type(exc).__name__}: {exc}")

        await status.edit(
            content=(
                "⚠️ Code Pro couldn't complete that request. "
                "The free model may be busy or rate-limited. "
                "Please try again."
            )
        )

    return True
