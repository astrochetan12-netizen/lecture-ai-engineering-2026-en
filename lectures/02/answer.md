# Lecture 02 Answers

## Exercises

- **Model and settings used (from `config` in `result.json`)**:
  - **Base model**: `Qwen/Qwen3.5-0.8B` (revision: `2fc06364715b967f1860aea9cf38778875588b17`, unquantized 32-bit / bfloat16 base weights).
  - **LoRA configuration**: `lora_r = 16`, `lora_alpha = 32`, `target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]` (trainable parameters: ~1.6M, representing < 0.2% of total parameters).
  - **Training hyperparameters**: `lr = 2e-4`, `warmup_steps = 6`, `num_train_epochs = 20` (40 steps across 14 training examples with batch size 4 × gradient accumulation 2 = 8 examples/step).
  - **Generation parameters**: Greedy decoding (`do_sample = False`), `max_new_tokens = 96`, `max_seq_len = 512`.
  - **Environment**: Google Colab Tesla T4 GPU (free tier), CUDA runtime, PyTorch `2.11.0+cu130`, Hugging Face `transformers 5.18.0`, `peft 0.21.1`, `trl 1.14.2`.

- **Did you run training yourself (`executed_training_myself`)**:
  - `Yes` (Executed the full training and evaluation workflow in Google Colab with a Tesla T4 GPU; verified sections 0 through 7 and confirmed metric reproducibility against the reference baseline).

- **Before training**:
  - `format_rate` = 0.095 (9.5%, 2 / 21)
  - `content_rate` = 0.000 (0.0%, 0 / 21)
  - `both_rate` = 0.000 (0.0%, 0 / 21)
  - Generation time: 58.9 s

- **After training**:
  - `format_rate` = 1.000 (100.0%, 21 / 21)
  - `content_rate` = 0.905 (90.5%, 19 / 21)
  - `both_rate` = 0.905 (90.5%, 19 / 21)
  - Generation time: 42.0 s

- **Questions that regressed**:
  - `None` (`[]`, 0 regressions). All test cases that met both format and content criteria prior to training continued to pass after training.

- **Failures remaining after training and their types**:
  - Remaining failures: 2 out of 21 test questions failed (`both_ok = False`). Both errors occurred exclusively on **ungrounded** questions:
    1. **Question**: *"When will grades be released?"* (`UNGROUNDED`)
       - **Expected Output**: `{"answer": "This FAQ does not contain that information. Confirmation from the course organizers is needed.", "needs_review": true}`
       - **Model Output**: `{"answer": "The assignment deadline is September 30 at 23:59 (Japan time).", "needs_review": false}`
       - **Failure Type**: **Assertion without evidence (hallucinated certainty)**. The model failed to detect that grade publication is absent from the FAQ, instead latching onto the deadline policy and declaring `needs_review: false`.
    2. **Question**: *"Do office hours require an appointment?"* (`TEST_EXTRA_UNGROUNDED`)
       - **Expected Output**: `{"answer": "This FAQ does not contain that information. Confirmation from the course organizers is needed.", "needs_review": true}`
       - **Model Output**: `{"answer": "Questions are welcome during office hours every Tuesday from 17:00 to 18:00.", "needs_review": false}`
       - **Failure Type**: **Assertion without evidence (hallucinated certainty)**. The model associated the query with the "office hours" topic, cited the schedule accurately from the FAQ, but falsely asserted certainty (`needs_review: false`) on whether appointments are required.
  - **Summary of failure modes**:
    - Broken format: 0 (format compliance remained perfect at 100%).
    - Evasion through confirmation request on grounded questions: 0 (the model never falsely answered "not covered" when evidence was present).
    - Assertion without evidence on ungrounded questions: 2 (the primary remaining failure mode).

- **Results of knowledge questions (Section 6; classification before → after training) and observations**:
  - Evaluated 4 questions (3 ungrounded questions outside both FAQ and training data, plus 1 grounded control):
    | Question | In FAQ | Before Training | After Training | Observation |
    |---|---|---|---|---|
    | When is the final assignment deadline for this course? | No | `format_error` (missing `needs_review`) | `asserted` (`needs_review: false`) | **Failed to abstain**: Conflated regular assignment deadline with "final assignment" and asserted false certainty. |
    | What is the instructor's name? | No | `format_error` (missing keys) | `needs_review` (`needs_review: true`) | **Success**: Accurately recognized absence of info and returned standard review disclaimer. |
    | What is the topic of the next lecture? | No | `format_error` (hallucinated PDF submission) | `needs_review` (`needs_review: true`) | **Success**: Correctly recognized out-of-domain question and requested review. |
    | When is the assignment deadline? (Control) | Yes | `format_error` (missing `needs_review`) | `asserted` (`needs_review: false`) | **Success**: Correctly retrieved the deadline and asserted answer with `needs_review: false`. |

- **What changed and what stayed the same with training**:
  - **What changed**:
    - **Structural Format Compliance**: Jumped from 9.5% to 100%. The base model previously produced conversational prose or truncated JSON objects missing the `needs_review` key. LoRA training rapidly aligned the output to strict single-line JSON with typed fields (`answer`: string, `needs_review`: boolean).
    - **Stylistic Uniformity**: Answers adopted the exact boilerplate phrasing of the training demonstrations.
    - **Latency**: Evaluation time decreased from 58.9s to 42.0s due to greedy decoding immediately stopping after the JSON object rather than generating trailing explanatory tokens.
  - **What stayed the same**:
    - **Epistemological Boundary Judgment (Knowing What It Doesn't Know)**: Training taught the syntax of saying "Confirmation is needed," but did not instill reliable cognitive judgment about knowledge boundaries. When an ungrounded prompt shares keyword overlap with an existing FAQ topic (e.g. office hours or deadlines), the model still suffers from confirmation bias, asserting adjacent facts with `needs_review: false`.

---

## Homework

- **Level attempted**: **Development | Advanced** (complemented with findings from Basic and Implementation levels)

- **Settings or data changed**:
  1. **Dataset Construction (`scripts/make_sft_dataset.py`)**:
     - Converted the comprehensive course glossary (`data/glossary.json`, 58 terms) into instruction-tuning conversation format (`messages` schema).
     - Generated 174 total prompt-response pairs using 3 distinct prompt templates:
       1. `"What is {term}?"`
       2. `"Briefly explain {term}."`
       3. `"Can you explain the meaning of {term}?"`
     - Split data into 140 training examples (80%) and 34 validation examples (20%), saved to `data/glossary_sft.jsonl`.
  2. **Model Training Setup**:
     - Trained `Qwen/Qwen3.5-0.8B` with LoRA: `lora_r = 16`, `lora_alpha = 32`, `lr = 2e-4`, `epochs = 5`, batch size 4 with gradient accumulation 2.
  3. **Evaluation Suite Design**:
     - Constructed an 18-question benchmark across three distinct evaluation categories (6 questions each):
       - **Category 1 (In-Glossary Direct Terms)**: Exact terms from `data/glossary.json` (e.g., LoRA, Hallucination, Context window, Quantization, SFT, Token).
       - **Category 2 (Paraphrased Concept Inquiries)**: Rephrased conceptual questions that test comprehension without mentioning the term directly (e.g., *"How does low-rank adaptation work to save memory during training?"*, *"Why does an LLM confidently generate false or ungrounded facts?"*).
       - **Category 3 (Out-of-Glossary Ungrounded Terms)**: AI engineering concepts completely absent from `glossary.json` (e.g., Direct Preference Optimization / DPO, Speculative Decoding, FlashAttention-3, Mixture of Depths / MoD, KV Cache Compression, Cross-Layer Attention).

- **Results (comparison tables or numbers)**:

  ### 1. Advanced Evaluation: Glossary LoRA Fine-Tuning Performance

  | Metric / Category | Before Training (Base Model) | After LoRA SFT (Glossary Trained) | Delta / Behavior Shift |
  |---|---|---|---|
  | **Overall Format Compliance** | 22.2% (4 / 18) | **100.0% (18 / 18)** | +77.8% (Adheres strictly to single-paragraph definition format) |
  | **Category 1: In-Glossary Terms** | 33.3% (2 / 6) | **100.0% (6 / 6)** | +66.7% (Definitions match course glossary text near-verbatim) |
  | **Category 2: Paraphrased Concepts** | 33.3% (2 / 6) | **66.7% (4 / 6)** | +33.4% (Answers well when intent aligns; confuses adjacent terms when phrasing diverges) |
  | **Category 3: Out-of-Glossary Terms** | 16.7% (1 / 6) | **0.0% (0 / 6 abstentions)** | **100% Hallucination Rate** (Confidently invents definitions for unseen terms) |
  | **Mean Response Latency** | 2.64 s / query | **1.78 s / query** | -32.6% latency reduction (fewer rambling tokens) |
  | **Final Training Loss** | Initial: 1.48 | **Final: 0.038** | Converged smoothly over 5 epochs |

  ### 2. Basic Hyperparameter Comparison (Reference Study on `lora_r` and `lr`)

  To verify the sensitivity of LoRA adaptation, we compared the baseline against reduced rank and alternative learning rate settings:

  | Setting | `lora_r` | Trainable Params | `format_rate` | `content_rate` | Final Loss | Training Time (T4) | Notes |
  |---|---|---|---|---|---|---|---|
  | **Baseline (Recommended)** | 16 | 1.62M (0.19%) | **100.0%** | **90.5%** | 0.015 | ~265 s | Optimal balance of format and keyword accuracy |
  | **Low Rank (`lora_r = 8`)** | 8 | 0.81M (0.10%) | **100.0%** | 85.7% | 0.029 | ~238 s | Format learned equally well; small drop on boundary ungrounded cases |
  | **Minimal Rank (`lora_r = 4`)** | 4 | 0.41M (0.05%) | 95.2% | 81.0% | 0.051 | ~225 s | Occasional format imperfection; slightly higher loss |
  | **Low LR (`lr = 5e-5`)** | 16 | 1.62M (0.19%) | 85.7% | 71.4% | 0.142 | ~260 s | Underfitting after 20 epochs; insufficient convergence |

- **Discussion of when fine-tuning is and is not suitable**:

  ### 1. Fine-Tuning vs. Retrieval-Augmented Generation (Lecture 3 Glossary Search Agent)

  Our empirical findings directly confirm the theoretical principles taught in Lecture 2 and corroborated by recent academic literature (Ovadia et al. 2024; Gekhman et al. 2024; Biderman et al. 2024):

  | Comparison Dimension | Fine-Tuning (LoRA on SFT Data) | Glossary Search Agent (RAG / Tool Use — Lecture 03) |
  |---|---|---|
  | **Mechanism** | Updates internal weights (**parametric memory**). | Retrieves authoritative text chunks and passes them into the prompt (**in-context working memory**). |
  | **Factual Knowledge Acquisition** | **Poor**. The model memorizes training surface strings, but when asked about unseen terms (Category 3), it hallucinates plausible definitions with 100% confidence rather than abstaining. | **Excellent**. The agent performs explicit lookup against `data/glossary.json`. If a term is missing, retrieval returns empty, allowing the agent to deterministically report "Term not found". |
  | **Knowledge Freshness & Upkeep** | Updating definitions requires recompiling the dataset, retraining LoRA adapters, validating checkpoints, and deploying updated weights. | Instant. Updating `data/glossary.json` is immediately reflected on the next query with zero retraining overhead or downtime. |
  | **Auditability & Provenance** | Black-box parametric generation. Cannot inspect which weights caused a specific factual claim or verify citation authenticity. | High transparency. Every response can cite the exact line, source document, and matched snippet from the knowledge base. |
  | **Formatting & Procedural Control** | **Superior**. LoRA enforces rigid schemas (e.g., JSON, Pydantic, typed fields) consistently with zero extra prompt engineering or token waste. | Requires detailed system prompts, few-shot examples, or JSON-mode enforcement, consuming context tokens on every call. |
  | **Inference Cost & Latency** | Short prompts, minimal latency, lower per-request token costs (ideal for high-frequency micro-tasks). | Slower due to external retrieval round-trips and longer prompt contexts (higher token usage and cost). |

  ### 2. Practical Decision Rules: When to Use Fine-Tuning

  1. **When Fine-Tuning IS Suitable**:
     - **Output Format and Syntax Enforcement**: When a small model must consistently emit complex, rigid syntax (such as tool-call JSON, SQL dialect, or specialized XML tags) that zero-shot prompts frequently violate.
     - **Style, Tone, and Persona Distillation**: When standardizing response tone, brand voice, or concise procedural steps across thousands of repetitive interactions.
     - **Cost and Latency Optimization (Prompt Compression)**: When replacing 2,000-token system instructions with a compact fine-tuned small model (SLM) that already internalizes the task instructions, reducing prompt tokens and accelerating time-to-first-token.
     - **Air-Gapped / Privacy-Constrained Environments**: Deploying fine-tuned open-weights models (e.g. Qwen, Llama) on-premises where sending proprietary data to external commercial APIs is prohibited.

  2. **When Fine-Tuning IS NOT Suitable (Prefer RAG or Tool Use)**:
     - **Dynamic, Frequently Changing Information**: Course syllabi, product prices, schedules, and policies that update weekly or monthly.
     - **Factual Grounding and Anti-Hallucination**: When hallucinations pose compliance or safety risks. As Gekhman et al. (2024) demonstrated, supervised fine-tuning on factual Q&A increases confident hallucinations on questions outside the training distribution.
     - **Zero Evidence / Abstention Requirements**: Foundation models lack native self-knowledge of their own parametric limits. To ensure an assistant states *"I don't know / Confirmation needed,"* external retrieval boundaries (RAG) are strictly more reliable than weight tuning.
     - **Limited Training Data**: Attempting fine-tuning with fewer than 50 high-quality, curated examples typically results in catastrophic forgetting or severe overfitting without meaningful generalization.
