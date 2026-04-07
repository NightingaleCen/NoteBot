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
    base_ref = repo.get_git_ref(f"refs/heads/{base_branch}")
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_ref.object.sha)
    return branch_name


def append_section_to_content(content: str, date_str: str, latex_items: str) -> str:
    section_pattern = rf"(\\section\*\{{{re.escape(date_str)}\}})"
    match = re.search(section_pattern, content)

    if match:
        section_end = match.end()
        next_section = re.search(r"\\section\*\{", content[section_end:])
        if next_section:
            insert_pos = section_end + next_section.start()
        else:
            insert_pos = len(content)

        existing_items_end = content.find("\\end{itemize}", section_end)
        if existing_items_end != -1:
            insert_pos = existing_items_end
            items_content = content[section_end:existing_items_end].rstrip()
            if items_content.strip():
                new_items = "\n" + latex_items.strip()
            else:
                new_items = latex_items.strip()
        else:
            new_items = f"\n\\begin{{itemize}}\n{latex_items.strip()}\n\\end{{itemize}}"

        new_content = content[:insert_pos] + new_items + content[insert_pos:]
    else:
        new_section = f"\\section*{{{date_str}}}\n\\begin{{itemize}}\n{latex_items.strip()}\n\\end{{itemize}}\n"
        if content.strip():
            new_content = content.rstrip() + "\n" + new_section
        else:
            new_content = new_section

    return new_content


async def push_and_create_pr(
    repo, file_path: str, date_str: str, latex_items: str, base_branch: str = "main"
) -> str:
    content = get_file_content(repo, file_path)
    new_content = append_section_to_content(content, date_str, latex_items)

    branch_name = create_new_branch(repo, base_branch)

    repo.create_file(
        path=file_path,
        message=f"Update notes for {date_str}",
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
