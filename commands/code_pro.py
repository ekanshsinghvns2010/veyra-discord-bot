
import asyncio
import json
import re
from pathlib import Path

import discord

from ai_client import ask_veyra
from commands.products import get_tier


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_FILE = DATA_DIR / "code_projects.json"

# Discord embed descriptions allow up to 4096 characters.
# Leave room for formatting and safety.
MAX_EMBED_CHARS = 3500


# ==================================================
# PROJECT STORAGE
# ==================================================

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
    temporary_file = PROJECTS_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(
            projects,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_file.replace(PROJECTS_FILE)


def get_project(message):
    guild_id = message.guild.id if message.guild else 0
    key = f"{guild_id}:{message.author.id}"

    projects = load_projects()
    project = projects.get(key, {})

    return key, projects, project


def update_project(message, prompt, response):
    key, projects, project = get_project(message)

    if not project:
        project = {
            "name": "My coding project",
            "goal": prompt[:500],
            "files": [],
            "progress": "Started",
            "notes": "",
        }

    # Preserve the original goal and existing file list.
    project["last_request"] = prompt[:500]
    project["notes"] = response[:2000]
    project["progress"] = "Latest response generated"

    projects[key] = project
    save_projects(projects)


# ==================================================
# OUTPUT FORMATTING
# ==================================================

def split_output(text, limit=MAX_EMBED_CHARS):
    """
    Split output into Discord embed descriptions.
    Avoid splitting at a newline when possible.
    """

    text = (text or "").strip()

    if not text:
        return ["No output was generated. Please try again."]

    chunks = []

    while text:
        if len(text) <= limit:
            chunks.append(text)
            break

        cut = text.rfind("\n", 0, limit)

        if cut < limit // 2:
            cut = limit

        chunk = text[:cut].rstrip()

        if not chunk:
            chunk = text[:limit]
            cut = limit

        chunks.append(chunk)
        text = text[cut:].lstrip()

    return chunks


async def send_output(message, response):
    """Send every response part as an embed."""

    chunks = split_output(response)
    total = len(chunks)

    for index, chunk in enumerate(chunks, start=1):
        embed = discord.Embed(
            title=f"Veyra Code Pro • Part {index}/{total}",
            description=chunk,
            color=discord.Color.blurple(),
        )

        embed.set_footer(
            text="Generated code • Review before running"
        )

        if index == 1:
            await message.reply(
                embed=embed,
                mention_author=False,
            )
        else:
            await message.channel.send(embed=embed)


# ==================================================
# CODE GENERATION
# ==================================================

def wants_explanation(prompt):
    """Enable explanations only when explicitly requested."""

    text = prompt.lower()

    indicators = (
        "explain",
        "explanation",
        "teach me",
        "how does this work",
        "how does it work",
        "why does this work",
        "walk me through",
        "describe the code",
        "understand this code",
    )

    return any(term in text for term in indicators)


def build_system_prompt(project, explanation_requested):
    project_name = project.get("name", "My coding project")
    project_goal = project.get("goal", "Not defined")
    project_files = project.get("files", [])
    progress = project.get("progress", "Not started")
    notes = project.get("notes", "")

    explanation_rule = (
        "The user explicitly requested an explanation. Explain "
        "the relevant code clearly, then provide any requested files."
        if explanation_requested
        else (
            "CODE-ONLY OUTPUT: no greeting, conversation, introduction, "
            "or explanation. Output the file tree followed by complete "
            "files only."
        )
    )

    return f"""
You are Veyra Code Pro, a code-generation platform by Volbasty Studios.

SAVED PROJECT
Name: {project_name}
Goal: {project_goal}
Files: {", ".join(project_files) if project_files else "Not recorded"}
Progress: {progress}
Notes: {notes or "None"}

RESPONSE MODE
{explanation_rule}

STRICT OUTPUT RULES
1. For multi-file tasks, start with a compact file tree.
2. Output each file separately, labelled exactly:
   FILE: path/to/file.ext
3. Put each file's complete contents in a language-labelled Markdown
   code fence.
4. Never combine different files into one code block.
5. Do not replace required code with placeholders, ellipses, or
   statements such as "rest of the code goes here".
6. For a single-file task, output the file directly.
7. For follow-up changes, output only changed files unless the user
   requests the complete project.
8. Ask one short question if a missing detail prevents implementation.
9. Keep filenames and project decisions consistent with saved context.
10. Never claim code was executed, tested, or deployed unless it was.
11. Never claim to have changed the user's repository or device.
12. Never execute generated code on the bot host.
13. Never reveal API keys, passwords, or private credentials.
14. Do not generate malware or harmful code.

SUPPORTED PROJECTS
Websites, Android apps, Discord bots, Python tools, robotics software,
and space-technology software.
"""


async def handle_code_pro(message, prompt):
    """
    Handle Code Pro requests.

    Returns True if the request was handled.
    Returns False for users who should continue through Code Free.
    """

    tier = get_tier(str(message.author.id), "code")

    if tier != "pro":
        return False

    prompt = prompt.strip()

    if not prompt:
        await message.reply(
            "Use `!veyra codepro <project request>`.\n"
            "Example: `!veyra codepro build a responsive landing page`",
            mention_author=False,
        )
        return True

    _, _, project = get_project(message)

    explanation_requested = wants_explanation(prompt)
    system_prompt = build_system_prompt(
        project,
        explanation_requested,
    )

    status = await message.reply(
        "🧊 Generating project files...",
        mention_author=False,
    )

    try:
        response = await asyncio.wait_for(
            ask_veyra(
                prompt=(
                    f"{system_prompt}\n\n"
                    f"USER REQUEST:\n{prompt}"
                ),
                mode="deep",
                web_search=False,
            ),
            timeout=280,
        )

        if not isinstance(response, str) or not response.strip():
            await status.edit(
                content="No code was generated. Please try again."
            )
            return True

        # Save project state independently of normal chat memory.
        update_project(message, prompt, response)

        try:
            await status.delete()
        except discord.HTTPException:
            pass

        await send_output(message, response)

    except asyncio.TimeoutError:
        await status.edit(
            content=(
                "⏳ Code generation timed out. "
                "Please try again with a smaller request."
            )
        )

    except Exception as exc:
        print(
            f"[CODE PRO ERROR] {type(exc).__name__}: {exc}"
        )

        try:
            await status.edit(
                content=(
                    "⚠️ Code generation failed. "
                    "The model may be busy or rate-limited. "
                    "Please try again."
                )
            )
        except discord.HTTPException:
            pass

    return True
