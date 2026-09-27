# Universal Multi-Agent AI Assistant Foundation

A production-ready foundation for a Universal Multi-Agent AI Assistant. The system features a multi-agent cognitive architecture combining sequential planning, short/long-term memory management, and external tool execution using the Model Context Protocol (MCP).

## Technology Stack

- **Frontend**: Next.js 15, React, TypeScript, TailwindCSS, ShadCN UI
- **Backend**: FastAPI, Python 3.12, SQLAlchemy (Async), Uvicorn
- **Databases**: PostgreSQL (Short-term context), Qdrant (Long-term semantic memory)
- **Model Context Protocol**: Official MCP SDK Client Manager
- **LLM Gateway**: OpenAI GPT, Anthropic Claude, and Google Gemini with streaming/non-streaming options
- **DevOps**: Docker, Docker Compose

---

## Directory Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/            # API endpoints & subrouters (auth, agent, mcp)
│   │   ├── config/         # App settings & MCP configs
│   │   ├── core/           # Logging, JWT Auth, and Global Exception handlers
│   │   ├── database/       # PostgreSQL (SQLAlchemy) & Qdrant vector DB clients
│   │   ├── llm/            # LLM Gateway interface & provider classes
│   │   ├── agents/         # Planner Agent & Memory Agent skeletons
│   │   ├── memory/         # Short-term & long-term memory coordinator
│   │   ├── mcp/            # Model Context Protocol client manager
│   │   ├── tools/          # Native backend-defined tools base interface
│   │   └── workflows/      # Multi-agent loop orchestrator
│   ├── tests/              # Pytest backend test suite
│   ├── Dockerfile          # Production-ready Python build definition
│   └── requirements.txt    # Python packages
├── frontend/               # Next.js 15 app
│   ├── src/                # Next.js App Router codebase
│   └── Dockerfile          # Node-based builder definition
├── docs/                   # System design & architecture details
├── docker-compose.yml      # Service coordinator (App, DBs, Vector DB)
└── README.md               # Setup & usage manual
```

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js (v18+ or v20+)
- Python (v3.12)

### Quick Start (Local macOS - No Docker Required)

Everything is set up and configured for local execution:

1. **Start the application**:
   ```bash
   ./start.sh
   ```
   This automatically starts the FastAPI backend (with all 12 MCP servers) on port 8000 and the Next.js frontend on port 3000.

2. **Stop the application**:
   ```bash
   ./stop.sh
   ```
   Or press `Ctrl+C` in the terminal running `./start.sh`.

3. **Re-run full setup if needed**:
   ```bash
   ./setup.sh
   ```

4. **Access the Web Interfaces**:
   - **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Backend Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Quick Start with Docker
The full stack (FastAPI, Next.js, Postgres, Qdrant) can also be run using docker-compose:

1. Setup your API keys in the environment or `.env` file at the root:
   ```env
   OPENAI_API_KEY=your-openai-key
   ANTHROPIC_API_KEY=your-anthropic-key
   GEMINI_API_KEY=your-gemini-key
   ```
2. Run docker-compose:
   ```bash
   docker compose up --build
   ```
3. Access:
   - Frontend Dashboard: `http://localhost:3000`
   - Backend Swagger Docs: `http://localhost:8000/docs`
   - Qdrant Dashboard: `http://localhost:6333/dashboard`

---

## Architecture Flow

The system runs a **Multi-Agent Reasoning Loop**:
1. **Request Intake**: User sends a prompt via Next.js to the FastAPI `/api/agent/chat` endpoint.
2. **Context Assembly**: The **Memory Manager** loads short-term history and queries Qdrant for semantic facts.
3. **Execution Planning**: The **Planner Agent** parses the query and list of MCP tools, returning a step-by-step `ExecutionPlan`.
4. **Tool Execution**: The **Orchestrator** loops through steps, calling external tools through the **MCP Client** (running stdio or SSE connections) and emitting execution logs to the chat screen.
5. **Synthesis**: The **LLM Gateway** synthesizes the tool results and streams the final message to the client.
6. **Memory Save**: **Memory Agent** extracts new facts, Qdrant indexes the embedding, and PostgreSQL appends the message.
