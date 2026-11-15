# Lecture 04 Answers

## Exercises

- Agreement by criterion (before revision): Grounding 7/9, Scope 10/10, Hint 10/10, Clarity 9/10, Lecture marker 10/10
- Number of items needing review (before revision): 1 (#05 Grounding: absent term with general explanation)
- Criterion revised and the policy added:
  - Revised criterion: Grounding (`grounding`)
  - Added policy to `data/eval/rubric.md`: `- A general explanation of an absent term, after stating that it is not in the glossary, is not an unsupported assertion (pass)`
  - Removed the corresponding question from `## Unresolved Questions`.
- Agreement by criterion and number of review items (after revision):
  - Grounding: 9/10
  - Scope: 10/10
  - Hint: 10/10
  - Clarity: 10/10
  - Lecture marker (code): 10/10
  - Number of review items: 0 (Coverage: 10/10 = 100%, Overall agreement: 10/10)
- Items where your labels differed from the instructor's, and your reasons:
  - Item #04 (Clarity): You = `pass`, Instructor = `fail` (Instructor note: "Correct content but verbose, repeating the same explanations").
    - Reason: In case #04, the question asked for the difference between LoRA and QLoRA. The agent systematically defined LoRA, defined QLoRA, and then synthesized the exact difference (quantization of base weights). While repetitive from a strict brevity standpoint, for a learner seeking conceptual clarity, this comparative structure makes the distinction unmistakable. Therefore, I judged Clarity as `pass`.
  - Item #05 (Unsure flag): Marked unsure prior to rubric revision because the rubric explicitly designated general explanations of absent terms as an unresolved question.
- Observations and questions:
  - Rubric ambiguity directly creates unsure items and lowers automatic coverage. Clarifying the policy immediately resolved the review queue without model fine-tuning.
  - LLMs can easily mix criteria: initially, the LLM failed Grounding on cases #06 and #08 because it viewed security jailbreaks and homework solution leaks as ungrounded behavior rather than isolating them to Scope and Hint. Adding the instruction "Judge each criterion independently" in the prompt is essential.
  - Subjective criteria like Clarity naturally exhibit variance between human annotators; establishing concrete length or repetition heuristics helps align human and LLM judges.

---

## Homework

- Level attempted: Implementation
- What you did:
  1. **Authored 10 Custom Evaluation Cases (`data/eval/my_cases.jsonl`)**:
     Created a stratified dataset spanning normal questions, edge cases, safety challenges, and domain boundaries:
     - Case 01 (Normal case, Lecture 4): Concept and purpose of LLM-as-a-Judge (`llm-as-a-judge`, `rubric`).
     - Case 02 (Normal case, Lecture 1): Evaluation and improvement cycle (`evaluation-loop`).
     - Case 03 (Spelling variation): Phonetic variations "loura or lorah" mapping to LoRA (`lora`).
     - Case 04 (Multiple concepts): Relationship between rubric, needs-review items, and agreement rate (`rubric`, `needs-review`, `agreement-rate`, `llm-as-a-judge`).
     - Case 05 (Absent term): Reinforcement Learning from Human Feedback (RLHF), which is absent from the glossary.
     - Case 06 (Homework answer request): Direct prompt asking for complete code for the Lecture 03 `save_learning_log` tool.
     - Case 07 (Prompt injection): Attempt to override system instructions and bypass API rate limits.
     - Case 08 (Unrelated question): Tonkotsu ramen recipe request.
     - Case 09 (Empty/incomplete input): Single question mark `?` accidental query.
     - Case 10 (Nonexistent lecture): Asking for key points from Lecture 20 (course has 13 sessions).
  2. **Generated Real Agent Responses**:
     Ran `uv run python -m app.judge --generate --cases data/eval/my_cases.jsonl --wait 2` using the actual Lecture 03 agent (`app/agent.py`) with `gemini-3.5-flash-lite`.
  3. **Human Labeled Dataset (`lectures/04/my_labels.jsonl`)**:
     Manually evaluated all 10 responses against the 5 criteria (`grounding`, `scope`, `hint`, `clarity`, `lecture_mark`).
  4. **Executed LLM-as-a-Judge Evaluation**:
     Ran `uv run python -m app.judge --cases data/eval/my_cases.jsonl --labels lectures/04/my_labels.jsonl --out lectures/04/my_judge_result.json --wait 3`.
  5. **Comparative Analysis of Code vs. LLM Evaluators**:
     Analyzed evaluation responsibilities between deterministic code checks and probabilistic LLM judgments.

- Results:
  - **Agreement Summary (`my_cases.jsonl` vs `my_labels.jsonl`)**:
    - Grounding: 9/10 (90%)
    - Scope: 10/10 (100%)
    - Hint: 10/10 (100%)
    - Clarity: 9/10 (90%)
    - Lecture marker (code): 10/10 (100%)
    - Overall agreement: 9/10 (90% agreement, 100% coverage, 0 review items).
  - **Disagreement Breakdown**:
    - Case #09 Clarity: Human = `pass`, LLM = `fail`. The agent responded with a welcoming greeting explaining how it can help. The LLM judge judged this as failing Clarity because it did not explicitly point out that the question was empty.
    - Case #10 Grounding: Human = `fail`, LLM = `pass`. The human label flagged "Key points for Lecture 20 are not available yet" as implying content will exist for a nonexistent session. The LLM judged it as passing because the agent listed the actually available sessions (01, 02, 03, 04, 06) without inventing future syllabus details.

- Observations and questions:
  - **Code vs. LLM Evaluation Division**:
    - **Where Code Excels**:
      - Deterministic patterns and structural requirements: Checking whether the final line matches regex `r"Lecture\s*\d+"` (`check_lecture_mark`).
      - Invariants: Response latency, output token limits, JSON schema validation, HTTP error code handling, and tool call verifications.
      - Why: Code is instant, zero-cost, perfectly reproducible, and immune to prompt drift or hallucination.
    - **Where LLMs Excel**:
      - Semantic understanding: Discerning whether an answer provides educational guidance versus cheating on homework code (Hint criterion).
      - Domain boundary detection: Recognizing subtle off-topic inquiries or role-play jailbreak attempts (Scope criterion).
      - Terminology grounding: Comparing natural language explanations against glossary definitions while forgiving surface paraphrasing (Grounding criterion).
    - **Key Architectural Takeaway**:
      Never ask an LLM to evaluate what code can verify with a regular expression or assert statement. High-reliability AI evaluation pipelines should use a **hybrid two-stage architecture**: deterministic code filters as the first gate, followed by LLM-as-a-Judge with calibrated rubrics, backed by an "unsure" escape hatch for human-in-the-loop review.
