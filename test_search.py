from load_ibm_into_chroma import get_collection

collection = get_collection()

PREFIX = "Represent this sentence for searching relevant passages: "
TARGETS = ["AI Coding Agent", "IBM Bob"]

queries = [
    "help developers expedite development with AI assistant",
    "hey i need to help my developers in expediting the development with AI assistant",
    "AI coding agent for software development",
]


def rank_products(query_text):
    results = collection.query(query_texts=[query_text], n_results=100)
    best = {}
    for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
        name = metadata["product"]
        if name not in best or distance < best[name]:
            best[name] = distance
    return sorted(best.items(), key=lambda item: item[1])


for query in queries:
    print(f"\nQUERY: {query!r}")
    for label, text in [("plain ", query), ("prefix", PREFIX + query)]:
        ranked = rank_products(text)
        names = [name for name, distance in ranked]
        positions = []
        for target in TARGETS:
            if target in names:
                positions.append(f"{target} = #{names.index(target) + 1}")
            else:
                positions.append(f"{target} = not in top {len(names)}")
        top5 = ", ".join(name for name, distance in ranked[:5])
        print(f"  {label}  {' | '.join(positions)}")
        print(f"          top 5: {top5}")