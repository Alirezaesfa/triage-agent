import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

url = "https://api.anthropic.com/v1/messages"
headers = {
    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

tools = [
    {
        "name": "get_request_priority",
        "description": "Look up the priority level for a given backlog request type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "request_type": {
                    "type": "string",
                    "description": "The category of the request, e.g. 'billing_dispute', 'address_change'",
                    "enum": ["billing_dispute", "address_change", "plan_upgrade"]
                },
                "days_open": {
                    "type": "integer",
                    "minimum": 1
                }
            },
            "required": ["request_type"]
        }
    },
    {
        "name":"check_customer_tier",
        "description":"you will look up whether a customer is Standard, Premium, or Enterprise",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "description": "category of customers",
                    "type": "string"
                }
            
            },
        "required": ["customer_id"]
        }
    }
]

body = {
    "model": "claude-haiku-4-5",
    "max_tokens": 1000,
    "tools": tools,
    "messages": [
        {"role": "user", "content": "what is the priority level of an address change requet tht has been oopen for 30 days?"}
    ]
}

response = requests.post(url, headers=headers, json=body)
print("status code:", response.status_code)

if response.status_code == 200:
    data = response.json()
    print(data["content"][0]["text"]) #print(json.dumps(data,indent=2))   

else:
    print("Error:", response.text)


def get_request_priority(request_type, days_open):
                        if days_open > 30:  
                            return {"Priority": "High"} 
                        elif days_open > 10:
                            return {"Priority": "Medium"}
                        else:
                            return {"Priority": "Low"}

def check_customer_tier(customer_id):
    if customer_id in ["CUST-001", "CUST-002"]:
        return("Enterprise")
    else:
        return("Standard")

available_functions = {
    "get_request_priority": get_request_priority,
    "check_customer_tier": check_customer_tier
}

if data["stop_reason"] == "tool_use":
    tool_name = data["content"][0]["name"]
    tool_input = data["content"][0]["input"]
    function_to_call = available_functions[tool_name]
    results = function_to_call(**tool_input)
    print(results)


messages = [
        *body["messages"]
    ,
    {
        "role":"assistant",
        "content":data["content"]
    },
    {
        "role":"user",
        "content": [
            {
                "type":"tool_result",
                "tool_use_id":data["content"][0]["id"],
                "content": json.dumps(results)
            }
        ]
    }


]


body2 = {
    "model": "claude-haiku-4-5",
    "max_tokens": 1000,
    "tools": tools,
    "messages": messages 
}

response2= response = requests.post(url, headers=headers, json=body2)
if response2.status_code == 200:
    data2 = response2.json()
    print(data2["content"][0]["text"]) #print(json.dumps(data2,indent=2)) #   

else:
    print("Error:", response2.text)