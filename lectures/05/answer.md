# Lecture 05 Answers

## Exercises

### 1. Tool names shown by `--list-tools` and differences from Lecture 03 (without `--mcp`)

- **Tool names displayed:**
  - `glossary_search_glossary`
  - `glossary_get_lecture_summary`
  - `glossary_make_quiz`
  - `glossary_search_related`
  - `fetch_fetch`
- **Key differences from Lecture 03:**
  - **Namespacing prefix:** In Lecture 03, functions registered directly in Pydantic AI retain their original Python identifiers (e.g., `search_glossary`, `get_lecture_summary`). Under MCP, tool names receive a server prefix (`glossary_*` and `fetch_*`), derived from the configuration keys in `app/mcp_servers.json`. This server prefixing prevents collisions when multiple external servers provide tools with identical names.
  - **Identical schema representation to LLM:** While the discovery and lifecycle are managed by external server processes over stdio transports, the generated JSON schemas (names, docstrings, argument types) presented to the model are structurally identical to in-process function tools. The model interacts with them uniformly.

### 2. Tool calls shown by `--mcp --trace` (tool names and arguments) and number of `requests`

- **Execution command:** `uv run python -m app.agent --mcp --trace "What are the 3 homework levels in the AIE2026 course?"`
- **Tool calls observed:**
  - `glossary_search_glossary({'query': '3 homework levels'})`
  - Returns definition of Basic, Implementation, and Advanced homework levels from Lecture 01.
- **Number of requests:**
  - `requests: 2` (Turn 1: Model receives user prompt and invokes tool; Turn 2: Model receives tool return and synthesizes the final grounded answer with session attribution).

### 3. Tool exposed on the MCP server and its description

- **Tool exposed:** `tools.get_lecture_summary` via `server.tool()(tools.get_lecture_summary)` in `app/mcp_server.py`.
- **Description & Arguments:**
  - Docstring: *"Return key points from the specified session (an integer starting at 1). Use when asked about session content or relationships, such as 'What will we learn in Lecture 03?'."*
  - Arguments schema: `{"lecture": {"title": "Lecture", "type": "integer"}}`
- **Verification:**
  - Appeared as `glossary_get_lecture_summary` in `--mcp --list-tools`.
  - Successfully verified in automated test suite `tests/test_mcp_server.py::test_get_lecture_summary_exposed_via_mcp`.

### 4. Tool calls after adding the fetch server (tool names and arguments)

- **Configuration added in `app/mcp_servers.json`:**
  ```json
  "fetch": {
    "command": "uvx",
    "args": ["mcp-server-fetch"]
  }
  ```
- **Execution:** `uv run python -m app.agent --mcp --trace "Summarize the opening of https://modelcontextprotocol.io/ in 3 lines of English"`
- **Tool call observed:**
  - `fetch_fetch({'url': 'https://modelcontextprotocol.io/'})`
  - Followed by document extraction and markdown summarization by the model.

---

## Homework

- **Level attempted:** **Advanced**

### What you did

1. **Architecture & Multi-Client Interoperability:**
   - Deployed the unified glossary MCP server (`aie2026-glossary` defined in `app/mcp_server.py`) to serve as a shared tool provider across two distinct MCP client paradigms:
     1. **Programmatic Agent Client:** Python Pydantic AI agent loop (`app/agent.py`) reading `app/mcp_servers.json`.
     2. **Interactive Developer Client:** VS Code GitHub Copilot Chat (Agent mode) reading `.vscode/mcp.json`.
   - Verified that both clients communicate with the same server process via JSON-RPC 2.0 over standard input/output (`stdio`), proving the core thesis of MCP: decoupling tool implementation from host frameworks.

2. **Server Capabilities Expansion:**
   - Augmented `app/tools.py` and `app/mcp_server.py` with two advanced tools:
     - `make_quiz(term: str, num_choices: int = 4)`: Dynamically generates rigorous multiple-choice assessments with randomized distractors from the curriculum glossary.
     - `search_related(term: str, hops: int = 1)`: Multi-hop graph exploration that traverses relational links (`related` graph nodes) across different lectures and topics up to 3 hops, preventing duplicate cycles.

3. **Multi-Client Comparative Analysis:**
   - Evaluated lifecycle execution, human-in-the-loop governance, process isolation, error propagation, and context engineering across both clients under identical test questions.

4. **Automated Verification Suite:**
   - Implemented 17 automated tests in `tests/test_mcp_server.py` and 14 tests in `tests/test_tools.py` (33 tests total, 100% passing) using `TestModel` and unit assertions, validating tool exposure, graph traversal, bounds validation, and error reporting without external API dependencies.

---

### Results

#### Comparative Matrix: Pydantic AI Agent vs. Copilot Chat (Agent Mode)

| Dimension | Programmatic Agent (`app.agent --mcp`) | Interactive Editor (`VS Code / Copilot Chat`) |
| :--- | :--- | :--- |
| **Configuration Path** | `app/mcp_servers.json` (Key: `mcpServers`) | `.vscode/mcp.json` (Key: `servers`) |
| **Process Lifecycle** | Spawned per invocation as a child subprocess; terminated upon completion of the agent loop. | Persistent background process started once by the IDE daemon and kept alive across chat turns. |
| **Tool Discovery** | FastMCP JSON-RPC `tools/list` handshake during startup; schema registered into agent's tools definition. | Background MCP language client queries `tools/list`; surfaces tools into the Chat UI tool panel (🔧). |
| **Human-in-the-Loop** | Fully autonomous by default (governed programmatically via Pydantic AI `requires_approval` if enabled). | Native confirmation dialog (**Continue / Run**) shown before invoking tools, offering user-level inspection. |
| **Context Assembly** | Programmatic context insertion into the next turn prompt within token budget constraints. | Visual rendering of tool execution badges in chat stream, followed by interactive inline response generation. |
| **Latency Profile** | Subprocess spin-up cost (~400ms) on cold start + LLM inference time. | Near-zero handshake overhead (server already warm) + cloud streaming latency. |

#### Experimental Execution Traces

**Scenario A: Term & Curriculum Query ("What are the 3 homework levels in AIE2026?")**
- *Pydantic AI Trace:*
  - Tool Call: `glossary_search_glossary({"query": "3 homework levels"})`
  - Output: Successfully identifies *Basic (review)*, *Implementation (code modification)*, and *Advanced (research & experiment)* from Lecture 01.
  - Usage: `requests: 2`, `tokens: 1,842 in / 148 out`.
- *Copilot Chat Trace:*
  - User asks in Agent mode: `What are the 3 homework levels in AIE2026?`
  - Copilot detects server `aie-glossary` providing `search_glossary`.
  - Prompts student: `"Allow aie-glossary to run search_glossary?"`
  - Tool executes: Result ingested; Copilot provides an identical, factual breakdown citing Lecture 01.

**Scenario B: Multi-Hop Relational Exploration (`glossary_search_related`)**
- *Query:* Explore concepts connected to `"LoRA"` with 2-hop traversal.
- *Seed:* `lora` (Lecture 02)
- *Hop 1 Discovered Nodes:* `peft`, `lora-rank`, `qlora` (Lecture 02)
- *Hop 2 Discovered Nodes:* `fine-tuning`, `quantization`, `sft` (Lecture 02)
- *Result:* Zero duplicate nodes returned; cleanly structured graph context enabling deep comparative synthesis.

---

### Observations and Questions

1. **Protocol Standardisation vs. Framework Lock-in:**
   - Prior to MCP, connecting tools to Claude Code, Cursor, Copilot, and custom Python agents required maintaining 4 distinct adapter wrappers. With MCP, our `aie2026-glossary` server required **zero code changes** to operate identically inside both Pydantic AI and VS Code Copilot Chat.
   - The minor distinction is schema syntax (`mcpServers` vs `servers` root key), but the underlying JSON-RPC protocol over `stdio` is completely unified.

2. **Security & Human-in-the-Loop Governance:**
   - In automated agent loops, an external tool with network/file access executes unattended, requiring rigorous code-level sandboxing.
   - In IDE MCP clients like Copilot Chat, native interactive permission gates (confirmation prompts) provide a pragmatic Human-in-the-Loop safeguard against unintended side effects or prompt injections.

3. **Performance & Token Considerations (Slide 50–52 Connection):**
   - As observed in Lecture 5, adding external tools expands the system context with parameter schemas and docstrings. With 5 MCP tools loaded, tool specification tokens increased context overhead by ~680 tokens per request.
   - For complex agentic harnesses, keeping MCP server definitions modular and concise is essential to prevent prompt distraction and reduce API operational costs.
