"""
backend.py
──────────
Called by app.py on every user question.
RAG pipeline: embed query → search MongoDB → call Groq → return answer.

The only function app.py imports is:
    from backend import search_and_answer
"""

import os
from dotenv import load_dotenv

load_dotenv()

# INSTALL: pip install groq sentence-transformers pymongo python-dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer, CrossEncoder
from pymongo import MongoClient

MONGODB_URI        = os.getenv("MONGODB_URI")
MONGODB_DB         = os.getenv("MONGODB_DB")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY")

EMBED_MODEL    = "all-mpnet-base-v2"              # same model used in ingest.py, 768 dimensions
RERANK_MODEL   = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # re-ranks retrieved chunks
CHAT_MODEL     = "llama-3.3-70b-versatile"        # free Groq model, better reasoning
TOP_K          = 15                               # candidates to retrieve before re-ranking
RERANK_TOP_K   = 5                                # chunks to keep after re-ranking


# ─────────────────────────────────────────────────────────────────────────────
def get_query_embedding(model, text: str) -> list[float]:
    """
    TODO: Embed the user's question using the same model used in ingest.py.

    Call model.encode([text])[0] to get a single vector.
    Convert to a plain Python list and return it.
    """
    
    embedding = model.encode([text])[0].tolist()
    
    return embedding


# ─────────────────────────────────────────────────────────────────────────────
def search_mongodb(collection, query_vector: list[float], top_k: int) -> list[str]:
    """
    TODO: Find the most relevant rule chunks using Atlas Vector Search.

    Build this aggregation pipeline and run collection.aggregate(pipeline):

        [
          {
            "$vectorSearch": {
              "index":         "vector_index",
              "path":          "embedding",
              "queryVector":   query_vector,
              "numCandidates": top_k * 10,
              "limit":         top_k,
            }
          },
          { "$project": { "text": 1, "_id": 0 } }
        ]

    Return a list of the "text" values from the results.
    """
    
    pipeline = [
          {
            "$vectorSearch": {
              "index":         "vector_index",
              "path":          "embedding",
              "queryVector":   query_vector,
              "numCandidates": top_k * 10,
              "limit":         top_k,
            }
          },
          { "$project": { "text": 1, "_id": 0 } }
        ]
    
    results = collection.aggregate(pipeline)
    return [doc["text"] for doc in results]


# ─────────────────────────────────────────────────────────────────────────────
def build_prompt(situation: str, context_chunks: list[str]) -> str:
    """
    TODO: Combine retrieved chunks and the user's situation into a prompt.

    Join the chunks with "\n\n---\n\n" as a separator, then build a string
    using this exact structure so the model knows what format to reply in:

        You are an expert FIFA referee assistant.
        Use ONLY the rules below to answer. Do not invent rules.

        RULES:
        {joined chunks}

        SITUATION:
        {situation}

        Reply in this exact format:
        LAW: <law name and number>
        DECISION: <one-line ruling>
        EXPLANATION: <plain English, 2-4 sentences>
        SOURCE: <direct quote from the rules above>

    Return the full prompt string.
    """
    
    rules = "\n\n---\n\n".join(context_chunks)
    return f"""You are an expert FIFA referee assistant.
            Use ONLY the rules below to answer. Do not invent rules.

            RULES:
            {rules}

            SITUATION:
            {situation}

            Reply in this exact format:
            LAW: <law name and number>
            DECISION: <one-line ruling>
            EXPLANATION: <plain English, 2-4 sentences>
            SOURCE: <direct quote from the rules above>"""


# ─────────────────────────────────────────────────────────────────────────────
def parse_response(raw: str) -> dict:
    """
    TODO: Parse the model's plain-text reply into a structured dict.

    Split raw by newlines. For each line check if it starts with
    "LAW:", "DECISION:", "EXPLANATION:", or "SOURCE:" and extract
    the value after the colon (strip whitespace).

    Return:
        {
            "law":         str,
            "decision":    str,
            "explanation": str,
            "sources":     [str]   ← wrap the SOURCE value in a list
        }

    If a field is missing from the reply, use an empty string as the default.
    """
    
    result = {"law": "", "decision": "", "explanation": "", "sources": [""]}

    for line in raw.split("\n"):
        if line.startswith("LAW:"):
            result["law"] = line[len("LAW:"):].strip()
        elif line.startswith("DECISION:"):
            result["decision"] = line[len("DECISION:"):].strip()
        elif line.startswith("EXPLANATION:"):
            result["explanation"] = line[len("EXPLANATION:"):].strip()
        elif line.startswith("SOURCE:"):
            result["sources"] = [line[len("SOURCE:"):].strip()]

    return result


# ─────────────────────────────────────────────────────────────────────────────
def search_and_answer(situation: str) -> dict:
    """
    TODO: Main function — wires all steps together. Only entry point for app.py.

    1. Load SentenceTransformer(EMBED_MODEL)
    2. Connect MongoClient(MONGODB_URI), get the collection
    3. query_vector = get_query_embedding(model, situation)
    4. chunks       = search_mongodb(collection, query_vector, TOP_K)
    5. prompt       = build_prompt(situation, chunks)
    6. Call Groq:
            client   = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[{ "role": "user", "content": prompt }],
                temperature=0.2,
            )
    7. raw = response.choices[0].message.content
    8. return parse_response(raw)

    Returns:
        { "law": str, "decision": str, "explanation": str, "sources": [str] }
    """
    
    model = SentenceTransformer(EMBED_MODEL)
    reranker = CrossEncoder(RERANK_MODEL)
    mongo_client = MongoClient(MONGODB_URI)

    collection = mongo_client[MONGODB_DB][MONGODB_COLLECTION]

    query_vector = get_query_embedding(model, situation)
    candidates = search_mongodb(collection, query_vector, TOP_K)

    # Re-rank candidates by relevance to the question, keep top RERANK_TOP_K
    scores = reranker.predict([(situation, chunk) for chunk in candidates])
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    chunks = [chunk for _, chunk in ranked[:RERANK_TOP_K]]

    prompt = build_prompt(situation, chunks)
    
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{ "role": "user", "content": prompt }],
        temperature=0.2,
    )
    
    raw = response.choices[0].message.content
    result = parse_response(raw)
    result["retrieved_chunks"] = chunks
    return result
