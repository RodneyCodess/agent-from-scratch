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
            "dir_path": {
                "type": "string",
                "description": (
                    "Path relative to the project root, using forward slashes. "
                )
            }
        },
        "required": ["dir_path"]
    }
}


message = client.messages.create(
    model="claude-sonnet-5",
    max_tokens = 1024,
    tools=[rf_tool],
    messages=[
        {
            "role": "user",
            "content": "how many lines are in hello.py?"
        }
    ]
)

print(message)
