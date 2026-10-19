
import asyncio
import io
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

import discord

from ai_client import ask_veyra
from commands.products import get_tier


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_FILE = DATA_DIR / "code_projects.json"

MAX_EMBED_CHARS = 3500
MAX_ATTACHMENT_BYTES = 7 * 1024 * 1024
MAX_PROJECT_BYTES = 20 * 1024 * 1024
MAX_FILES = 100

# Discord attachment limits depend on the server/account.
# Stay conservative and handle upload failures gracefully.


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


def update_project(message, prompt, response, files=None):
    key, projects, project = get_project(message)

    if not project:
        project = {
            "name": "My coding project",
            "goal": prompt[:500],
            "files": [],
            "progress": "Started",
            "notes": "",
        }

    project["last_request"] = prompt[:500]
    project["notes"] = response[:2000]
    project["progress"] = "Latest response generated"

    if files:
        project["files"] = list(files.keys())[:MAX_FILES]

    projects[key] = project
    save_projects(projects)


# ==================================================
# RESPONSE PARSING
# ==================================================

_FILE_MARKER = re.compile(
    r"(?m)^[ \t]*FILE:[ \t]*(.+?)[ \t]*$"
)

_FENCE_LINE = re.compile(
    r"^[ \t]{0,3}(`{3,}|~{3,})([^\r\n]*)$"
)


def _safe_filename(name):
    """Reject absolute paths and traversal outside the project."""

    name = name.strip().replace("\\", "/")
    path = PurePosixPath(name)

    if (
        not name
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or ":" in path.parts[0]
    ):
        return None

    cleaned = str(path)

    if cleaned in {"", "."}:
        return None

    return cleaned


def _remove_outer_fence(content):
    """
    Remove one outer Markdown fence when it wraps an entire file.

    The opening and closing fences must match. Inner Markdown fences
    are retained when the outer fence uses a longer delimiter.
    """

    lines = content.splitlines(keepends=True)

    if len(lines) < 2:
        return content.strip("\r\n")

    opening = _FENCE_LINE.match(lines[0].rstrip("\r\n"))

    if not opening:
        return content.strip("\r\n")

    marker = opening.group(1)
    marker_char = marker[0]

    closing_index = None

    for index in range(len(lines) - 1, 0, -1):
        candidate = _FENCE_LINE.match(
            lines[index].rstrip("\r\n")
        )

        if not candidate:
            continue

        closing_marker = candidate.group(1)

        if (
            closing_marker[0] == marker_char
            and len(closing_marker) >= len(marker)
            and not candidate.group(2).strip()
        ):
            closing_index = index
            break

    if closing_index is None:
        return content.strip("\r\n")

    # Only unwrap if the fence encloses the entire section.
    if any(line.strip() for line in lines[1:closing_index]):
        return "".join(lines[1:closing_index]).strip("\r\n")

    return ""


def extract_files(response):
    """
    Extract files labelled as:

        FILE: src/main.py
        ```python
        print("hello")
        ```

    Returns a dictionary of path -> complete file content.
    If no valid file markers are found, returns an empty dictionary.
    """

    matches = list(_FILE_MARKER.finditer(response))

    if not matches:
        return {}

    files = {}

    for index, match in enumerate(matches):
        raw_name = match.group(1).strip()
        name = _safe_filename(raw_name)

        if not name:
            continue

        section_start = match.end()
        section_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(response)
        )

        section = response[section_start:section_end].strip()

        # Prefer the first fenced block in the section. For files such
        # as README.md, the model should use an outer fence longer than
        # any embedded Markdown fence.
        lines = section.splitlines(keepends=True)
        opening_index = None
        opening_marker = None

        for line_index, line in enumerate(lines):
            fence = _FENCE_LINE.match(line.rstrip("\r\n"))

            if fence:
                opening_index = line_index
                opening_marker = fence.group(1)
                break

        if opening_index is not None:
            marker_char = opening_marker[0]
            closing_index = None

            for line_index in range(
                opening_index + 1,
                len(lines),
            ):
                fence = _FENCE_LINE.match(
                    lines[line_index].rstrip("\r\n")
                )

                if not fence:
                    continue

                candidate = fence.group(1)

                if (
                    candidate[0] == marker_char
                    and len(candidate) >= len(opening_marker)
                    and not fence.group(2).strip()
                ):
                    closing_index = line_index

            if closing_index is not None:
                content = "".join(
                    lines[opening_index + 1:closing_index]
                ).rstrip("\r\n")
            else:
                # Preserve the content if the model forgot the closing
                # fence rather than discarding the end of the file.
                content = "".join(
                    lines[opening_index + 1:]
                ).rstrip("\r\n")
        else:
            content = section.strip("\r\n")

        if name in files:
            # Don't silently overwrite a duplicate file in one response.
            suffix = 2
            original = name

            while name in files:
                path = PurePosixPath(original)
                name = str(
                    path.with_name(
                        f"{path.stem}_{suffix}{path.suffix}"
                    )
                )
                suffix += 1

        files[name] = content

        if len(files) >= MAX_FILES:
            break

    return files


# ==================================================
# DISPLAY HELPERS
# ==================================================

def split_output(text, limit=MAX_EMBED_CHARS):
    """Split display text without dropping characters."""

    text = text or ""

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

        chunks.append(text[:cut])
        text = text[cut:]

    return chunks


async def send_embeds(message, text, title="Veyra Code Pro"):
    """Send ordinary status or project-tree text as embeds."""

    chunks = split_output(text)
    total = len(chunks)

    for index, chunk in enumerate(chunks, start=1):
        embed = discord.Embed(
            title=f"{title} • {index}/{total}",
            description=chunk,
            color=discord.Color.blurple(),
        )

        embed.set_footer(
            text="Generated by Veyra Code Pro • Review before running"
        )

        if index == 1:
            await message.reply(
                embed=embed,
                mention_author=False,
            )
        else:
            await message.channel.send(embed=embed)


# ==================================================
# FILE DELIVERY
# ==================================================

def build_zip(files):
    """Build an in-memory ZIP containing the complete extracted files."""

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for name, content in files.items():
            archive.writestr(name, content)

    buffer.seek(0)
    return buffer


async def send_file_attachments(message, files):
    """
    Send complete source files as attachments.

    Small projects are sent as individual files. Larger projects are
    packaged into a ZIP, avoiding embed splitting of source code.
    """

    if not files:
        return False

    total_bytes = sum(
        len(content.encode("utf-8"))
        for content in files.values()
    )

    if total_bytes > MAX_PROJECT_BYTES:
        await message.channel.send(
            "⚠️ The generated project is too large to attach in one "
            "delivery. Reduce the requested project size and try again."
        )
        return False

    if len(files) == 1:
        name, content = next(iter(files.items()))
        data = content.encode("utf-8")

        if len(data) <= MAX_ATTACHMENT_BYTES:
            attachment = discord.File(
                io.BytesIO(data),
                filename=PurePosixPath(name).name,
            )

            await message.channel.send(
                content=f"📄 Complete file: `{name}`",
                file=attachment,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return True

    # ZIP delivery preserves directory structure and complete file data.
    zip_buffer = build_zip(files)

    if zip_buffer.getbuffer().nbytes > MAX_ATTACHMENT_BYTES:
        await message.channel.send(
            "⚠️ The project ZIP exceeds the configured attachment size. "
            "Try requesting a smaller project."
        )
        return False

    attachment = discord.File(
        zip_buffer,
        filename="veyra_code_project.zip",
    )

    await message.channel.send(
        content=(
            f"📦 Complete project attached "
            f"({len(files)} files). Extract the ZIP to use the files."
        ),
        file=attachment,
        allowed_mentions=discord.AllowedMentions.none(),
    )

    return True


async def send_output(message, response):
    """
    Deliver generated output.

    Recognized file-labelled responses are sent as actual files.
    The project tree is displayed in embeds. Unrecognized output is
    preserved as text rather than guessed into files.
    """

    files = extract_files(response)

    if files:
        tree_match = re.search(
            r"(?ms)^[ \t]*```(?:text|tree)?[ \t]*\r?\n"
            r"(.*?)^[ \t]*```[ \t]*$",
            response,
        )

        if tree_match:
            tree = tree_match.group(1).strip()
            if tree:
                await send_embeds(
                    message,
                    tree,
                    title="Project Structure",
                )

        delivered = await send_file_attachments(message, files)

        if delivered:
            return

        # If attachments fail or exceed limits, provide a clear warning.
        await send_embeds(
            message,
            (
                "The generated files were recognized, but attachment "
                "delivery did not complete. Please retry with a smaller "
                "project. No claim is made that the files were delivered."
            ),
            title="Delivery Notice",
        )
        return

    # No reliable file boundaries: preserve the model response as text.
    await send_embeds(
        message,
        response,
        title="Veyra Code Pro Output",
    )


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
        "the relevant code clearly, then provide the requested files."
        if explanation_requested
        else (
            "CODE-ONLY OUTPUT: no greeting, introduction, conversation, "
            "or explanation. Output the project tree followed by files."
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
1. For multi-file projects, begin with a compact project tree.
2. Label every file on its own line exactly as:
   FILE: path/to/file.ext
3. Put each file's complete contents in one Markdown code fence.
4. Use an outer fence longer than any Markdown fence inside the file.
   For example, use four backticks around a README containing triple
   backticks. Do not alter the actual file content.
5. Never split a file into numbered response parts.
6. Never insert phrases like "Part 2 response" into a file.
7. Never omit code, docstrings, imports, closing brackets, or file endings.
8. Never replace required code with placeholders or ellipses.
9. For follow-up changes, output changed files only unless asked for all.
10. Keep paths relative to the project root.
11. Do not repeat a FILE label for the same file.
12. Never claim code was executed, tested, or deployed unless it was.
13. Never claim to have modified the user's repository or device.
14. Never execute generated code on the bot host.
15. Never reveal API keys, passwords, or private credentials.
16. Do not generate malware or harmful code.
17. If you cannot fit the requested implementation into one response,
    clearly say so instead of fabricating complete files.

SUPPORTED PROJECTS
Websites, Android apps, Discord bots, Python tools, robotics software,
and space-technology software.
"""


# ==================================================
# MAIN HANDLER
# ==================================================

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

        files = extract_files(response)

        # Persist project state independently of normal chat memory.
        update_project(
            message,
            prompt,
            response,
            files=files or None,
        )

        try:
            await status.delete()
        except discord.HTTPException:
            pass

        await send_output(message, response)

    except asyncio.TimeoutError:
        try:
            await status.edit(
                content=(
                    "⏳ Code generation timed out. "
                    "Please try again with a smaller request."
                )
            )
        except discord.HTTPException:
            pass

    except Exception as exc:
        print(
            f"[CODE PRO ERROR] {type(exc).__name__}: {exc}"
        )

        try:
            await status.edit(
                content=(
                    "⚠️ Code generation or delivery failed. "
                    "The model may be busy, rate-limited, or the "
                    "attachment may exceed Discord's upload limit. "
                    "Please try again with a smaller request."
                )
            )
        except discord.HTTPException:
            pass

    return True
