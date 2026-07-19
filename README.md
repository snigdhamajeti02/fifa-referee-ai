# FIFA Referee AI

A Retrieval-Augmented Generation (RAG) application that answers football referee questions using the official FIFA Laws of the Game. Describe any match situation and get the official ruling, the relevant law, an explanation, and a direct quote from the rulebook.

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
    fifa_laws.pdf   -- place your FIFA Laws of the Game PDF here
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd fifa-rag
pip install -r requirements.txt
pip install sentence-transformers groq
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

Place the FIFA Laws of the Game PDF in the project folder as `fifa_laws.pdf`.

### 4. Run ingestion

```bash
python ingest.py
```

This will:
- Extract text from the PDF
- Split it into sentence-aware chunks
- Embed each chunk using all-MiniLM-L6-v2
- Insert 155 documents into MongoDB
- Create a cosine similarity vector search index

### 5. Run the app

```bash
python -m streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Example Questions

- A player scores directly from a throw-in
- The ball hits the referee and goes into the goal during open play
- A substitute enters the pitch before the substituted player has left
- A goalkeeper drops the ball and picks it up again without an opponent touching it

---

## Evaluation

The system was tested against a set of rule scenarios. Key observations:

- **Correct rulings**: offside, handball, substitution, and restart rules are retrieved and answered accurately
- **Edge cases**: situations involving indirect free kicks, dropped balls, and Law 12 handball are handled well with the improved chunking (1000-char sentence-aware chunks)
- **Limitations**: the model is constrained to text extracted from the PDF. Scanned or image-based pages will produce empty chunks. Questions requiring cross-referencing multiple laws in a single answer may receive partial responses

---

## Notes

- Run `ingest.py` only once (or whenever you update the PDF). It drops and rebuilds the collection each time.
- The vector search index on MongoDB Atlas takes 1-2 minutes to build after `ingest.py` finishes.
- `all-MiniLM-L6-v2` downloads automatically on first run (~90 MB).
- The Groq free tier is sufficient for this project.
