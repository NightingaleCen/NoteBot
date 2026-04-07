import re
from openai import OpenAI
from config import LLM_API_KEY, LLM_MODEL, LLM_BASE_URL

client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
)

SECRETARY_SYSTEM_PROMPT = """You are a helpful assistant and note-taking secretary in a team's Discord channel.

You help the team with discussions, questions, and analysis. You also take notes when asked.

You have access to a take_notes tool.
Call it ONLY when the user's intent is to PERSIST something — they want to save, record, or write something into a notes file.
Do NOT call it when the user's intent is to RETRIEVE, DISCUSS, or ANALYZE — even if the topic is about today's conversation or a summary.

Examples of when to call take_notes:
- "take notes" / "record this" / "add this to the notes"
- "save this for later" / "write this down"
- "put today's discussion into the notes"

Examples of when NOT to call take_notes:
- "summarize today" (just summarize, don't save)
- "what did we discuss today" (retrieval)
- "help me review this code" (analysis)
- Casual questions or greetings

Be concise and direct in your replies."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "take_notes",
            "description": "Save a summary of today's conversation as LaTeX notes into the team's notes file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "Optional specific instruction about what to focus on or how to format the notes.",
                    }
                },
                "required": [],
            },
        },
    }
]

LATEX_SYSTEM_PROMPT_NEW_SECTION = """You are a precise note-taking assistant. Convert the provided conversation into LaTeX notes.

Output format — a complete new section:
\\section*{{DATE}}
\\begin{{itemize}}
    \\item ...
    \\item ...
\\end{{itemize}}

Rules:
- Replace DATE with the date provided by the user
- Use \\item for each distinct point
- Nested sub-points use \\begin{{itemize}} / \\end{{itemize}} inside an \\item
- Language: plain and concise English; add detail only if the user requests it
- Focus on decisions, conclusions, and actionable points
- Output ONLY the LaTeX code, no markdown fences, no explanations

Example output:
\\section*{{2026-03-29}}
\\begin{{itemize}}
    \\item SFT may work better than LoRA for the 150M model since saving compute is not a priority. Plan to train with both and compare after pipeline is set up.
    \\item VSCode extension for Modelica is available.
    \\item Evaluation:
    \\begin{{itemize}}
        \\item Set up a reusable Python script for API calls; can be tuned for edge cases later.
        \\item Add a secondary check: verify simulation outputs match expected results.
        \\item Optionally benchmark models after minor fine-tuning to identify which adapts better.
    \\end{{itemize}}
\\end{{itemize}}"""

LATEX_SYSTEM_PROMPT_APPEND = """You are a precise note-taking assistant. Convert the provided conversation into LaTeX note items to be appended to an existing section.

Output format — items only, no section header:
    \\item ...
    \\item ...

Rules:
- No \\section, no \\begin{{itemize}}, no \\end{{itemize}} — items only
- Nested sub-points use \\begin{{itemize}} / \\end{{itemize}} inside an \\item
- Language: plain and concise English; add detail only if the user requests it
- Focus on decisions, conclusions, and actionable points
- Output ONLY the \\item lines, no markdown fences, no explanations

Example output:
    \\item SFT may work better than LoRA for the 150M model since saving compute is not a priority. Plan to train with both and compare after pipeline is set up.
    \\item VSCode extension for Modelica is available.
    \\item Evaluation:
    \\begin{{itemize}}
        \\item Set up a reusable Python script for API calls; can be tuned for edge cases later.
        \\item Add a secondary check: verify simulation outputs match expected results.
        \\item Optionally benchmark models after minor fine-tuning to identify which adapts better.
    \\end{{itemize}}"""


def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def chat(user_message: str, chat_history: str, date_str: str) -> dict:
    """
    First LLM call: secretary role with tool calling.
    Returns:
      {"type": "reply", "content": "..."}
      {"type": "take_notes", "instruction": "..."}
    """
    messages = [
        {"role": "system", "content": SECRETARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"[Today's conversation context — {date_str}]\n{chat_history}\n\n"
                f"[Current request from user]\n{user_message}"
            ),
        },
    ]

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.3,
    )

    msg = response.choices[0].message

    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        import json

        args = (
            json.loads(tool_call.function.arguments)
            if tool_call.function.arguments
            else {}
        )
        return {
            "type": "take_notes",
            "instruction": args.get("instruction", ""),
        }

    content = _strip_thinking(msg.content or "")
    return {"type": "reply", "content": content}


def generate_latex(
    chat_history: str,
    instruction: str,
    date_str: str,
    has_section: bool,
) -> str:
    """
    Second LLM call: pure LaTeX generation.
    has_section=True  → output \item lines only
    has_section=False → output full \section*{date}...\end{itemize}
    """
    system_prompt = (
        LATEX_SYSTEM_PROMPT_APPEND if has_section else LATEX_SYSTEM_PROMPT_NEW_SECTION
    )

    instruction_text = f"\n\nSpecific instruction: {instruction}" if instruction else ""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Date: {date_str}\n\n"
                    f"Conversation:\n{chat_history}"
                    f"{instruction_text}"
                ),
            },
        ],
        temperature=0.2,
        max_tokens=4096,
    )

    raw = response.choices[0].message.content or ""
    return _strip_thinking(raw).strip()
