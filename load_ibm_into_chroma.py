"""
Load the pre-chunked IBM product data into ChromaDB, then search it.

Plan:
  1. Pick an embedding model that can read a whole chunk (see EMBED_MODEL below).
  2. Read ibm_products_chunks.jsonl: one line = one chunk, already split by section.
  3. Add every chunk to a Chroma collection: the `text` gets embedded, the other
     fields go in as metadata so you can filter on them later.
  4. find_products(): search with the customer's problem, then group the matching
     chunks by product so you get a ranked list of products, not loose chunks.

Install once:  pip install chromadb sentence-transformers
Run:           python load_ibm_into_chroma.py
"""
import json
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

# ---- settings ---------------------------------------------------------------
HERE = Path(__file__).parent
CHUNKS_FILE = HERE / "ibm_products_chunks.jsonl"
DB_FOLDER = HERE / "chroma_db"          # Chroma saves the database here
COLLECTION = "ibm_products"

# Chroma's default model (all-MiniLM-L6-v2) only reads ~256 tokens (~1,000 characters)
# and silently ignores the rest. These chunks run up to ~2,300 characters, so use a
# model that reads 512 tokens. bge-small is fast and runs fine on a laptop CPU.
EMBED_MODEL = "BAAI/bge-small-en-v1.5"


def get_collection():
    client = chromadb.PersistentClient(path=str(DB_FOLDER))
    embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    return client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=embed,
        metadata={"hnsw:space": "cosine"},
    )


def to_metadata(chunk):
    """Chroma metadata values must be str, int, float or bool, so lists become text,
    and the most useful filters also get their own true/false fields."""
    deployment = chunk.get("deployment") or []
    return {
        "product_id": chunk["id"],
        "product": chunk["name"],
        "url": chunk["url"],
        "section_type": chunk["section_type"],      # summary, features, use_cases, pricing, ...
        "section_heading": chunk["section_heading"],
        "category": "; ".join(chunk.get("category") or []),
        "topics": "; ".join(chunk.get("topics") or []),
        "industries": "; ".join(chunk.get("industries") or []),
        "deployment": "; ".join(deployment),
        "on_premises": "On-premises" in deployment,
        "saas": "SaaS" in deployment,
        "free_trial": bool(chunk.get("free_trial")),
        "buy_now": bool(chunk.get("buy_now")),
        "popularity_rank": int(chunk.get("rank_popularity") or 9999),
    }


def load(collection, batch_size=200):
    chunks = [json.loads(line) for line in CHUNKS_FILE.open(encoding="utf-8")]
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        collection.upsert(                       # upsert = safe to re-run, no duplicates
            ids=[c["chunk_id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[to_metadata(c) for c in batch],
        )
        print(f"loaded {min(start + batch_size, len(chunks))}/{len(chunks)}")
    return len(chunks)


def find_products(collection, problem, top_products=5, where=None):
    """Search with the customer's problem and return the best products, each with the
    chunks that matched (to pass to your LLM as context)."""
    res = collection.query(query_texts=[problem], n_results=30, where=where)
    products = {}
    for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        p = products.setdefault(meta["product_id"], {
            "product": meta["product"], "url": meta["url"], "best_distance": dist, "chunks": []})
        p["best_distance"] = min(p["best_distance"], dist)
        p["chunks"].append(text)
    ranked = sorted(products.values(), key=lambda p: p["best_distance"])
    return ranked[:top_products]


def build_llm_context(matches):
    """Turn the matches into one block of text for your LLM prompt."""
    parts = []
    for m in matches:
        parts.append(f"=== {m['product']} ({m['url']}) ===\n" + "\n\n".join(m["chunks"][:3]))
    return "\n\n".join(parts)


if __name__ == "__main__":
    col = get_collection()
    if col.count() == 0:
        load(col)
    print("chunks in database:", col.count())

    question = "I need to analyze customer feedback and find out how people feel about our product"
    for m in find_products(col, question):
        print(f"{m['best_distance']:.3f}  {m['product']}  {m['url']}")

    # Same search, but only products that run on-premises:
    print("\nOn-premises only:")
    for m in find_products(col, question, where={"on_premises": True}):
        print(f"{m['best_distance']:.3f}  {m['product']}")
