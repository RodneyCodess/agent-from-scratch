# agent-from-scratch

A tool-using LLM agent built without any agent framework — no LangChain, no orchestration library. Raw Anthropic API calls and a hand-written loop. The point is to understand the machinery frameworks hide: how a model requests a tool, how results get fed back, and where the real engineering problems live.

**Status:** Weeks 1–2 done (tools, error handling, turn limits, file logging, approval gates). Week 3 (context management) is next.

## Setup

Requires Python 3.9+ and an Anthropic API key with credits (a Claude Pro/Max subscription does not cover API usage — separate billing).

```bash
python3 -m venv .venv
source .venv/Scripts/activate    # Windows/Git Bash; use bin/activate on macOS/Linux
pip install anthropic requests
export ANTHROPIC_API_KEY="sk-ant-..."
python agent.py
```

The task is hardcoded as the first entry in the `messages` list in `agent.py` — there is no CLI or interactive prompt, so editing the source is the only way to change what the agent does. `hello.py` is a minimal no-tools API call, kept deliberately as a smoke test to isolate environment problems from loop bugs.

## Tools

| Tool | Arguments | Approval | Notes |
|---|---|---|---|
| `read_file` | `file_path` | no | Returns contents, or an `Error:` string |
| `write_file` | `file_path`, `content` | **yes** | Overwrites, returning old contents in the result if under 500 lines |
| `shell_exec` | `commands` | **yes** | bash via `subprocess`, 30s timeout, output capped at 5000 chars per stream |
| `gh_list_issues` | `repo`, `state` | no | Read-only GitHub API call, up to 10 issues, PRs excluded |

## How it works

The agent is a `for turn in range(10)` loop around one API call. Each pass sends the whole conversation plus the tool schemas, then branches on `stop_reason`: `end_turn` prints the answer and breaks, `tool_use` means work to do. Every block in `response.content` is scanned for tool calls — a single response can contain several — each is dispatched by `block.name`, and all results are appended as one `tool_result` message before looping. The loop's `else` clause fires if the turn ceiling is hit without finishing.

There is no server-side memory. The `messages` list is the entire state and gets re-sent every turn, so token cost grows superlinearly with turn count. Tool schemas and Python functions aren't linked by anything except the dispatch code — the schema is a prompt the model reads, so its wording is behavior rather than documentation. Errors are returned as strings starting with `Error:` rather than raised, so the model can read the failure and recover instead of the process dying.

Every run writes a timestamped JSONL file to `logs/` — one line per event (`run_start`, `turn_start`, `model_response`, `tool_call`, `approval`, `tool_result`, `shell_raw`, `final_answer`, `max_tokens_hit`, `max_turns_hit`) — so a run can be reconstructed after the fact even though only the final answer prints to stdout.

## Findings

**The model cannot count reliably.** Asked to count lines in a file, it returned 38, enumerated 40 in its own explanation, and `wc -l` said 41. File contents came back verbatim, so retrieval was fine and the arithmetic wasn't. Deterministic work belongs in code — this is the argument for the shell tool.

**Approval gates must precede the action, not follow it.** The first version of the write gate called `write_file` and *then* asked for approval, so denial only changed the string the model saw while the file was already overwritten. Worse than no gate, since it desynced the conversation from the filesystem.

**Truncation budgets should be per-stream, not per-message.** Capping the combined output would let a noisy stdout consume the entire budget and drop stderr — which is usually the part that explains the failure.

**Nonzero exit codes are information, not errors.** `grep` exits 1 on no matches. Wrapping every nonzero exit in `Error:` would teach the model that successful searches failed.

**The final answer assumes the last content block is text.** `response.content[-1].text` on `end_turn` will raise if the model ever ends on a non-text block, or silently drop earlier text if the model emits more than one block. Not yet observed, but it's an untested assumption.

## Known limitations

- **`shell_exec` is not sandboxed.** It runs arbitrary commands with the user's full privileges. The only safeguard is a human approval prompt before execution, not process isolation — a `y` on a bad command still does full damage. Docker or a restricted user is the real fix, not yet built.
- **Approval logic is duplicated**, not centralized. `write_file` and `shell_exec` each have their own copy of the "print preview, `input()`, log, branch" code instead of a shared gate driven by a lookup (e.g. a `NEEDS_APPROVAL` set) — adding a fifth destructive tool means writing the same block again and hoping it matches.
- **The task is hardcoded** in `messages`, not interactive. There is no CLI, no way to pass a task at runtime, and no loop for follow-up input after the agent finishes.
- Approval previews for `write_file` truncate at 300 characters, so long writes are partly approved blind; `shell_exec` previews the full command with no truncation.
- `gh_list_issues` is the only external-data tool and is GitHub-specific — there is no general web search.
- No context management yet: the full message history is resent every turn with no summarization or pruning, so long runs get expensive and will eventually hit the context window.

## Roadmap

- **Week 3** — token accounting per turn, summarization of old tool results, core/working/droppable context policy tested against a task large enough to overflow the window.
- **Week 4** — 20–30 eval tasks with assertable pass/fail criteria, measured pass rate, root-cause analysis of the worst failures.
