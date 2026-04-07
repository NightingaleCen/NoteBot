from openai import OpenAI
from config import LLM_API_KEY, LLM_MODEL, LLM_BASE_URL

client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
)

SYSTEM_PROMPT = """You are a professional note-taking assistant. Your task is to transform conversation records into clean LaTeX formatted notes.

Output format requirements:
- Use \\section*{{YYYY-MM-DD}} for the date header
- Use \\begin{{itemize}} and \\item for bullet points
- Keep language plain and concise unless user requests detail
- If the conversation contains specific topics, focus on those topics
- If user instruction is empty, summarize the key discussion points
- Output ONLY the LaTeX code, no explanations or markdown fences"""


def generate_notes(chat_history: str, user_instruction: str, date_str: str) -> str:
    if not chat_history:
        return f"\\section*{{{date_str}}}\n\\begin{{itemize}}\n\\item (No messages found for today)\n\\end{{itemize}}"

    user_instruct_text = (
        f"\n\nUser's specific instruction: {user_instruction}"
        if user_instruction
        else ""
    )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Today's conversation:\n{chat_history}{user_instruct_text}",
            },
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    return response.choices[0].message.content.strip()
