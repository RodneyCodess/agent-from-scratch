import anthropic
import os
import sys
import json

client = anthropic.Anthropic()


# read file tool
rf_tool ={
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







messages = [
    {"role": "user", "content": "can you write a file called haiku with a haiku in it and tell me which is longer that file or hello.py"}

]

for turn in range(10):
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens = 1024,
        tools=[rf_tool, wf_tool],
        messages=messages
    )

    print(f"--- stop_reason: {response.stop_reason}")


    messages.append({
        "role": "assistant",
        "content": response.content
    })

    if response.stop_reason == "end_turn":
        print(response.content[-1].text)
        break

    tool_results = [
    ]

    for block in response.content:
        if block.type != "tool_use":
            continue

        if block.name == 'read_file':
            result = read_file(**block.input)

        elif block.name == 'write_file':

            print(f"WRITE to {block.input['file_path']}:")
            print(block.input['content'][:300])

            if input("approve? (y/n) ").strip().lower() == "y":
                result = write_file(**block.input )
            else:
                result = "Error: user denied the write."

        else:
            result = f"Error: unknown tool '{block.name}'"

        tool_results.append({
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": result,
    })

    messages.append({"role": "user", "content": tool_results})

else:
    print("Hit max turns without finishing.")
