import re
import config
from messages import get_today_messages, format_chat_for_llm, get_local_date_str
from llm import generate_notes
from views import ConfirmView
from github_utils import push_and_create_pr, get_repo


intents = config.discord.Intents.default()
intents.message_content = True
client = config.discord.Client(intents=intents)


def extract_instruction(content: str, bot_name: str) -> str:
    pattern = rf"<@!?\d+>\s*(.+)"
    match = re.match(pattern, content)
    if match:
        return match.group(1).strip()
    return ""


async def edit_callback(interaction, latex_content: str):
    repo = get_repo()
    date_str = get_local_date_str(config.LOCAL_TIMEZONE)
    user = interaction.user

    await interaction.message.edit(
        content=f"⏳ {user.mention} Pushing your edited notes...",
        view=None,
    )

    pr_url = await push_and_create_pr(repo, config.FILE_PATH, date_str, latex_content)
    await interaction.message.edit(content=f"✅ Merged! PR: {pr_url}")


async def confirm_callback(interaction):
    repo = get_repo()
    date_str = get_local_date_str(config.LOCAL_TIMEZONE)
    message = interaction.message
    view: ConfirmView = message.view
    latex_content = view.latex_content

    await interaction.message.edit(content="⏳ Creating PR and merging...", view=None)

    pr_url = await push_and_create_pr(repo, config.FILE_PATH, date_str, latex_content)
    await interaction.message.edit(content=f"✅ Merged! PR: {pr_url}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    bot_id = client.user.id
    if not re.search(rf"<@!?{bot_id}>", message.content):
        return

    user_instruction = extract_instruction(message.content, client.user.name)

    await message.channel.typing()

    messages = await get_today_messages(message.channel, config.LOCAL_TIMEZONE)

    if not messages:
        await message.reply("No messages found today.")
        return

    chat_history = format_chat_for_llm(messages)
    date_str = get_local_date_str(config.LOCAL_TIMEZONE)
    latex_content = generate_notes(chat_history, user_instruction, date_str)

    view = ConfirmView(
        latex_content=latex_content,
        date_str=date_str,
        edit_callback=edit_callback,
        confirm_callback=confirm_callback,
    )

    await message.reply(f"**Preview for {date_str}:**\n```latex\n{latex_content}\n```")
    await message.reply("Choose an action:", view=view)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


if __name__ == "__main__":
    client.run(config.DISCORD_TOKEN)
