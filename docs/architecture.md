# System Architecture: Universal Multi-Agent AI Assistant

This document outlines the architecture design, component layers, and message flows of the Universal Multi-Agent AI Assistant.

## Overview

The assistant is an autonomous multi-agent cognitive system capable of decomposing user prompts, executing actions via Model Context Protocol (MCP) servers, maintaining contextual history (short-term memory), and storing knowledge graphs (long-term memory).

```
                      +-------------------+
                      | Next.js Frontend  |
                      +---------+---------+
                                |
                                | (HTTP/SSE Chat Stream)
                                v
                      +---------+---------+
                      |  FastAPI Backend  |
                      +---------+---------+
                                |
                                v
                    +-----------+-----------+
                    |  Workflow Orchestrator |
                    +-----------+-----------+
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
+-------+-------+       +-------+-------+       +-------+-------+
| Planner Agent |       | Memory Manager|       |  MCP Client   |
+-------+-------+       +-------+-------+       +-------+-------+
        |                       |                       |
        | (Reasoning/Plan)      | (Get Context/Persist) | (Execute tools)
        v                       v                       v
+-------+-------+       +-------+-------+       +-------+-------+
|  LLM Gateway  |       | PostgreSQL /  |       | MCP Servers   |
| (GPT/Claude/  |       |  Qdrant DB    |       | (Sqlite/Fetch)|
|    Gemini)    |       +---------------+       +---------------+
+---------------+
```

## System Components

### 1. Frontend Layer
- **Next.js 15**: Builds the reactive user interface.
- **Tailwind CSS & ShadCN**: Drives styling using a modern, unified design system.
- **SSE Client Connection**: Connects to the backend via Server-Sent Events to render real-time execution steps and status logs (e.g. "Running Tool sqlite-server...") alongside streaming text.

### 2. FastAPI Backend Layer
- Exposes API endpoints for Authentication, MCP Discovery, and Agent Workflow Execution.
- Implements custom exception mapping, standard JWT token security dependencies, and structured JSON logs.

### 3. Workflow Orchestrator
- Functions as the core runner. It coordinates between components in a loop:
  1. Requests history from the **Memory Manager**.
  2. Queries the **MCP Client** for available tools.
  3. Sends the goal to the **Planner Agent** to generate an execution plan.
  4. Loops through steps, invoking relevant tools via the **MCP Client**.
  5. Feeds the accumulated execution trace to the **LLM Gateway** to compile the final response.
  6. Persists short-term history and indices long-term facts asynchronously.

### 4. Planner Agent
- Breaks down complex requirements into a list of structured `PlanSteps` containing targets, tools, and arguments.

### 5. Memory Manager & Memory Agent
- **Short-Term Memory**: Stores full session chat message transcripts in PostgreSQL.
- **Long-Term Memory**: Employs a **Memory Agent** to extract facts, preferences, and details from conversations, compiles vector embeddings, and indexes them in Qdrant.
- Queries Qdrant semantic search on startup to provide user-context injection to the LLM.

### 6. LLM Gateway
- Standardized wrapper client abstraction supporting OpenAI (GPT), Anthropic (Claude), and Google (Gemini) with streaming and non-streaming behaviors.

### 7. MCP Client & Servers
- Integrates the official Anthropic Model Context Protocol SDK.
- Launches and manages connections to multiple local subprocess servers (using `stdio`) and remote services (via `SSE`).
- Handles tool discovery, schema matching, and routing execution payloads.
