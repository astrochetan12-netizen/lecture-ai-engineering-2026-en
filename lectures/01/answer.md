# Lecture 01 Answers

## Exercises

- Model's answer to the course-specific question (the 3 homework levels; a summary is fine):
  When asked *"What are the 3 homework levels in the AIE2026 course?"*, the base model (`gemini-3.5-flash-lite`) hallucinated a plausible-sounding but completely incorrect three-tier curriculum:
  1. *Level 1: Beginner / Core (The Essentials)*
  2. *Level 2: Intermediate / Applied (The Standard)*
  3. *Level 3: Advanced / Production-Grade (The Challenge)*

- What you noticed when comparing it with the correct meaning in the glossary:
  In `data/glossary.json` under `homework-levels`, the actual course levels are defined as:
  - **Basic**: Review lecture content.
  - **Implementation**: Write your own code.
  - **Advanced**: Research and experimentation.
  The bare LLM answered with high confidence despite not having access to the private course materials or glossary, demonstrating that foundation models will fabricate reasonable-sounding general answers when domain-specific grounding (such as RAG or tools) is missing.

- Token counts you displayed (input / output):
  Using the added `_display_tokens()` hook reading `response.usage_metadata`:
  - For the default course question: `[tokens] input: 21, output: 153`
  - For the test query *"What is LoRA?"*: `[tokens] input: 11, output: 531`

---

## Homework

- **Level attempted**: Advanced (also completed Basic and Implementation)
- **Models used**: `gemini-3.5-flash-lite` (default), `gemini-3.5-flash`, `gemini-3.1-flash-lite`

### Basic

**Question asked:** *"Explain LoRA in 3 sentences."* (3 repeats per model = 9 total calls)

| Model | Run 1 Tokens (Out) / Latency | Run 2 Tokens (Out) / Latency | Run 3 Tokens (Out) / Latency | Mean Latency | Mean Tokens |
|---|---|---|---|---|---|
| `gemini-3.5-flash-lite` | 91 tok / 1.60s | 89 tok / 0.94s | 84 tok / 0.89s | **1.14s** | **88.0** |
| `gemini-3.5-flash` | 75 tok / 5.91s | 90 tok / 5.96s | 87 tok / 4.56s | **5.48s** | **84.0** |
| `gemini-3.1-flash-lite` | 83 tok / 15.59s | 82 tok / 45.64s | 82 tok / 5.30s | **22.18s** | **82.3** |

**Observations:**
- All models strictly followed the 3-sentence constraint.
- `gemini-3.5-flash-lite` exhibited extremely fast time-to-first-token and overall latency (under 1.2s average).
- `gemini-3.5-flash` was slower (~5.5s) and used markdown bolding and more formal phrasing.
- `gemini-3.1-flash-lite` experienced significant latency spikes (ranging from 5.30s to 45.64s).
- **Temperature note**: Temperature is not configurable in the provided `app/config.py` (no `config` parameter is passed to `generate_content`). Per instructions, temperature was not arbitrarily invented, and models were compared using their default settings.

---

### Implementation

**What I changed in `app/ask.py`:**
1. **Added Token Usage Display:** Implemented `_display_tokens(response)` checking `response.usage_metadata.prompt_token_count` and `candidates_token_count` to address the `TODO(Lecture 01 exercise)`.
2. **Conversation History Support:** Added `chat_turn(history, user_message, client, model)` which appends the user prompt `{"role": "user", "parts": [{"text": ...}]}`, calls `client.models.generate_content(model=model, contents=history)`, and appends the model's reply `{"role": "model", "parts": [{"text": ...}]}` in place.
3. **Interactive Mode (`--chat`):** Added a CLI flag `--chat` in `main()` invoking `chat_loop()`. Users can converse continuously, and each successive question preserves full past context. Exit triggers include typing `exit`, `quit`, or pressing EOF (Ctrl-D / Ctrl-Z).
4. **Backward Compatibility:** Preserved the exact behavior of `python -m app.ask "question"` for non-interactive single queries.

**How I tested it:**
- Created `tests/test_ask.py` with mock objects `FakeGenAIClient` and `FakeResponse`.
- Tested single-turn querying (`test_ask_single_turn_calls_model`).
- Tested multi-turn memory (`test_chat_turn_preserves_conversation_history`), explicitly verifying that the 2nd API call's `contents` argument contains the 1st turn's user prompt and model response plus the new question.
- Ran tests:
  ```
  pytest -q tests/test_ask.py tests/test_tools.py
  ......... [100%]
  9 passed in 1.08s
  ```

---

### Advanced

**Benchmark Design:**
- **3 Models**: `gemini-3.5-flash-lite`, `gemini-3.5-flash`, `gemini-3.1-flash-lite`
- **4 Question Types**:
  - `factual`: *"What does the abbreviation LoRA stand for?"*
  - `explanatory`: *"Explain what Low-Rank Adaptation (LoRA) is and why it reduces GPU memory usage."*
  - `long_form`: *"Write a detailed guide comparing full parameter fine-tuning, LoRA, and prompt engineering, covering memory and performance trade-offs."*
  - `reasoning`: *"A 70B model has 80 weight matrices of size 8192x8192. If LoRA is applied with rank r=8, calculate the exact parameter count of these LoRA adapters (A and B matrices) and show steps."*
- **3 Repeats** per combination = 36 total scheduled API calls.
- Measured: Latency in seconds (`time.perf_counter()`), prompt input tokens, output candidate tokens, retry counts, and errors with exponential backoff on HTTP 429 and 503.

**Measured Results by Model:**

| Model | Success / Total | Mean Latency | Min Latency | Max Latency | Mean Out Tokens | Retries Handled |
|---|---|---|---|---|---|---|
| `gemini-3.5-flash-lite` | **12 / 12** | **4.79s** | **1.11s** | **9.01s** | 924.8 | 0 |
| `gemini-3.5-flash` | **12 / 12** | **16.63s** | **3.81s** | **44.48s** | 1212.7 | 5 |
| `gemini-3.1-flash-lite` | **5 / 12** | **14.99s** | **6.43s** | **19.71s** | 566.6 | 10+ (7 exhausted) |

**Measured Results by Question Type:**

| Question Type | Successful Calls | Mean Latency | Mean In Tokens | Mean Out Tokens |
|---|---|---|---|---|
| `factual` | 7 | 3.68s | 10.0 | 117.7 |
| `explanatory` | 8 | 12.67s | 20.0 | 998.1 |
| `long_form` | 6 | 21.68s | 27.0 | 2584.7 |
| `reasoning` | 8 | 9.35s | 57.0 | 520.8 |

**Observations & Free-Tier Rate Limits:**
1. **Correlation between Token Length and Latency:** Latency is heavily dominated by output generation length rather than prompt processing. `factual` completed in ~3.7s (mean ~118 output tokens), whereas `long_form` averaged ~21.7s (mean ~2585 output tokens).
2. **Model Behavior:** `gemini-3.5-flash-lite` was by far the most resilient and responsive, completing 100% of calls without needing a single retry. `gemini-3.5-flash` produced significantly richer output (+31% tokens), but required 5 exponential backoff retries when encountering server busy 503 states.
3. **503 Server Unavailable vs 429 Rate Limits:**
   - Under the Gemini API free tier, rate limits are stated as 15 RPM (Requests Per Minute) and 1,000,000 TPM for Flash models.
   - We paced requests with 1.2s intervals between calls, staying well within normal quota bounds.
   - Despite staying under the nominal RPM, `gemini-3.1-flash-lite` suffered repeated `503 Service Unavailable` errors (7 calls completely failed even after 4 exponential backoff retry cycles of 3s, 5s, 9s, 17s). This indicates that the 3.1-flash-lite cluster currently experiences backend resource contention on the free tier endpoint, whereas 3.5-generation clusters handled the same load smoothly.

---

### Things that didn't work / surprises

1. **Perception vs. Measurement Divergence (METR Study Insight):**
   Prior to empirical testing, one might assume that older `3.1-flash-lite` and newer `3.5-flash-lite` would have similar throughput since both are "lite" models. In reality, `3.5-flash-lite` was 3x faster on basic queries and 100% reliable, while `3.1-flash-lite` failed over 58% of benchmark requests due to backend 503s. Measuring was essential to reveal this operational difference.
2. **Windows Asyncio Subprocess Deadlock:**
   The course's pre-existing `tests/test_agent.py` and `tests/test_mcp_server.py` attempted to spawn subprocesses or run asynchronous loops that stalled on Windows due to proactor pipe differences. To keep the project clean and regression-free without modifying existing test files, our new tests in `tests/test_ask.py` used clean object-level mocking, running in ~1s.
3. **No 429 Errors, only 503s:**
   We anticipated hitting rate limit 429s on the free tier, but our inter-request delay prevented 429s. Instead, transient 503s became the primary failure mode, proving the necessity of exponential backoff.
