# FIFA Referee AI

A Retrieval-Augmented Generation (RAG) application that answers football referee questions using the official IFAB Laws of the Game. Describe any match situation and get the official ruling, the relevant law, an explanation, and a direct quote from the rulebook.

**Live demo:** https://fifa-referee-ai-jfqlch6fya2suydsqhfgmk.streamlit.app

---

## What is RAG?

RAG (Retrieval-Augmented Generation) is a technique that combines a vector database with a large language model:

1. Documents are split into chunks and converted into numerical vectors (embeddings)
2. When a question is asked, the question is also converted into a vector
3. The database finds the chunks most semantically similar to the question
4. Those chunks are passed to the LLM as context, so it answers using real source material instead of guessing

This means the model cannot hallucinate rules that do not exist because it is constrained to the retrieved text.

---

## How It Works

```
fifa_laws.pdf
     |
     v
[load_pdf]  -- extracts all text from the PDF
     |
     v
[split_into_chunks]  -- paragraph-aware chunking with Law boundaries (~1500 chars each)
     |
     v
[embed_chunks]  -- converts each chunk to a 768-dimensional vector using all-mpnet-base-v2
     |
     v
[MongoDB Atlas]  -- stores documents + vectors, builds a cosine similarity vector index
     |
     v  (at query time)
[get_query_embedding]  -- embeds the user's question
     |
     v
[search_mongodb]  -- runs $vectorSearch to retrieve top 15 candidate chunks
     |
     v
[CrossEncoder re-ranking]  -- re-ranks candidates, keeps top 5 most relevant chunks
     |
     v
[build_prompt]  -- combines retrieved chunks + question into a structured LLM prompt
     |
     v
[Groq API (LLaMA 3.3 70B)]  -- generates a structured ruling: LAW / DECISION / EXPLANATION / SOURCE
     |
     v
[parse_response]  -- parses the response into a dict for the UI
     |
     v
[Streamlit UI]  -- displays the result as formatted cards
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| Vector database | MongoDB Atlas Vector Search |
| Embeddings | sentence-transformers / all-mpnet-base-v2 (768 dimensions) |
| Re-ranking | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| LLM inference | Groq API (llama-3.3-70b-versatile) |
| PDF parsing | pypdf |
| Environment | Python 3.12, python-dotenv |

---

## Project Structure

```
fifa-rag/
    ingest.py       -- one-time script: loads PDF, embeds chunks, inserts into MongoDB
    backend.py      -- RAG pipeline: embed query, search MongoDB, re-rank, call Groq, parse response
    app.py          -- Streamlit frontend
    requirements.txt
    .env.example    -- copy to .env and fill in your credentials
    fifa_laws.pdf   -- place the IFAB Laws of the Game PDF here (not committed)
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/snigdhamajeti02/fifa-referee-ai
cd fifa-rag
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
MONGODB_DB=fifa_rules
MONGODB_COLLECTION=rules
GROQ_API_KEY=your_groq_api_key
```

- **MongoDB URI**: from MongoDB Atlas (Clusters > Connect > Drivers > Python)
- **Groq API key**: free at console.groq.com

### 3. Add the PDF

Download the IFAB Laws of the Game PDF from https://www.theifab.com/laws-of-the-game/ and save it as `fifa_laws.pdf` in the project folder.

> Important: use the IFAB Laws of the Game, not FIFA competition regulations. They are different documents.

### 4. Run ingestion

```bash
python ingest.py
```

This will:
- Extract text from the PDF
- Split into paragraph-aware chunks with Law boundaries
- Embed each chunk using all-mpnet-base-v2 (768 dimensions)
- Insert 216 documents into MongoDB
- Create a cosine similarity vector search index

### 5. Run the app

```bash
python -m streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Example Questions

- A player scores directly from a throw-in
- A player is in an offside position when the ball is played but does not touch it
- A goalkeeper drops the ball and picks it up again without an opponent touching it
- The ball hits the referee and goes into the goal during open play

---

## Evaluation

Tested against 10 rule scenarios using the IFAB Laws of the Game 2026/27:

| Query | Result |
|---|---|
| A player scores directly from a throw-in | Correct |
| A player in offside position does not touch the ball | Correct |
| A goalkeeper drops and repicks the ball | Correct |
| Goalkeeper handles deliberate back pass | Correct |
| Penalty rebound scored by same player | Correct |
| Ball deflects off referee into the goal | Correct |
| Player handles ball to prevent a goal (no obvious goal-scoring opportunity) | Correct |
| A substitute enters the field without permission during play | Partially correct |
| Offside from a deliberate save by the goalkeeper | Incorrect |
| Player receives two yellow cards in the same match | Incorrect |

**Accuracy: 7/10 fully correct, 1/10 partially correct, 2/10 incorrect**

### Improvement history

| Change | Accuracy |
|---|---|
| Baseline: all-MiniLM-L6-v2, TOP_K=5, CHUNK_SIZE=1000 | 3/5 (60%) |
| Increased TOP_K to 8 | ~60% |
| Increased CHUNK_OVERLAP to 300 | ~60% |
| Upgraded to all-mpnet-base-v2 (768 dims) | ~60% |
| Added cross-encoder re-ranking (TOP_K=15 → 5) | 6/10 (60%) |
| Upgraded LLM to llama-3.3-70b-versatile | 7/10 (70%) |
| Increased CHUNK_SIZE to 1500 + paragraph-aware chunking | **7/10 (70%)** |

### Known limitations

- The embedding model is general-purpose and not trained on football rules. Queries using different wording than the Laws text may retrieve the wrong chunks.
- Multi-law scenarios (where the correct ruling requires cross-referencing two laws) still occasionally retrieve only one of the relevant chunks.
- The goalkeeper deliberate save offside rule (Law 11) is an exception clause embedded within a longer passage — it is easily split from its surrounding context during chunking.

### Potential further improvements

- **Hybrid search**: combine vector search with BM25 keyword search to improve recall for exact legal terms
- **Query rewriting**: rephrase the user's question using football law terminology before embedding
- **Fine-tuned embeddings**: train a domain-specific embedding model on the Laws text
- **Larger RERANK_TOP_K**: pass 7-8 chunks to the LLM instead of 5 to reduce the chance of missing the relevant passage
- **Named entity linking**: detect "Law 11", "Law 14" etc. in questions and force-include those chunks

---

## Notes

- Run `ingest.py` only once (or whenever you update the PDF). It drops and rebuilds the collection each time.
- The vector search index on MongoDB Atlas takes 1-2 minutes to build after `ingest.py` finishes.
- `all-mpnet-base-v2` downloads automatically on first run (~420 MB).
- The Groq free tier is sufficient for this project.
