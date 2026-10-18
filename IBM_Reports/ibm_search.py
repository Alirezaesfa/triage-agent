import chromadb
from pypdf import PdfReader

reader = PdfReader("ibmars2025.pdf")

documents = []
ids = []
metadatas = []

client = chromadb.PersistentClient(path="chroma_db")                 
collection = client.get_or_create_collection(name="ibm_ars2025")  

if collection.count() == 0:
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if not text:
            continue
        words = text.split()
        for start in range(0, len(words), 120):
            chunk = " ".join(words[start:start+150])
            documents.append(chunk)
            ids.append(f"page{page_number}-start{start}")
            metadatas.append({"page": page_number})
    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas
        )
    pass

def search_ibm_report(question):
    results = collection.query(query_texts=[question], n_results=3)
    matches = []                       # one dict per matching chunk
    for chunk, metadata in zip(results["documents"][0], results["metadatas"][0]):
        matches.append({"page":page_number, "text":chunk})        
    return matches                        