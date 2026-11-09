# Lecture 03 Answers

## Exercises

- Differences between the Lecture 01 (bare LLM) and agent answers:
  In Lecture 01 (`app.ask`), the bare LLM relied solely on its general pretraining weights. When asked about course-specific concepts such as "What are the 3 homework levels in the AIE2026 course?", it gave generic or hallucinated responses. In Lecture 03 (`app.agent`), the agent recognized course-specific terminology, called the `search_glossary` tool with query `"3 homework levels"`, retrieved the exact ground-truth entry from `data/glossary.json`, correctly listed the three levels (Basic: Review lecture content, Implementation: Write your own code, Advanced: Research and experimentation), and concluded with the relevant session citation `(Lecture 01)`.

- Tool calls shown by `--trace` (tool names and arguments):
  When asked `"What is the difference between LoRA and QLoRA?"` with `--trace`:
  - `[tool call] search_glossary({'query': 'LoRA'})`
  - `[tool call] search_glossary({'query': 'QLoRA'})`
  Both tool calls returned matching terms and definitions from the glossary, which the agent combined to contrast standard precision weight adaptations with quantized 4-bit base weights.

- Number of LLM calls for one question (`requests`):
  `requests`: 2
  - Request 1: The model received the user question and system instructions, and generated the two tool calls to look up "LoRA" and "QLoRA".
  - Request 2: The model received the tool return outputs and synthesized the final comparative answer.
  Total token usage was 2,172 tokens (1,917 input tokens + 255 output tokens), with a run cost of $0.0012126.

- Tool added and the description in its docstring:
  Added `make_quiz(lecture: int) -> str` in `app/tools.py` and registered it with `agent.tool_plain(tools.make_quiz)` in `app/agent.py`.
  Docstring:
  ```python
  """Generate a review question from the glossary for the specified lecture session (an integer starting at 1).

  Use when asked for a review question, quiz, or check question about a specific lecture (for example, "Give me one review question from Lecture 02").
  """
  ```
  Verified via `--trace "Give me one review question from Lecture 02"`, which produced `[tool call] make_quiz({'lecture': 2})` and returned a targeted question and answer pair.

## Homework

- Level attempted: Implementation

- What you did:
  1. Implemented `save_learning_log(topic, what_learned, key_points, reflection="", filename=None) -> str` in `app/tools.py`:
     - Creates the `learning_log/` directory automatically if it does not exist.
     - Saves learning logs in structured, UTF-8 encoded Markdown files including timestamp, topic, summary, bullet points, and optional reflection.
     - Generates safe, readable filenames formatted as `YYYYMMDD_HHMMSS_<slug>.md`.
     - Prevents silent overwriting: if a target file already exists, it safely appends incremental counter suffixes (`_1.md`, `_2.md`).
     - Hardened against path traversal: validates that all paths resolve strictly within `learning_log/` using `target_path.relative_to(LOG_DIR.resolve())`, returning an explicit error message if an attempt escapes the directory.
  2. Registered `save_learning_log` in `app/agent.py` using `agent.tool_plain(tools.save_learning_log, requires_approval=True)` and set `output_type=[str, DeferredToolRequests]`.
  3. Added interactive human-in-the-loop CLI handling in `app/agent.py`:
     - Pauses when `isinstance(result.output, DeferredToolRequests)`.
     - Displays the tool name and formatted JSON arguments.
     - Asks the user `Allow '<tool_name>' to proceed? [y/N]: ` with safe EOF/interrupt handling.
     - Bundles decisions via `result.output.build_results(approvals=approvals)`.
     - Resumes execution by passing `deferred_tool_results` and `message_history=result.all_messages()` back to `target.run_sync()`.
     - Updated instructions so that if a user rejects an action, the agent accepts the choice and does not retry calling the tool.
  4. Expanded unit testing in `tests/test_tools.py` and `tests/test_agent.py`:
     - Added tests for `make_quiz` with valid and non-existent lectures.
     - Added tests for directory creation, markdown content writing, non-overwriting behavior, and path traversal rejection.
     - Added tests for `TestModel` deferred tool pausing, approval execution (file written), and rejection execution (file not written, `outcome="denied"`).

- Results:
  - All 17 automated tests pass (`pytest -q tests/test_agent.py tests/test_tools.py`):
    `17 passed in 5.25s`
  - Tool inspection verified (`python -m app.agent --list-tools`):
    Lists all 4 tools (`search_glossary`, `get_lecture_summary`, `make_quiz`, `save_learning_log`) with clear parameters and schemas.
  - Interactive approval test:
    Running `python -m app.agent --trace "Please save a learning log for Lecture 03 on AI Agents and human approval."` prompted for confirmation:
    `[approval required] Tool 'save_learning_log' requests execution.`
    Approving with `y` saved `learning_log/20261109_044419_ai_agents_and_human_approval.md` with complete notes and key points.
  - Interactive denial test:
    Running the same command and entering `n` denied the execution:
    `[tool return] save_learning_log -> The tool call was denied.`
    No file was created, and the agent politely responded: *"The operation to save your learning log was canceled because the tool call was denied."*

- Observations and questions:
  - Human-in-the-Loop for Irreversible Actions: Read-only operations (like searching a glossary or fetching a summary) can run autonomously, but write operations (saving files, modifying databases, sending network requests) need verification. `requires_approval=True` provides an elegant boundary without polluting tool logic with interactive I/O.
  - Loop Control on Rejection: During initial rejection testing, without explicit instruction, the model tended to treat the denial as an invitation to retry the tool call with identical arguments. Instructing the agent to respect rejections and adding defensive input handling in the CLI loop was critical to prevent infinite approval loops.
  - Ergonomics of `DeferredToolRequests`: Combining `output_type=[str, DeferredToolRequests]` with `message_history` preserves full agent context across execution steps, making human approval flows natural to implement in terminal and web UI environments alike.
