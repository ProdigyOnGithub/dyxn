# dyxn

Notes generator for lecture PDFs. Upload a textbook or slides, we chunk them, stick the vectors in Qdrant, then you can either chat against that context or run a little agent graph that dumps LaTeX notes.

Auth is off for now. Everything just works locally without a token.

## Layout

```text
├── frontend/               React + Vite UI
├── api/
│   ├── routes/
│   │   ├── auth.py                 Login and register endpoints
│   │   ├── chat.py                 Chat session management and AI inference routes
│   │   └── documents.py            PDF upload endpoints and progress websockets
│   ├── services/
│   │   ├── auth_service.py         Password hashing, JWT generation, and rate limiting
│   │   ├── chat_service.py         Wires the LLM to the Qdrant context manager for chat
│   │   ├── progress_manager.py     Tracks document ingestion progress state in Redis hashes
│   │   ├── pubsub_listener.py      Listens to Redis for progress updates to broadcast
│   │   └── websocket_manager.py    Manages active WebSocket connections to the frontend
│   ├── schemas.py                Pydantic models for API requests and responses
│   └── server.py                 FastAPI app initialization and router inclusion
├── agents/
│   ├── base_agent.py             Base class for LLM agents with standard config and logger
│   ├── chatbot.py                Standalone Q&A agent that answers questions from documents
│   ├── evaluator.py              Scores the synthesized notes out of 10
│   ├── latex_agent.py            Converts final synthesized notes into valid LaTeX code
│   ├── orchestrator.py           LangGraph state machine that wires the agents together
│   ├── planner.py                Breaks down the requested topic into search queries
│   ├── retriever.py              Executes searches against Qdrant based on the planner
│   ├── state.py                  Defines the shared State dictionary passed through LangGraph
│   └── synthesizer.py            Combines retrieved document chunks into coherent notes
├── core/
│   ├── interfaces/
│   │   ├── context_provider.py     Abstract base for managing chat history
│   │   ├── embedding_provider.py   Abstract base for generating text embeddings
│   │   ├── llm_provider.py         Abstract base for LLM inference
│   │   └── vector_store.py         Abstract base for vector database operations
│   ├── providers/
│   │   └── sentence_transformer_provider.py Local embedding generator using MiniLM
│   ├── config.py                 Environment variables and static configuration
│   ├── logging.py                Centralized structured logger setup
│   └── redis.py                  Global Redis client connection
├── ingestion/
│   └── parser.py                 Extracts text from PDFs, falling back to RapidOCR if needed
├── data_processing/
│   └── chunkers/
│       └── semantic_chunker.py     Splits text and merges sentences by embedding similarity
├── workers/
│   ├── base_worker.py            Base class for consuming messages from a Redis stream
│   ├── chunk_worker.py           Pulls PDFs, parses, semantically chunks, and queues for embedding
│   └── embedding_worker.py       Pulls text chunks, generates vectors, and upserts to Qdrant
├── db/
│   ├── models.py                 SQLAlchemy schema definitions (Users, ChatSessions)
│   ├── postgres.py               Postgres connection engine and session maker
│   └── qdrant_store.py           Qdrant vector store implementation
└── tests/mocks/                Fake LLM, embeddings, vector store, context provider
```

Postgres is only used for users and chat sessions, which we aren't really using while auth is skipped. Chat history is supposed to live in Qdrant.

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

# And for the UI
cd frontend && npm install && npm run dev
```

To run the background workers that handle parsing, chunking, and embedding:

```bash
python -m workers.chunk_worker
python -m workers.embedding_worker
```

Upload hits `POST /documents/upload`, which dumps a job on the `document_processing` stream. Chat is `POST /chat/sessions` then `POST /chat/sessions/{id}/chat` — the second one still needs the LLM stack hooked up.

The backend also uses WebSockets (`/documents/ws/progress/{document_id}`) tied to Redis PubSub to stream upload progress in real-time to the React frontend.
