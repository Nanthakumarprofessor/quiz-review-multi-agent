# Quiz & Review Multi-Agent System

An agentic AI quiz generation and answer evaluation system built with Python, LangGraph, LangChain, Ollama, FastAPI, and PostgreSQL, featuring dynamic multi-step orchestration, tool-based question generation, and educational review feedback.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-llama3.1-orange.svg)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

QuizMaster AI is a multi-agent assessment system that orchestrates specialized AI sub-agents through a LangGraph ReAct loop. A single API request triggers a four-phase workflow:

1. **Quiz Generation** — a sub-agent LLM produces structured JSON questions on any topic and difficulty level
2. **Answer Collection** — answers arrive either programmatically via the JSON payload or interactively through terminal stdin (Human-in-the-Loop)
3. **Answer Review** — a second sub-agent evaluates each answer and generates constructive, educational feedback
4. **Structured Output** — results are returned as a typed Pydantic `AgentResponse` model

The MainAgent uses LangGraph's `create_react_agent` with a **dynamic, per-step callable prompt** that injects the correct system instructions and restricts the active tool set at each phase — ensuring the agent never calls the wrong tool at the wrong time.

---

## Architecture

```mermaid
flowchart TD
    A([Client / Postman]) -->|POST /api/v1/chat| B[FastAPI Route]
    B --> C[ChatService\nSingleton lifecycle]
    C --> D[MainAgent\nLangGraph ReAct Agent\nInMemorySaver Checkpointer]

    D -->|Phase 1: current_step = quiz_step\nDynamic prompt + quiz tool only| E[Quiz Agent Tool\nSub-LLM generates\nJSON questions]
    E -->|LangGraph Command\nToolMessage → state| D

    D -->|Phase 2: Answer collection| F{Answer source}
    F -->|answers in request payload| G[API JSON answers]
    F -->|no answers provided| H[Terminal stdin\nHuman-in-the-Loop]
    G --> I[qa_pairs string]
    H --> I

    I -->|Phase 3: current_step = review_step\nDynamic prompt + review tool only| J[Review Agent Tool\nSub-LLM evaluates\ncorrectness + feedback]
    J -->|LangGraph Command\nToolMessage → state| D

    D -->|Phase 4: Structured output| K[AgentResponse\nPydantic model]
    K -->|JSON| A

    D -.->|On error| L[(PostgreSQL\nerror_logs table)]

    style D fill:#1a1a2e,color:#e0e0e0
    style E fill:#16213e,color:#e0e0e0
    style J fill:#16213e,color:#e0e0e0
    style L fill:#0f3460,color:#e0e0e0
```

On any unhandled exception, both the route handler and the service layer independently capture the error and write a structured record to the `error_logs` PostgreSQL table via `ClientErrorRepository`.

---

## Key Features

| Feature | Detail |
|---|---|
| **Multi-Agent Orchestration** | LangGraph ReAct agent coordinates two specialised sub-agent tools in a defined sequence |
| **Dynamic Step-Config Prompts** | A callable `prompt_fn` inspects `current_step` at runtime and injects the correct system prompt and validates required state fields before each agent invocation |
| **LangGraph `Command` + `InjectedToolCallId`** | Tools return `Command(update={...})` objects to write `ToolMessage` results directly into graph state, avoiding manual state stitching |
| **Dual-Mode Answer Input** | Answers supplied in the `answers` JSON array are used directly; if omitted, the agent pauses and collects answers interactively from the terminal |
| **Educational Review Feedback** | The review agent identifies correct/incorrect answers, explains reasoning, and provides the correct answer where the user was wrong |
| **PostgreSQL Error Telemetry** | All exceptions are persisted to `error_logs` with request ID, function name, file, error class, and truncated traceback |
| **Auto Database Migration** | `Migration.create_tables()` runs on startup via the FastAPI lifespan manager — no manual SQL required |
| **Local-First LLM** | Powered by Ollama `llama3.1:latest` by default — zero API costs, fully offline |
| **Optional AWS Bedrock Fallback** | Switch `LLM_PROVIDER=bedrock` in `.env` to route all LLM calls through Amazon Bedrock (Claude or other models) |
| **FastAPI Async Web Layer** | Async lifespan management, CORS middleware, interactive Swagger UI at `/docs` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Agent Framework | LangGraph 0.2+, LangChain 0.3+ |
| Local LLM | Ollama (`llama3.1:latest`) |
| Cloud LLM (optional) | AWS Bedrock (Claude 3 Haiku) via `langchain-aws` |
| Web Framework | FastAPI 0.115+ |
| ASGI Server | Uvicorn |
| Data Validation | Pydantic v2, pydantic-settings |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| DB Driver | psycopg2-binary / psycopg3 |

---

## Project Structure

```
quiz-review-multi-agent/
│
├── quiz_agent/                     # Main application package
│   ├── agent/
│   │   ├── agent.py                # MainAgent, QuizState, dynamic prompt callable, step-config
│   │   ├── system_prompt.py        # Per-step system prompts + sub-LLM tool prompts
│   │   └── tools.py                # make_quiz_agent_tool / make_review_agent_tool (LangGraph Command)
│   │
│   ├── migration/
│   │   └── create_tables.py        # SQLAlchemy table auto-creation on startup
│   │
│   ├── models/
│   │   └── chat_models.py          # ChatRequestDTO, AgentResponse (Pydantic)
│   │
│   ├── repositories/
│   │   ├── database/
│   │   │   ├── connection.py       # SQLAlchemy engine + test_connection()
│   │   │   ├── session.py          # SessionLocal factory, get_db() dependency
│   │   │   └── models.py           # Re-exports ORM models
│   │   ├── schemas/
│   │   │   └── schema.py           # ErrorLog ORM model (error_logs table)
│   │   └── client_error_repository.py  # log_error() — persists exceptions to DB
│   │
│   ├── routes/
│   │   └── chat_router.py          # POST /chat endpoint + error logging
│   │
│   ├── service/
│   │   └── chat_service.py         # ChatService singleton, lazy MainAgent init
│   │
│   ├── utils/
│   │   └── logger.py               # Structured stdout logger (quiz_agent)
│   │
│   ├── main.py                     # FastAPI app factory, lifespan, /health endpoint
│   ├── settings.py                 # Pydantic BaseSettings — all config from .env
│   ├── requirements.txt
│   └── .env.example                # Safe template — copy to .env and fill in values
│
├── test_agent.py                   # Direct MainAgent test (no HTTP, runs async)
├── test_client.py                  # HTTP test against the running FastAPI server
├── README.md
└── .gitignore
```

---

## How the Agent Works

The agent lifecycle is driven by two sequential `ainvoke` calls on the same LangGraph thread (identified by `thread_id = f"quiz_{user_id}"`), sharing state via `InMemorySaver`.

### Phase 1 — Quiz Generation

`current_step` is set to `"quiz_step"`. The dynamic `prompt_fn` callable reads this, injects `QUIZ_STEP_PROMPT` (formatted with topic, difficulty, and count), and restricts the tool list to `[quiz_agent]` only. The ReAct loop calls `quiz_agent`, which invokes the sub-LLM to produce a JSON array of questions, then writes a `ToolMessage` back into graph state via `Command(update={...})`. The agent terminates after the tool call completes.

### Phase 2 — Answer Collection

`_extract_questions()` walks `state["messages"]` in reverse, finds the `ToolMessage`, and parses the JSON question list. If the request payload includes an `answers` array, those are used directly. Otherwise, the system prompts the user on the terminal for each question (Human-in-the-Loop mode). All Q&A pairs are assembled into a `qa_pairs` string.

### Phase 3 — Answer Review

A second `ainvoke` on the same thread sets `current_step` to `"review_step"`. The `prompt_fn` injects `REVIEW_STEP_PROMPT` (with `qa_pairs`) and restricts tools to `[review_agent]` only. The review sub-agent evaluates each answer and returns structured textual feedback via another `Command` + `ToolMessage`.

### Phase 4 — Structured Output

`_extract_feedback()` retrieves the review `ToolMessage` content. The result is wrapped in an `AgentResponse(user_id, response)` Pydantic model and returned as JSON.

---

## Example API Request & Response

**Request — `POST /api/v1/chat`**

```json
{
  "user_id": 1,
  "query": "Python Data Structures",
  "difficulty": "medium",
  "questions_count": 3,
  "answers": [
    "A list is an ordered, mutable sequence",
    "A dictionary stores key-value pairs with O(1) average lookup",
    "Sets are unordered collections of unique elements"
  ]
}
```

> Omit `"answers"` to switch to interactive terminal mode.

**Response**

```json
{
  "response": {
    "user_id": 1,
    "response": "Q1: ✅ Correct! A list is indeed an ordered, mutable sequence in Python.\n\nQ2: ✅ Correct! Dictionaries use hash tables providing O(1) average-case lookup.\n\nQ3: ✅ Correct! Sets are unordered collections that automatically enforce uniqueness..."
  }
}
```

---

## Setup & Local Run

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running locally
- PostgreSQL running (default port `5433`, or update `DATABASE_URL`)

### 1. Pull the LLM model

```bash
ollama pull llama3.1:latest
```

Verify Ollama is running:
```bash
ollama list
```

### 2. Clone & create a virtual environment

```bash
git clone https://github.com/<your-username>/quiz-review-multi-agent.git
cd quiz-review-multi-agent

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r quiz_agent/requirements.txt
```

### 4. Configure environment

```bash
cp quiz_agent/.env.example quiz_agent/.env
```

Edit `quiz_agent/.env` and set your PostgreSQL connection string:

```env
DATABASE_URL=postgresql://postgres:your_password@localhost:5433/quiz_db
```

All other defaults work out of the box for a local Ollama setup.

### 5. Start the server

```bash
cd quiz_agent
python main.py
```

The server starts at `http://localhost:8001`. Database migrations run automatically on startup.

```
============================================================
Quiz & Review Multi-Agent System STARTING
============================================================
Database connected successfully
Running database migrations...
Database migrations completed successfully
Server ready at http://0.0.0.0:8001
API Docs available at http://0.0.0.0:8001/docs
LLM Provider: ollama (llama3.1:latest)
============================================================
```

### 6. Test the system

**Option A — Swagger UI** (easiest)

Open `http://localhost:8001/docs` in your browser and use the interactive `/api/v1/chat` form.

**Option B — HTTP test script**

With the server running, from the project root:
```bash
python test_client.py
```

**Option C — Direct agent test** (no HTTP, no server needed)

```bash
python test_agent.py
```

**Option D — Postman / curl**

```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "query": "Python Basics",
    "difficulty": "easy",
    "questions_count": 2,
    "answers": ["Guido van Rossum", "Indentation defines code blocks"]
  }'
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check — returns service name and active LLM provider |
| `POST` | `/api/v1/chat` | Start a full quiz generation + evaluation session |

### `POST /api/v1/chat` — Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | `int` | ✅ | Unique identifier for the quiz session thread |
| `query` | `string` | ✅ | Topic for the quiz (e.g. `"Python Data Structures"`) |
| `difficulty` | `string` | ✅ | Difficulty level: `easy`, `medium`, or `hard` |
| `questions_count` | `int` | ✅ | Number of questions to generate |
| `answers` | `string[]` | ❌ | Pre-supplied answers; omit to use interactive terminal mode |

---

## Engineering & Architectural Highlights

**ReAct loop termination** — After a `ToolMessage` lands in state, `prompt_fn` detects it and injects a hard stop instruction (`"Do NOT call any more tools. Summarize..."`) so the agent exits the loop cleanly without additional LLM calls.

**StateSchema compliance** — `QuizState` extends `MessagesState` with `NotRequired` typed extras (`remaining_steps`, `current_step`, `topic`, `difficulty`, `questions_count`, `qa_pairs`). Using `NotRequired` satisfies LangGraph's strict state schema validation while keeping fields optional between phases.

**Tool closure pattern** — `make_quiz_agent_tool(llm)` and `make_review_agent_tool(llm)` are factory functions that close over the `llm` instance at construction time. This injects the LLM dependency without globals or service locators, and makes each tool independently testable.

**`InjectedToolCallId` + `Command`** — Tools receive `tool_call_id` as an `Annotated[str, InjectedToolCallId]` parameter injected by LangGraph (never sent by the LLM). They return a `Command(update={"messages": [ToolMessage(...)]})` to write results directly into the graph's message state, preserving the full ReAct message chain.

**Dual-layer error isolation** — Both `chat_router.py` and `chat_service.py` independently catch exceptions and write to `ClientErrorRepository`. This ensures errors at any layer are persisted even if the other layer also fails.

**Lazy agent initialization** — `ChatService.ensure_agent()` initialises `MainAgent` on the first request rather than at import time. This avoids blocking the FastAPI startup and allows the Ollama connection to be established only when needed.

---

## Future Improvements

- **Web frontend** — A React or Next.js UI for taking quizzes interactively in the browser, replacing the terminal stdin mode
- **Persistent quiz history** — Store per-user quiz attempts, scores, and feedback in PostgreSQL for progress tracking over time
- **Multiple choice support** — Extend the quiz generation tool to produce MCQ format with lettered options, in addition to open-ended questions
- **Streaming responses** — Use FastAPI `StreamingResponse` and LangGraph's `astream_events` to stream review feedback token-by-token to the client
- **Multi-topic session continuity** — Allow a single conversation thread to span multiple quiz rounds on different topics using LangGraph's persistent checkpointer

---

## Repository

**Name:** `quiz-review-multi-agent`

**Description:** Multi-agent quiz generation and answer evaluation system built with Python, LangGraph, LangChain, Ollama, FastAPI, and PostgreSQL.

**Topics:** `python` `langgraph` `langchain` `ollama` `agentic-ai` `multi-agent-systems` `fastapi` `postgresql` `ai-agent` `llm`

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
