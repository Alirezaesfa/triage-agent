import os
import json
import requests
from dotenv import load_dotenv


load_dotenv()

url = "https://api.anthropic.com/v1/messages"
headers = {
    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json"
}

body = {
    "model": "claude-haiku-4-5",
    "max_tokens": 200,
    "messages": [
        {
            "role": "user",
            "content": "Hello, how are you?, in one sentence, what does a business analyst do?"
        }
    ]
}

response = requests.post(url, headers=headers, json=body)
print("status code:", response.status_code)

if response.status_code == 200:
    data = response.json()
    print(json.dumps(data["content"][0]["text"], indent=3)) #    print(data["content"][0]["text"])

else:
    print("Error:", response.text)