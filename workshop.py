import requests

def gh_list_issues(repo, state = "open"):
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

    block = []
    for issue in issues:
        title = issue.get("title")
        number = issue.get("number")
        state = issue.get("state")
        if issue.get("body") != None:
            body = issue.get("body")[:300].replace("\n"," ")
        else:
            body = "No body provided."

        str_block = f"#{number} [{state}] {title}: {body}"
        block.append(str_block)

    return "\n\n".join(block)




print(gh_list_issues("anthropics/anthropic-sdk-python"))
