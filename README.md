# agent-from-scratch

A tool-using LLM agent built without any agent framework — no LangChain, no orchestration library. Raw Anthropic API calls and a hand-written loop. The point is to understand the machinery frameworks hide: how a model requests a tool, how results get fed back, and where the real engineering problems live.

**Status:** Week 2. Three tools, human approval on destructive actions, turn limit.

## Setup

Requires Python 3.9+ and an Anthropic API key with credits (a Claude Pro/Max subscription does not cover API usage — separate billing).

```bash
python3 -m venv .venv
source .venv/Scripts/activate    # Windows/Git Bash; use bin/activate on macOS/Linux
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
python agent.py
```

The task is hardcoded in the `messages` list in `agent.py` — edit it there. `hello.py` is a minimal no-tools API call, kept deliberately as a smoke test to isolate environment problems from loop bugs.

## Tools

| Tool | Arguments | Approval | Notes |
|---|---|---|---|
| `read_file` | `file_path` | no | Returns contents, or an `Error:` string |
| `write_file` | `file_path`, `content` | **yes** | Overwrites, returning old contents in the result if under 500 lines |
| `shell_exec` | `commands` | **yes** | bash via `subprocess`, 30s timeout, output capped at 5000 chars per stream |

## How it works

The agent is a `for turn in range(10)` loop around one API call. Each pass sends the whole conversation plus the tool schemas, then branches on `stop_reason`: `end_turn` prints the answer and breaks, `tool_use` means work to do. Every block in `response.content` is scanned for tool calls — a single response can contain several — each is dispatched by `block.name`, and all results are appended as one `tool_result` message before looping. The loop's `else` clause fires if the turn ceiling is hit without finishing.

There is no server-side memory. The `messages` list is the entire state and gets re-sent every turn, so token cost grows superlinearly with turn count. Tool schemas and Python functions aren't linked by anything except the dispatch code — the schema is a prompt the model reads, so its wording is behavior rather than documentation. Errors are returned as strings starting with `Error:` rather than raised, so the model can read the failure and recover instead of the process dying.

## Findings

**The model cannot count reliably.** Asked to count lines in a file, it returned 38, enumerated 40 in its own explanation, and `wc -l` said 41. File contents came back verbatim, so retrieval was fine and the arithmetic wasn't. Deterministic work belongs in code — this is the argument for the shell tool.

**Approval gates must precede the action, not follow it.** The first version of the write gate called `write_file` and *then* asked for approval, so denial only changed the string the model saw while the file was already overwritten. Worse than no gate, since it desynced the conversation from the filesystem.

**Truncation budgets should be per-stream, not per-message.** Capping the combined output would let a noisy stdout consume the entire budget and drop stderr — which is usually the part that explains the failure.

**Nonzero exit codes are information, not errors.** `grep` exits 1 on no matches. Wrapping every nonzero exit in `Error:` would teach the model that successful searches failed.

## Known limitations

- **`shell_exec` is not sandboxed.** It runs arbitrary commands with the user's full privileges. Mitigation is human approval plus committed git, not isolation. Docker is the real fix.
- Approval previews truncate at 300 characters, so long writes are partly approved blind.
- Approval logic is duplicated across two branches rather than driven by a `NEEDS_APPROVAL` list.
- No logging to file — trace output goes to stdout and is lost on exit.
- Task is hardcoded; no CLI or interactive input loop.
- No web search / external API tool yet.

## Roadmap

- **Week 2 (remaining)** — structured logging to file; web search or external API tool.
- **Week 3** — token accounting per turn, summarization of old tool results, core/working/droppable context policy tested against a task large enough to overflow the window.
- **Week 4** — 20–30 eval tasks with assertable pass/fail criteria, measured pass rate, root-cause analysis of the worst failures.
