"""
ingest.py
─────────
Run this script ONCE to populate MongoDB with FIFA rule chunks.

    python ingest.py

After it finishes, go to MongoDB Atlas UI and create a Vector Search index
on the `embedding` field.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# INSTALL: pip install pypdf sentence-transformers pymongo python-dotenv
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient

MONGODB_URI        = os.getenv("MONGODB_URI")
MONGODB_DB         = os.getenv("MONGODB_DB")          # fifa_rules
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")  # rules

PDF_PATH      = "fifa_laws.pdf"   # ← put your PDF here
CHUNK_SIZE    = 1000              # characters per chunk
CHUNK_OVERLAP = 300               # overlap between chunks
EMBED_MODEL   = "all-MiniLM-L6-v2"  # 384 dimensions, downloads automatically on first run


# ─────────────────────────────────────────────────────────────────────────────
def load_pdf(path: str) -> str:
    """
    TODO: Extract all text from the FIFA Laws PDF.

    Use PdfReader(path), loop through .pages, call .extract_text() on each,
    join everything into one string and return it.
    """
    
    fifa_rules_pdf_extracted = PdfReader(path)
    fifa_rules_text = ""
    
    for i, page in enumerate(fifa_rules_pdf_extracted.pages):
        fifa_rules_text = fifa_rules_text + (page.extract_text() or "")
    
    return fifa_rules_text

# ─────────────────────────────────────────────────────────────────────────────
def split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    TODO: Slide a window over the text to produce overlapping chunks.

    Start at 0, slice text[start : start + chunk_size], then advance by
    (chunk_size - overlap). Repeat until the end of the text.
    Return the list of chunk strings.
    """
    
    sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
    chunks = []
    current = ""

    for sentence in sentences:
        sentence = sentence + ". "
        if len(current) + len(sentence) <= chunk_size:
            current += sentence
        else:
            if current:
                chunks.append(current.strip())
            current = current[-overlap:] + sentence if overlap else sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
def embed_chunks(model, chunks: list[str]) -> list[list[float]]:
    """
    TODO: Turn every chunk into a vector using sentence-transformers.

    Call model.encode(chunks, show_progress_bar=True) — it accepts the whole
    list at once which is much faster than one at a time.
    Convert the result to a plain Python list and return it.
    Each vector will have 384 floats.
    """
    
    chunks_embed = model.encode(chunks, show_progress_bar=True).tolist()
    
    return chunks_embed


# ─────────────────────────────────────────────────────────────────────────────
def insert_chunks(collection, chunks: list[str], embeddings: list[list[float]]) -> None:
    """
    TODO: Build documents and insert them into MongoDB in one batch.

    Zip chunks and embeddings together. For each pair build:
        { "chunk_id": index, "text": chunk, "embedding": vector }
    Collect all documents into a list, then call collection.insert_many(docs).
    Print how many documents were inserted.
    """
    
    docs = []
    
    for index, chunk in enumerate(chunks):
        docs.append({"chunk_id": index, "text": chunk, "embedding": embeddings[index]})
        
    collection.insert_many(docs)
    
    print("Number of documents inserted", collection.count_documents({}))
    
    return None


# ─────────────────────────────────────────────────────────────────────────────
def main():
    """
    TODO: Wire everything together.

    1. Load SentenceTransformer(EMBED_MODEL)
    2. Connect MongoClient(MONGODB_URI), get the collection, drop it to start fresh
    3. Call load_pdf → split_into_chunks → embed_chunks → insert_chunks
    4. Print "Ingestion complete"

    AFTER RUNNING — create the Vector Search index in MongoDB Atlas UI:
        Index name : vector_index
        Field      : embedding
        Dimensions : 384          ← must match all-MiniLM-L6-v2
        Similarity : cosine
    """
    
    model = SentenceTransformer(EMBED_MODEL)
    mongo_client = MongoClient(MONGODB_URI)
    
    collection = mongo_client[MONGODB_DB][MONGODB_COLLECTION]
    collection.drop()
    
    rules_text = load_pdf(PDF_PATH)
    chunks = split_into_chunks(rules_text, CHUNK_SIZE, CHUNK_OVERLAP)
    embeddings = embed_chunks(model, chunks)
    insert_chunks(collection, chunks, embeddings)
    
    print("Ingestion complete")
    
    collection.create_search_index(
        {
            "name": "vector_index",
            "type": "vectorSearch",
            "definition": {
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": 384,
                        "similarity": "cosine"
                    }
                ],
            },
        }
    )


if __name__ == "__main__":
    main()
