import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-sonnet-5",
    max_tokens = 100,
    messages=[
        {
            "role": "user",
            "content": "Hello, how are you?"
        }
    ]
)

print(message)
