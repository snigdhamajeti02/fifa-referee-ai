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
[split_into_chunks]  -- splits into sentence-aware overlapping chunks (~1000 chars each)
     |
     v
[embed_chunks]  -- converts each chunk to a 384-dimensional vector using all-MiniLM-L6-v2
     |
     v
[MongoDB Atlas]  -- stores documents + vectors, builds a cosine similarity vector index
     |
     v  (at query time)
[get_query_embedding]  -- embeds the user's question
     |
     v
[search_mongodb]  -- runs $vectorSearch to retrieve top 5 most relevant chunks
     |
     v
[build_prompt]  -- combines retrieved chunks + question into a structured LLM prompt
     |
     v
[Groq API (LLaMA 3.1)]  -- generates a structured ruling: LAW / DECISION / EXPLANATION / SOURCE
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
| Embeddings | sentence-transformers / all-MiniLM-L6-v2 (384 dimensions) |
| LLM inference | Groq API (llama-3.1-8b-instant) |
| PDF parsing | pypdf |
| Environment | Python 3.12, python-dotenv |

---

## Project Structure

```
fifa-rag/
    ingest.py       -- one-time script: loads PDF, embeds chunks, inserts into MongoDB
    backend.py      -- RAG pipeline: embed query, search MongoDB, call Groq, parse response
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
- Split it into sentence-aware chunks
- Embed each chunk using all-MiniLM-L6-v2
- Insert 301 documents into MongoDB
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

Tested against 5 rule scenarios using the IFAB Laws of the Game 2026/27:

| Query | Result |
|---|---|
| A player scores directly from a throw-in | Correct |
| A player in offside position does not touch the ball | Correct |
| A goalkeeper drops and repicks the ball | Correct |
| Goalkeeper handles deliberate back pass | Partially correct (cites trick clause instead of back pass rule) |
| Penalty rebound scored by same player | Incorrect (retrieval fetches wrong chunk) |

**Accuracy: 3/5 fully correct, 1/5 partially correct, 1/5 incorrect** on a representative set of scenarios.

### Known limitations

- The embedding model (all-MiniLM-L6-v2) is general-purpose and not trained on football rules. Queries that use different wording than the Laws text may retrieve the wrong chunks.
- Multi-law scenarios (where the correct ruling requires cross-referencing two laws) often retrieve only one of the relevant chunks.
- Sentence-aware chunking can still split a rule across chunk boundaries, causing the key sentence to be partially present in two different chunks but fully present in neither.

### Potential improvements

- **Larger embedding model**: `all-mpnet-base-v2` (768 dimensions) improves semantic matching at the cost of speed
- **Hybrid search**: combine vector search with BM25 keyword search to improve recall for exact legal terms
- **Cross-encoder re-ranking**: after retrieving top 10 chunks, re-rank them with a cross-encoder before passing to the LLM
- **Increase TOP_K**: retrieving 7-10 chunks instead of 5 reduces the chance of missing the relevant passage
- **Query rewriting**: rephrase the user's question using football law terminology before embedding

---

## Notes

- Run `ingest.py` only once (or whenever you update the PDF). It drops and rebuilds the collection each time.
- The vector search index on MongoDB Atlas takes 1-2 minutes to build after `ingest.py` finishes.
- `all-MiniLM-L6-v2` downloads automatically on first run (~90 MB).
- The Groq free tier is sufficient for this project.
