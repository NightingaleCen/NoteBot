import re
from datetime import datetime
from github import Github
from config import GITHUB_TOKEN, REPO_NAME, FILE_PATH


def get_github_client():
    return Github(GITHUB_TOKEN)


def get_repo():
    client = get_github_client()
    return client.get_repo(REPO_NAME)


def get_file_content(repo, path: str) -> str:
    try:
        file = repo.get_contents(path)
        return file.decoded_content.decode("utf-8")
    except Exception:
        return ""


def file_exists(repo, path: str) -> bool:
    try:
        repo.get_contents(path)
        return True
    except Exception:
        return False


def create_branch_name() -> str:
    return f"note-update-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def create_new_branch(repo, base_branch: str = "main"):
    branch_name = create_branch_name()
    base_sha = repo.get_branch(base_branch).commit.sha
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
    return branch_name


def _find_matching_end_itemize(text: str, start: int) -> int:
    depth = 0
    pos = start
    while pos < len(text):
        next_begin = re.search(r"\\begin\{itemize\}", text[pos:])
        next_end = re.search(r"\\end\{itemize\}", text[pos:])
        if next_end is None:
            return -1
        if next_begin is not None and next_begin.start() < next_end.start():
            depth += 1
            pos += next_begin.end()
        else:
            if depth == 0:
                return pos + next_end.start()
            depth -= 1
            pos += next_end.end()
    return -1


def extract_items(latex_content: str) -> str:
    content = latex_content.strip()
    content = re.sub(r"^\\section\*\{[^}]*\}\s*", "", content, count=1)
    begin_match = re.search(r"\\begin\{itemize\}", content)
    if begin_match:
        end_pos = _find_matching_end_itemize(content, begin_match.end())
        if end_pos != -1:
            items = content[begin_match.end() : end_pos]
            return items.strip()
    return content.strip()


def check_section_exists(content: str, date_str: str) -> bool:
    pattern = rf"\\section\*\{{{re.escape(date_str)}\}}"
    return bool(re.search(pattern, content))


def append_section_to_content(content: str, date_str: str, latex_items: str) -> str:
    if not content.strip():
        return (
            "\\documentclass{article}\n\n"
            "\\begin{document}\n"
            f"\\section*{{{date_str}}}\n"
            f"\\begin{{itemize}}\n"
            f"{latex_items.strip()}\n"
            f"\\end{{itemize}}\n\n"
            "\\end{document}\n"
        )

    doc_end_match = re.search(r"\\end\{document\}", content)
    doc_end_pos = doc_end_match.start() if doc_end_match else len(content)

    section_pattern = rf"\\section\*\{{{re.escape(date_str)}\}}"
    section_match = re.search(section_pattern, content)

    if section_match:
        section_end = section_match.end()

        next_section = re.search(r"\\section\*\{", content[section_end:])
        section_boundary = (
            section_end + next_section.start() if next_section else doc_end_pos
        )

        section_body = content[section_end:section_boundary]
        begin_match = re.search(r"\\begin\{itemize\}", section_body)

        if begin_match:
            end_pos_relative = _find_matching_end_itemize(
                section_body, begin_match.end()
            )
            if end_pos_relative != -1:
                absolute_pos = section_end + end_pos_relative
                return (
                    content[:absolute_pos]
                    + latex_items.strip()
                    + "\n"
                    + content[absolute_pos:]
                )

        insert_content = (
            f"\n\\begin{{itemize}}\n{latex_items.strip()}\n\\end{{itemize}}\n"
        )
        return content[:section_end] + insert_content + content[section_end:]
    else:
        new_section = f"\n\\section*{{{date_str}}}\n\\begin{{itemize}}\n{latex_items.strip()}\n\\end{{itemize}}\n"
        return content[:doc_end_pos] + new_section + content[doc_end_pos:]


async def push_and_create_pr(
    repo,
    file_path: str,
    date_str: str,
    latex_items: str,
    existing_content: str,
    base_branch: str = "main",
) -> str:
    new_content = append_section_to_content(
        existing_content, date_str, extract_items(latex_items)
    )

    branch_name = create_new_branch(repo, base_branch)

    try:
        file_obj = repo.get_contents(file_path, ref=base_branch)
        repo.update_file(
            path=file_path,
            message=f"Update notes for {date_str}",
            content=new_content,
            sha=file_obj.sha,
            branch=branch_name,
        )
    except Exception:
        repo.create_file(
            path=file_path,
            message=f"Create notes for {date_str}",
            content=new_content,
            branch=branch_name,
        )

    pr = repo.create_pull(
        title=f"Notes update for {date_str}",
        body=f"Automated note update for {date_str}",
        head=branch_name,
        base=base_branch,
    )

    pr.merge()

    return pr.html_url
