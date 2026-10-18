import json
import anthropic
from dotenv import load_dotenv
from load_ibm_into_chroma import get_collection, load, find_products

load_dotenv()

client = anthropic.Anthropic()

collection = get_collection()
if collection.count() == 0:
    print("Database is empty, loading the product chunks (first run only)...")
    load(collection)

SYSTEM_PROMPT = (
    "You are a pre-sales assistant that recommends IBM products. "
    "The user describes a business problem or need. "
    "Always use the find_ibm_products tool before recommending anything, and recommend only products it returns. "
    "Search at least twice: once with the user's need in their own words, "
    "and once rephrased the way an IBM product page would describe the solution, using product-category terms "
    "(for example 'data lakehouse for analytics and AI' instead of 'our data is scattered across many databases', "
    "or 'API management platform' instead of 'partners need secure access to our services'). "
    "If the problem has several parts, search once per part, then combine the results into a bundle. "
    "If the user mentions a requirement such as on-premises, SaaS or a free trial, pass the matching filter. "
    "Recommend one product or a small bundle of at most 3. "
    "Prefer general-purpose products over specialized ones unless the user mentions the specialty "
    "(for example, do not lead with a mainframe-only product unless the user mentions mainframes). "
    "For each product, give its name as a markdown link to its URL and one or two sentences on how it addresses the user's problem. "
    "If nothing returned is a good fit, say so honestly instead of forcing a recommendation. "
    "Be concise."
)

tools = [
    {
        "name": "find_ibm_products",
        "description": "Search IBM's product catalog for products that match a customer's problem or need. Returns up to 8 products, each with its name, URL, match distance (lower is closer) and the matching parts of its description.",
        "input_schema": {
            "type": "object",
            "properties": {
                "problem": {
                    "type": "string",
                    "description": "The customer's problem or need, in plain words, e.g. 'analyze customer feedback to understand sentiment'"
                },
                "on_premises": {
                    "type": "boolean",
                    "description": "Set to true only if the customer needs to run the product on their own servers."
                },
                "saas": {
                    "type": "boolean",
                    "description": "Set to true only if the customer wants a cloud (SaaS) product."
                },
                "free_trial": {
                    "type": "boolean",
                    "description": "Set to true only if the customer wants products with a free trial."
                }
            },
            "required": ["problem"]
        }
    }
]


def find_ibm_products(problem, on_premises=False, saas=False, free_trial=False):
    filters = []
    if on_premises:
        filters.append({"on_premises": True})
    if saas:
        filters.append({"saas": True})
    if free_trial:
        filters.append({"free_trial": True})

    if len(filters) == 0:
        where = None
    elif len(filters) == 1:
        where = filters[0]
    else:
        where = {"$and": filters}

    matches = find_products(collection, problem, top_products=8, where=where)
    print(f"\nSEARCH: {problem!r}  filters={where}")
    for match in matches:
        print(f"  {match['best_distance']:.3f}  {match['product']}")
    results = []
    for match in matches:
        results.append({
            "product": match["product"],
            "url": match["url"],
            "distance": round(match["best_distance"], 3),
            "evidence": match["chunks"][:2]
        })
    return results


available_functions = {
    "find_ibm_products": find_ibm_products
}


def ask_products(question):
    messages = [
        {"role": "user", "content": question}
    ]

    for turn in range(8):
        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages
        )

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
            answer = ""
            for block in response.content:
                if block.type == "text":
                    answer = answer + block.text
            return answer

    return "Sorry, I could not finish answering that. Please try rephrasing your question."


if __name__ == "__main__":
    print(ask_products("Our support team gets thousands of emails a week and we want to understand what customers are unhappy about. It has to run on our own servers."))