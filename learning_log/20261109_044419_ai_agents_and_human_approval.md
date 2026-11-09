# Learning Log: AI Agents and human approval

- **Date**: 2026-11-09 04:44:19 UTC
- **Topic**: AI Agents and human approval

## What I Learned
Learned about the core architecture of AI agents (model + loop + tools), the role of tool descriptions, the impact of the agent loop on cost and latency, and the importance of guardrails and human-in-the-loop for safe execution.

## Key Points
- An AI agent's basic structure is model + loop + tools.
- Tools are requested by the LLM based on names, descriptions, and argument types, and executed by the program.
- Agent loops incur costs in terms of multiple LLM calls, latency, charges, and rate limits.
- Guardrails and Human-in-the-loop are essential for irreversible operations like file writes.
