import anthropic
import json
from dotenv import load_dotenv
from ibm_search import search_ibm_report

load_dotenv()

client = anthropic.Anthropic() 

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
                    "description": "number of days the request has been open",
                    "type": "integer",
                    "minimum": 1
                }
            },
            "required": ["request_type", "days_open"]
        }
    },
    {
        "name":"check_customer_tier",
        "description":"you will look up whether a customer is Standard, Premium, or Enterprise",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "description": "customer id e.g. CUST-001",
                    "type": "string"},
                "years_customer": {
                    "description": "number of years the customer has been with the company",
                    "type": "integer",
                    "minimum": 1}
                },
         "required": ["customer_id", "years_customer"]   
            }        
    },
    {
        "name": "search_ibm_report",
        "description": "you will look into the ibm annual report when anything about the company was asked",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string",
                             "description": "What to look for in the report, e.g. 'IBM net income 2025'"} 
            },
            "required": ["question"]
        }   }
]

messages = [
    {"role": "user", "content": "What was IBM's net income for 2025? Answer in one sentence and cite the page."}
]

def get_request_priority(request_type, days_open):
                        if days_open > 30:  
                            return {"Priority": "High"} 
                        elif days_open > 10:
                            return {"Priority": "Medium"}
                        else:
                            return {"Priority": "Low"}

def check_customer_tier(customer_id, years_customer):
    if customer_id in ["CUST-001", "CUST-002"] and years_customer > 5:
        return("Enterprise")
    else:
        return("Standard")

available_functions = {
    "get_request_priority": get_request_priority,
    "check_customer_tier": check_customer_tier,
    "search_ibm_report": search_ibm_report
}

while True:
    response = client.messages.create(
        model= "claude-haiku-4-5",
        max_tokens= 1000,
        tools= tools,
        messages= messages)

   # response = requests.post(url, headers=headers, json=body)
   # data = response.json()
   # print(json.dumps(data["content"], indent=2))

    if response.stop_reason == "tool_use":
        tool_results = []                                  

        for block in response.content:                    
            if block.type == "tool_use":                
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id                 
                function_to_call = available_functions[tool_name]
                results = function_to_call(**tool_input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(results)
                })

        
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
    else:
        print(response.content[0].text)
        break

                