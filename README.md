# agent-from-scratch

A tool-using LLM agent built without any agent framework — no LangChain, no orchestration library. Raw Anthropic API calls and a hand-written loop. The point is to understand the machinery frameworks hide: how a model requests a tool, how results get fed back, and where the real engineering problems live. Week 2 of 4: multi-tool, working multi-turn loop.

next tool to working on is shell exec - agent should be able to run bash commands

### requiremnts

Requires Python 3.9+ and an Anthropic API key with credits (a Claude Pro/Max subscription does not cover API usage — separate billing).

## setup

Set up with `python3 -m venv .venv`, activate it, `pip install anthropic`, and export ANTHROPIC_API_KEY. Then `python agent.py`. The task is hardcoded in the messages list near the top of agent.py — edit it there to ask something different. hello.py is a minimal no-tools API call, kept deliberately as a smoke test to isolate environment problems from loop bugs.
