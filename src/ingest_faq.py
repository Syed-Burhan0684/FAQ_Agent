# src/ingest_faq.py
import os
import csv
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
MODEL_NAME = os.getenv("LOCAL_EMB_MODEL", "all-MiniLM-L6-v2")
FAQ_CSV = os.path.join("data", "faq.csv")
COLLECTION_NAME = os.getenv("FAQ_COLLECTION_NAME", "faq_collection")

print("CHROMA_PATH:", CHROMA_PATH)
print("Loading SentenceTransformer model:", MODEL_NAME)
model = SentenceTransformer(MODEL_NAME)

client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(allow_reset=True))

try:
    coll = client.get_collection(COLLECTION_NAME)
    print(f"Found existing collection '{COLLECTION_NAME}'.")
except Exception:
    coll = client.create_collection(name=COLLECTION_NAME)
    print(f"Created collection '{COLLECTION_NAME}'.")

def embed_text(text: str):
    vec = model.encode(text, show_progress_bar=False)
    return vec.tolist() if hasattr(vec, "tolist") else list(map(float, vec))

def ingest_faq_from_csv(csv_path=FAQ_CSV):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"{csv_path} not found. Create data/faq.csv with id,question,answer[,category] header.")
    ids, metadatas, embeddings, documents = [], [], [], []
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for idx, row in enumerate(r):
            _id = str((row.get("id") or "").strip() or idx)
            q = (row.get("question") or "").strip()
            a = (row.get("answer") or "").strip()
            cat = (row.get("category") or "").strip()
            if not q or not a:
                continue
            ids.append(_id)
            metadatas.append({"question": q, "answer": a, "category": cat})
            documents.append(f"Q: {q}\nA: {a}")
            embeddings.append(embed_text(q))   # embed question (or change to q + " " + a)

    if not ids:
        print("No valid FAQ rows found in CSV.")
        return 0

    coll.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
    try:
        client.persist()
    except Exception:
        pass

    print(f"Ingested {len(ids)} FAQ items into Chroma at {CHROMA_PATH}.")
    try:
        sample = coll.get(ids=[ids[0]], include=['documents','metadatas','ids'])
        print("Sample stored item (first):", sample)
    except Exception:
        pass

    return len(ids)

def ingest(csv_path=FAQ_CSV):
    return ingest_faq_from_csv(csv_path)

if __name__ == "__main__":
    ingest()
