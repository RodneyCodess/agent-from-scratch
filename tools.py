import os
import subprocess
import requests
from agent_log import log

MAX_OUTPUT = 5000


# ===BELOW ARE THE TOOL SCHEMAS===
# read file tool
rf_tool = {
    "name": "read_file",
    "description": (
        "Reads the contents of a file and returns it. "
        "If the file does not exist, returns an error message beginning with 'Error:' rather than failing — "
        "read it and try a corrected path."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "Path relative to the project root, using forward slashes. "
                )
            }
        },
        "required": ["file_path"]
    }
}

wf_tool = {
    "name": "write_file",
    "description": (
        "Writes text to a file at the given path, creating it if it does not exist. "
        "Returns the number of characters and lines written on success. "
        "If the file already exists, overwrites it but return the file with the old contents in the success message. "
        "Returns a message beginning with 'Error:' if the write fails — "
        "most commonly because permission issues or directory does not exist. "
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "Path relative to the project root, using forward slashes. "
                )
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file."
            }
        },
        "required": ["file_path", "content"]
    }
}

se_tool = {
    "name": "shell_exec",
    "description": (
        "Runs one or more shell commands and returns their output. "
        "Commands execute in a bash shell with the project root as the working directory. "
        "Returns the exit code, then stdout, then stderr, in labelled sections. "
        "A nonzero exit code is reported, not treated as a failure — some commands "
        "exit nonzero as a normal result (grep exits 1 when it finds no matches). "
        "Output longer than 5000 characters is truncated, and the result says so. "
        "Commands are killed after 30 seconds, returning a message beginning with 'Error:'. "
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "commands": {
                "type": "string",
                "description": (
                    "The command line to run. Pipes, redirects, and chaining with && "
                    "are supported. Example: 'grep -rn TODO . | head -20'"
                )
            }
        },
        "required": ["commands"]
    }
}

gh_issues = {
    "name": "gh_list_issues",
    "description": (
        "Lists issues on a public GitHub repository. Returns up to 10 issues, "
        "each as a block: '#<number> [<state>] <title>' followed by the issue body, "
        "clipped to 300 characters. Blocks are separated by blank lines. "
        "Pull requests are excluded. "
        "If the repository has no matching issues, returns a message saying so — "
        "this is a valid result, not a failure. "
        "Returns a message beginning with 'Error:' on failure. A 404 means the repo "
        "was not found or is private; check the owner/name spelling rather than retrying "
        "the same request. A rate-limit error means the request quota is exhausted; "
        "report this and do not retry. A network error may be transient and is worth "
        "retrying once."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in 'owner/name' form. Example: 'anthropics/anthropic-sdk-python'"
            },
            "state": {
                "type": "string",
                "description": "Which issues to return: 'open', 'closed', or 'all'. Defaults to 'open'."
            }
        },
        "required": ["repo"]
    }
}


# ===BELOW ARE THE TOOL FUNCTIONS===


def gh_list_issues(repo, state="open"):
    url = f"https://api.github.com/repos/{repo}/issues"
    params = {"state": state, "per_page": 10}
    headers = {"Accept": "application/vnd.github+json"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
    except requests.exceptions.RequestException as e:
        return f"Error: could not fetch issues from '{repo}': {e}"

    if r.status_code == 404:
        return f"Error: repository '{repo}' not found or is private."
    if r.status_code == 403:
        return "Error: GitHub rate limit exceeded. Do not retry."
    if r.status_code != 200:
        return f"Error: GitHub returned {r.status_code}: {r.text[:200]}"

    issues = r.json()

    blocks = []
    for issue in issues:
        if "pull_request" in issue:
            continue

        number = issue.get("number")
        title = issue.get("title")
        issue_state = issue.get("state")

        body = issue.get("body")
        if body is not None:
            body = body[:300].replace("\n", " ")
        else:
            body = "No body provided."

        blocks.append(f"#{number} [{issue_state}] {title}: {body}")

    if not blocks:
        return f"No {state} issues found in '{repo}'."

    return "\n\n".join(blocks)


def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        return f"Error: could not read '{file_path}': {e}"


def write_file(file_path, content):
    content_lines = content.count('\n') + (0 if content.endswith('\n') else 1)
    old_contents = None
    if os.path.exists(file_path):
        old_contents = read_file(file_path)
        lines = len(old_contents.splitlines())
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            chars_written = file.write(content)
            if old_contents is not None:
                if lines >= 500:
                    return f"file path already exists and overwritten {lines} of old content - success with {chars_written} characters and {content_lines} lines written"
                return f"file path already existed and was overwritten, \n--- previous contents \n{old_contents}\n--- end of previous contents\n - success with {chars_written} characters and {content_lines} lines written"
            else:
                return f"{file_path} was written with {chars_written} characters and {content_lines} lines written"
    except Exception as e:
        return f"Error: could not write '{file_path}': {e}"


def shell_exec(commands):

    try:
        completed = subprocess.run(
            commands,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        log("shell_raw",
            commands=commands,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr)

    except subprocess.TimeoutExpired:
        log("shell_timeout", commands=commands, timeout=30)
        return f"Error: command timed out after 30 seconds: {commands}"
    except Exception as e:
        log("shell_error", commands=commands, error=str(e))
        return f"Error: could not run '{commands}': {e}"

    exit_code = completed.returncode
    stdout = completed.stdout
    stderr = completed.stderr

    if len(stdout) > MAX_OUTPUT:
        stdout = stdout[:MAX_OUTPUT] + f"\n... [truncated, {len(stdout)} chars total]"
    elif len(stdout) == 0:
        stdout = "(empty)"

    if len(stderr) > MAX_OUTPUT:
        stderr = stderr[:MAX_OUTPUT] + f"\n... [truncated, {len(stderr)} chars total]"
    elif len(stderr) == 0:
        stderr = "(empty)"

    labeled_string = f"exit code {exit_code}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"

    return labeled_string


TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "shell_exec": shell_exec,
    "gh_list_issues": gh_list_issues,
}

SCHEMAS = [rf_tool, wf_tool, se_tool, gh_issues]

NEEDS_APPROVAL = {"write_file", "shell_exec"}
