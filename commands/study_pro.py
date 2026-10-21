
import asyncio
import discord

from commands.products import get_tier, ICE_BLUE
from ai_client import ask_veyra


STUDY_ACTIONS = {
    "explain": {
        "label": "Explain a Topic",
        "emoji": "💡",
        "free": True,
    },
    "notes": {
        "label": "Chapter Notes",
        "emoji": "📝",
        "free": True,
    },
    "quiz": {
        "label": "Practice Quiz",
        "emoji": "🎯",
        "free": True,
    },
    "plan": {
        "label": "Revision Plan",
        "emoji": "📅",
        "free": False,
    },
}


def study_embed(user_id, server_name):
    tier = get_tier(user_id, "study")
    is_pro = tier == "pro"

    embed = discord.Embed(
        title="📚 Study Pro | Learning Workspace",
        description=(
            "*Turn difficult topics into clear knowledge.*\n\n"
            f"**Account:** {'⚡ PRO' if is_pro else '🆓 FREE'}\n"
            f"**Server:** {server_name}\n\n"
            "Choose a study tool below to get started."
        ),
        color=ICE_BLUE,
    )

    embed.add_field(
        name="💡 Learn",
        value=(
            "Understand difficult concepts with clear explanations "
            "and examples."
        ),
        inline=False,
    )

    embed.add_field(
        name="📝 Revise",
        value=(
            "Create chapter notes, key definitions, and important "
            "points for revision."
        ),
        inline=False,
    )

    embed.add_field(
        name="🎯 Practise",
        value=(
            "Test your understanding with questions and answers."
        ),
        inline=False,
    )

    embed.add_field(
        name="⚡ Pro tools",
        value=(
            "Detailed revision plans, extended quizzes, and "
            "structured chapter notes."
            if is_pro
            else "Revision plans and extended study tools are "
                 "available with Study Pro."
        ),
        inline=False,
    )

    embed.set_footer(
        text="VEYRA STUDY • POWERED BY VOLBASTY STUDIOS"
    )

    return embed


class StudyView(discord.ui.View):
    def __init__(self, user_id, server_name):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.server_name = server_name

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This study workspace belongs to another user. "
                "Run `!veyra study` to open your own.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        label="Explain",
        emoji="💡",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def explain(self, interaction, button):
        await interaction.response.send_modal(
            StudyPromptModal("explain")
        )

    @discord.ui.button(
        label="Chapter Notes",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def notes(self, interaction, button):
        await interaction.response.send_modal(
            StudyPromptModal("notes")
        )

    @discord.ui.button(
        label="Quiz",
        emoji="🎯",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def quiz(self, interaction, button):
        await interaction.response.send_modal(
            StudyPromptModal("quiz")
        )

    @discord.ui.button(
        label="Revision Plan",
        emoji="📅",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def plan(self, interaction, button):
        if get_tier(self.user_id, "study") != "pro":
            await interaction.response.send_message(
                "⚡ **Study Pro feature**\n"
                "Revision plans are available to Study Pro users. "
                "Ask the bot owner about access.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            StudyPromptModal("plan")
        )


class StudyPromptModal(discord.ui.Modal):
    def __init__(self, action):
        self.action = action

        details = STUDY_ACTIONS[action]

        super().__init__(
            title=details["label"],
            timeout=300,
        )

        self.topic = discord.ui.TextInput(
            label="Subject and topic",
            placeholder="e.g. Class 11 Economics — Demand",
            required=True,
            max_length=500,
            style=discord.TextStyle.short,
        )

        self.instructions = discord.ui.TextInput(
            label="Extra instructions (optional)",
            placeholder=(
                "e.g. simple English, Hindi, 5 questions..."
            ),
            required=False,
            max_length=500,
            style=discord.TextStyle.paragraph,
        )

        self.add_item(self.topic)
        self.add_item(self.instructions)

    async def on_submit(self, interaction):
        user_id = interaction.user.id
        tier = get_tier(user_id, "study")

        if self.action == "plan" and tier != "pro":
            await interaction.response.send_message(
                "This action requires Study Pro access.",
                ephemeral=True,
            )
            return

        topic = self.topic.value.strip()
        extra = self.instructions.value.strip()

        prompts = {
            "explain": (
                "Teach the following topic like a patient school tutor. "
                "Start with a simple explanation, then give a practical "
                "example, important terms, and a short recap. "
                "Avoid unsupported claims."
            ),
            "notes": (
                "Create useful school revision notes for the requested "
                "topic. Use headings, concise bullet points, key terms, "
                "definitions, examples, and a recap. "
                + (
                    "Provide comprehensive, well-structured notes."
                    if tier == "pro"
                    else "Keep the notes concise and focused on essentials."
                )
            ),
            "quiz": (
                "Create a practice quiz for the requested school topic. "
                "Include 5 questions for Free users or 15 questions for "
                "Pro users. Mix question types where appropriate. "
                "Put the answer key at the end so the learner can try "
                "first. Do not claim the questions are official exam "
                "questions."
            ),
            "plan": (
                "Create a realistic revision plan for the topic. "
                "Break it into manageable sessions, include active "
                "recall, practice questions, and spaced revision. "
                "Ask no follow-up questions; state reasonable assumptions "
                "if the available time was not specified."
            ),
        }

        system_prompt = (
            "You are Veyra Study, a supportive educational tutor. "
            "Help students learn rather than merely memorize. "
            "Use clear formatting and age-appropriate explanations. "
            "Do not invent textbook quotations, syllabus requirements, "
            "or exam predictions. If the board or syllabus is unknown, "
            "make that limitation clear. "
            f"User tier: {tier.upper()}.\n\n"
            f"Task: {prompts[self.action]}"
        )

        user_prompt = f"Topic: {topic}"

        if extra:
            user_prompt += f"\nAdditional instructions: {extra}"

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            answer = await ask_veyra(
                prompt=f"{system_prompt}\n\n{user_prompt}",
                mode="deep" if tier == "pro" else "chat",
                web_search=False,
            )

            answer = str(answer or "").strip()

            if not answer:
                answer = (
                    "I couldn't generate the study material. "
                    "Please try again."
                )

            # Discord embed descriptions have a 4096-character limit.
            chunks = [
                answer[index:index + 3800]
                for index in range(0, len(answer), 3800)
            ]

            for index, chunk in enumerate(chunks):
                embed = discord.Embed(
                    title=(
                        f"{STUDY_ACTIONS[self.action]['emoji']} "
                        f"{STUDY_ACTIONS[self.action]['label']}"
                        + (
                            f" · Part {index + 1}/{len(chunks)}"
                            if len(chunks) > 1
                            else ""
                        )
                    ),
                    description=chunk,
                    color=ICE_BLUE,
                )

                embed.set_footer(
                    text=f"STUDY {tier.upper()} • VEYRA AI"
                )

                if index == 0:
                    await interaction.followup.send(
                        embed=embed,
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        embed=embed,
                        ephemeral=True,
                    )

        except Exception as error:
            print(
                f"[STUDY ERROR] {type(error).__name__}: {error}",
                flush=True,
            )

            await interaction.followup.send(
                "⚠️ Study Pro couldn't complete this request. "
                "Please try again in a moment.",
                ephemeral=True,
            )


async def handle_study_workspace(message):
    if message.guild is None:
        await message.reply(
            "Please open Study from a Discord server.",
            mention_author=False,
        )
        return

    loading = discord.Embed(
        title="❄️ VEYRA STUDY",
        description=(
            "```ansi\n"
            "\u001b[1;36mPREPARING YOUR STUDY WORKSPACE\u001b[0m\n"
            "```\n"
            "◈ Checking your Study access...\n"
            "◈ Preparing learning tools...\n"
            "◈ Setting up your workspace..."
        ),
        color=ICE_BLUE,
    )

    reply = await message.reply(
        embed=loading,
        mention_author=False,
    )

    await asyncio.sleep(4.5)

    view = StudyView(
        message.author.id,
        message.guild.name,
    )

    await reply.edit(
        embed=study_embed(
            message.author.id,
            message.guild.name,
        ),
        view=view,
    )
