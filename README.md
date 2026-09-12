# dyxn

Notes generator for lecture PDFs. Upload a textbook or slides, we chunk them, stick the vectors in Qdrant, then you can either chat against that context or run a little agent graph that dumps LaTeX notes.

Auth is off for now. Everything just works locally without a token.

## Layout

```
api/                 FastAPI routes + a couple of service classes
agents/              LangGraph nodes (planner → retriever → synthesizer → latex → evaluator)
                     plus a standalone chatbot that isn't on the graph
core/                config, redis, logging, and the interfaces we inject
data_processing/     PDF parse (OCR fallback) + semantic chunker
workers/             Redis stream consumers for chunking and embedding
db/                  Postgres users table, Qdrant wrapper
tests/mocks/         fake LLM / embeddings / vector store / chat memory
```

Postgres is only used for users, which we aren't really using while auth is skipped. Chat history is supposed to live in Qdrant.

## How the graph works

`WorkflowOrchestrator` wires:

planner → retriever → synthesizer → latex_agent → evaluator

If the evaluator scores below 8, it loops back to the synthesizer. Caps at 3 tries so it doesn't spin forever.

The chatbot is separate. Same retrieval idea, different entrypoint.

## Running it

You still need Postgres, Redis, and Qdrant even with auth off, because uploads go through Redis and embeddings go to Qdrant.

```bash
# .env: QDRANT_HOST, GROQ_API_KEY, embedding model name, collection names, etc.

docker compose up -d redis qdrant postgres

uvicorn api.server:app --reload
```

Workers aren't fully wired (no real LLM/embedding providers plugged into `__main__` yet). When they are:

```bash
python -m workers.chunk_worker
python -m workers.embedding_worker
```

Upload hits `POST /documents/upload`, which dumps a job on the `document_processing` stream. Chat is `POST /chat/sessions` then `POST /chat/sessions/{id}/chat` — the second one still needs the LLM stack hooked up.
