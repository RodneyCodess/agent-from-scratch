import anthropic
import os
from agent_log import log
from tools import TOOLS, SCHEMAS, NEEDS_APPROVAL


client = anthropic.Anthropic()

# ==== APPROVE FUNCTION ====
def approve(block):
    if block.name == "write_file":
        print(f"WRITE to {block.input['file_path']}:")
        print(block.input['content'][:300])
    elif block.name == "shell_exec":
        print(f"RUN: {block.input['commands']}")
    else:
        print(f"{block.name}: {block.input}")

    return input("approve? (y/n) ").strip().lower() == "y"

messages = [

    {"role": "user", "content": "can you git add and commit with the name update and push it"}
]

os.makedirs("logs", exist_ok=True)
log("run_start", task=messages[0]["content"])

for turn in range(10):

    log("turn_start", turn=turn + 1)

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=8192,
        tools=SCHEMAS,
        messages=messages
    )

    print(f"--- stop_reason: {response.stop_reason}")

    log("model_response",
        turn=turn + 1,
        stop_reason=response.stop_reason,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens)

    messages.append({
        "role": "assistant",
        "content": response.content
    })

    if response.stop_reason == "end_turn":
        text = response.content[-1].text
        print(text)
        log("final_answer", text=text)
        break

    if response.stop_reason == "max_tokens":
        print("Response was cut off by max_tokens.")
        log("max_tokens_hit", turn=turn + 1)
        break

    tool_results = []

    for block in response.content:
        if block.type != "tool_use":
            continue

        log("tool_call", tool=block.name, input=block.input)

        fn = TOOLS.get(block.name)

        if fn is None:
            result = f"Error: unknown tool '{block.name}'"
        elif block.name in NEEDS_APPROVAL and not approve(block):
            log("approval", tool=block.name, approved=False)
            result = f"Error: user denied {block.name}."
        else:
            if block.name in NEEDS_APPROVAL:
                log("approval", tool=block.name, approved=True)
            result = fn(**block.input)

        log("tool_result", result=result)

        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result,
        })

    messages.append({"role": "user", "content": tool_results})

else:
    print("Hit max turns without finishing.")
    log("max_turns_hit", limit=10)
