import json
import product_agent as pa

NEW_PROMPT = (
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

METHODS = {
    "old": {"prompt": pa.SYSTEM_PROMPT, "top_products": 5},
    "new": {"prompt": NEW_PROMPT, "top_products": 8},
}

# Each test: the customer's question, and the products that count as correct (name and URL).
# An empty "expected" list means there is no good match in the catalog.
TESTS = [
    {"id": 1, "question": "My developers need to ship features faster",
     "expected": [("AI Coding Agent", "https://www.ibm.com/products/ai-coding-agent")]},
    {"id": 2, "question": "Our factory machines keep breaking down and we only find out after they fail",
     "expected": [("Maximo Application Suite", "https://www.ibm.com/products/maximo")]},
    {"id": 3, "question": "Sending huge video files to partners overseas takes forever and often fails",
     "expected": [("Aspera", "https://www.ibm.com/products/aspera")]},
    {"id": 4, "question": "We want to know when someone is attacking our network",
     "expected": [("QRadar SIEM", "https://www.ibm.com/products/qradar-siem"),
                  ("QRadar", "https://www.ibm.com/products/qradar")]},
    {"id": 5, "question": "Our cloud bill keeps growing and our apps are still slow",
     "expected": [("Turbonomic", "https://www.ibm.com/products/turbonomic")]},
    {"id": 6, "question": "Our app is slow and we can't figure out which part is causing it",
     "expected": [("Instana", "https://www.ibm.com/products/instana")]},
    {"id": 7, "question": "Employees lose company phones and laptops and we can't lock or track them",
     "expected": [("MaaS360", "https://www.ibm.com/products/maas360")]},
    {"id": 8, "question": "We record thousands of support calls and want them as searchable text",
     "expected": [("Speech to Text", "https://www.ibm.com/products/speech-to-text")]},
    {"id": 9, "question": "We get paper invoices and someone types the data in by hand",
     "expected": [("Document Processing", "https://www.ibm.com/products/document-processing"),
                  ("IBM Datacap", "https://www.ibm.com/products/data-capture-and-imaging")]},
    {"id": 10, "question": "Employees have too many passwords and we want one secure login for all our apps",
     "expected": [("IBM Verify", "https://www.ibm.com/products/verify"),
                  ("Verify Workforce Identity", "https://www.ibm.com/products/verify-workforce-identity")]},
    {"id": 11, "question": "We have to report our company's carbon emissions",
     "expected": [("Envizi", "https://www.ibm.com/products/envizi")]},
    {"id": 12, "question": "Our finance team builds the yearly budget in dozens of Excel files",
     "expected": [("Planning Analytics", "https://www.ibm.com/products/planning-analytics")]},
    {"id": 13, "question": "Managers want dashboards and reports on our sales data",
     "expected": [("Cognos Analytics", "https://www.ibm.com/products/cognos-analytics")]},
    {"id": 14, "question": "Customers keep asking the same questions on our website",
     "expected": [("Watsonx Assistant", "https://www.ibm.com/products/watson-assistant")]},
    {"id": 15, "question": "I want to advertise my company", "expected": []},
    {"id": 16, "question": "We need a food delivery app for our restaurant", "expected": []},
]

# Every search Claude makes during one question gets recorded here.
search_log = []
current_top_products = 5


def logged_search(problem, on_premises=False, saas=False, free_trial=False):
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

    matches = pa.find_products(pa.collection, problem, top_products=current_top_products, where=where)
    search_log.append({"query": problem, "products": [m["product"] for m in matches]})

    results = []
    for match in matches:
        results.append({
            "product": match["product"],
            "url": match["url"],
            "distance": round(match["best_distance"], 3),
            "evidence": match["chunks"][:2]
        })
    return results


# Point the agent at the logging search instead of its own.
pa.available_functions["find_ibm_products"] = logged_search


def run_method(name, settings):
    global current_top_products
    pa.SYSTEM_PROMPT = settings["prompt"]
    current_top_products = settings["top_products"]

    rows = []
    for test in TESTS:
        search_log.clear()
        answer = pa.ask_products(test["question"])
        searches = list(search_log)

        found_names = set()
        for search in searches:
            found_names.update(search["products"])

        expected_names = [n for n, u in test["expected"]]
        retrieved = any(n in found_names for n in expected_names)
        recommended = any(f"[{n}]" in answer or f"{u})" in answer for n, u in test["expected"])

        rows.append({
            "id": test["id"],
            "question": test["question"],
            "expected": expected_names,
            "retrieved": retrieved,
            "recommended": recommended,
            "searches": searches,
            "answer": answer,
        })
        print(f"  [{name}] #{test['id']} done")
    return rows


def mark(value):
    return "yes" if value else "NO"


all_results = {}
for name, settings in METHODS.items():
    print(f"\nRunning method: {name}")
    all_results[name] = run_method(name, settings)

print("\n=== RESULTS (questions 1-14) ===")
print(f"{'#':>3}  {'expected':<28} {'old found':>9} {'old rec':>8} {'new found':>9} {'new rec':>8}")
for old_row, new_row in zip(all_results["old"], all_results["new"]):
    if not old_row["expected"]:
        continue
    print(f"{old_row['id']:>3}  {old_row['expected'][0]:<28} "
          f"{mark(old_row['retrieved']):>9} {mark(old_row['recommended']):>8} "
          f"{mark(new_row['retrieved']):>9} {mark(new_row['recommended']):>8}")

for name in METHODS:
    scored = [r for r in all_results[name] if r["expected"]]
    found = sum(r["retrieved"] for r in scored)
    rec = sum(r["recommended"] for r in scored)
    print(f"{name}: found {found}/{len(scored)}, recommended {rec}/{len(scored)}")

print("\n=== NO-MATCH QUESTIONS (judge these by reading) ===")
for name in METHODS:
    for row in all_results[name]:
        if not row["expected"]:
            print(f"\n[{name}] #{row['id']} {row['question']}")
            print("  searches:", [s["query"] for s in row["searches"]])
            print("  answer:", row["answer"][:500])

with open("eval_results.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)
print("\nFull details (every search and answer) saved to eval_results.json")