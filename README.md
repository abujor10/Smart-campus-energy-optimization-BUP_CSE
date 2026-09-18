# Energy Optimizer API

A production-ready FastAPI service that optimizes a 24-hour battery and grid schedule to minimize energy costs using Linear Programming (PuLP) and LLM-powered (Gemini) intelligent directive parsing.

## Pipeline Architecture
1. **Request Intake:** FastAPI receives a 24-hour scenario including energy demands, tariffs, and solar inputs.
2. **LLM Interpreter:** `google-generativeai` converts human-written operator notes into JSON directives.
3. **Guardrails:** Deterministic Python validation ensures LLM output is structurally and logically safe.
4. **Optimizer:** PuLP (Linear Programming solver) models battery actions to strictly minimize cost, strictly satisfying physical constraints and end-of-day neutrality.

## Setup Instructions

### 1. Get a Free Gemini API Key
Go to [Google AI Studio](https://aistudio.google.com/) and create a free API key.

### 2. Environment Setup
Create a file named `.env` in the root folder and add your key:
```bash
GEMINI_API_KEY=your_actual_key_here