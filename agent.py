import anthropic

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

def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        return f"Error: could not read '{file_path}': {e}"

messages = [
    {"role": "user", "content": "how many lines are in hello.py?",}

]

response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens = 1024,
    tools=[rf_tool],
    messages=messages
)

messages.append({
    "role": "assistant",
    "content": response.content
})

block = response.content[-1]
file_text  = read_file(block.input['file_path'])

messages.append({
    "role": "user",
    "content": [{
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": file_text
    }]
})

response2 = client.messages.create(
    model="claude-sonnet-5",
    max_tokens = 1024,
    tools = [rf_tool],
    messages=messages
)

print(response2.content[-1].text)
