import re
import traceback
import logging
import config
from messages import get_today_messages, format_chat_for_llm, get_local_date_str
from llm import chat, generate_latex
from views import ConfirmView
from github_utils import (
    push_and_create_pr,
    get_repo,
    get_file_content,
    check_section_exists,
)

logging.basicConfig(level=logging.INFO)

intents = config.discord.Intents.default()
intents.message_content = True
bot = config.discord.Client(intents=intents)


def extract_user_message(content: str) -> str:
    match = re.match(r"<@!?\d+>\s*(.*)", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()


async def execute_take_notes(
    message, instruction: str, chat_history: str, date_str: str
):
    repo = get_repo()
    existing_content = get_file_content(repo, config.FILE_PATH)
    has_section = check_section_exists(existing_content, date_str)

    latex = generate_latex(chat_history, instruction, date_str, has_section)

    async def confirm_callback(interaction):
        await interaction.message.edit(content="Creating PR and merging...", view=None)
        try:
            pr_url = await push_and_create_pr(
                repo, config.FILE_PATH, date_str, latex, existing_content
            )
            await interaction.message.edit(
                content=f"Merged. Please pull the latest notes in the Overleaf project."
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.message.edit(content=f"Error: {e}")

    async def edit_callback(interaction, original_message, edited_latex: str):
        await original_message.edit(content="Pushing edited notes...", view=None)
        try:
            pr_url = await push_and_create_pr(
                repo, config.FILE_PATH, date_str, edited_latex, existing_content
            )
            await original_message.edit(
                content=f"Merged. Please pull the latest notes in the Overleaf project."
            )
        except Exception as e:
            traceback.print_exc()
            await original_message.edit(content=f"Error: {e}")

    view = ConfirmView(
        latex_content=latex,
        date_str=date_str,
        edit_callback=edit_callback,
        confirm_callback=confirm_callback,
    )

    await message.reply(f"**Preview for {date_str}:**\n```latex\n{latex}\n```")
    await message.reply("Confirm or edit:", view=view)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    bot_id = bot.user.id
    if not re.search(rf"<@!?{bot_id}>", message.content):
        return

    user_message = extract_user_message(message.content)
    if not user_message:
        return

    async with message.channel.typing():
        messages = await get_today_messages(message.channel, config.LOCAL_TIMEZONE)
        chat_history = format_chat_for_llm(messages)
        date_str = get_local_date_str(config.LOCAL_TIMEZONE)

        result = chat(user_message, chat_history, date_str)

    if result["type"] == "reply":
        await message.reply(result["content"])
    elif result["type"] == "take_notes":
        await execute_take_notes(
            message,
            instruction=result["instruction"],
            chat_history=chat_history,
            date_str=date_str,
        )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_error(event, *args, **kwargs):
    traceback.print_exc()


if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN)
