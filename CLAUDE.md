# CLAUDE.md

Guidance for Claude Code (and any AI assistant) working in this repository.
This file is the source of truth for *how* we build. Read it fully before
generating or editing code.

---

## 1. Project overview

**Name:** `research-analyst-agent`

**What it is:** An automated financial research analyst. It ingests messy
real-world financial documents (earnings reports, regulatory filings, news
articles), extracts structured data, reasons over that data with tools, and
produces analyst-grade memos with citations.

**Why it exists:** This is a capstone learning project to build deep, durable
mastery of LangChain across its most widely used primitives — ChatModels,
ChatPromptTemplate, structured outputs, output parsers, LCEL chains, Runnables,
ReAct agents, tools, memory, evaluation, and tracing. The goal is not just a
working demo but a system whose every design decision can be defended in a
technical interview.

**Audience / author:** An AI engineer (~1.5 yrs experience) working in Indian
fintech (UPI infrastructure). Domain intuition for financial and transaction
data is assumed; LangChain depth is the thing being built.

**Success criteria:** After completion, the author should be able to explain,
from first principles, what each LangChain abstraction does, when to reach for
it, and when NOT to (e.g. chain vs agent).

---

## 2. Golden rules for the assistant

1. **Teach, don't just solve.** This is a learning project. When you implement
   something non-obvious, add a short comment or docstring explaining *why* this
   approach over the alternative. Favor clarity over cleverness.
2. **Two paths when it teaches.** Where a concept has a "modern easy path" and a
   "manual under-the-hood path" (e.g. `with_structured_output` vs
   `PydanticOutputParser`), implement BOTH where the file's purpose is learning,
   and note the tradeoff. Don't silently pick the shortcut.
3. **Verify the API surface.** LangChain moves fast and reorganizes packages.
   Do NOT trust memory or old tutorials for imports/signatures. Check the
   pinned versions in `pyproject.toml` and current docs before using an API.
   If unsure whether something is deprecated, say so.
4. **Prefer LCEL.** Compose with the pipe syntax and the Runnable interface.
   Do not use the legacy `LLMChain` / `SequentialChain` classes except in ONE
   clearly-labeled file that exists to contrast old vs new.
5. **Update `DECISIONS.md`.** Every meaningful architectural choice ("X over Y
   because Z") gets a one-paragraph entry. This is the author's interview prep;
   treat it as a first-class deliverable, not an afterthought.
6. **Never hardcode secrets.** API keys come from environment variables only.
   Never write a key into source, tests, or commits.
7. **Ask before scope creep.** If a request implies a big new subsystem (e.g. a
   full RAG store, a UI), flag it and confirm before building.
8. **Type everything.** All functions and chain boundaries are type-annotated.
   Structured data is always a Pydantic model, never a loose dict.

---

## 3. Tech stack & environment

- **Language:** Python 3.11+
- **Package/dependency manager:** `uv`
- **Core libraries:**
  - `langchain`, `langchain-core`, `langchain-community`
  - `langchain-openai`
  - `langchain-text-splitters`
  - `langgraph` (for the graph-based agent in Week 3)
  - `langsmith` (tracing + eval in Week 4)
  - `pydantic` v2
  - `fastapi` + `uvicorn` (serving)
  - `pytest` (tests)
- **Pin versions.** All versions are pinned in `pyproject.toml`. When adding a
  dependency, pin it and note why it's needed.
- **Config:** All keys and other sensitive data keep in `.env` file.

---

## 4. Repository structure

```
research-analyst-agent/
├── CLAUDE.md                  # this file
├── DECISIONS.md               # running log of architectural choices
├── README.md                  # public-facing: what/why/how-to-run
├── pyproject.toml             # pinned deps
├── .env.example               # documents required env vars (no real values)
├── src/
│   └── analyst/
│       ├── config.py          # typed settings, env loading
│       ├── models.py          # configurable ChatModel layer (init_chat_model)
│       ├── schemas/           # Pydantic models (the data contracts)
│       │   ├── financials.py  # CompanyFinancials, etc.
│       │   ├── risk.py        # RiskFactor
│       │   └── sentiment.py   # SentimentScore
│       ├── ingestion/         # Week 1 — loaders, splitters, metadata
│       │   ├── loaders.py
│       │   └── chunking.py
│       ├── extraction/        # Week 1/2 — structured-output chains
│       │   ├── structured.py  # with_structured_output path
│       │   └── manual_parse.py# PydanticOutputParser path (under-the-hood)
│       ├── prompts/           # ChatPromptTemplates, few-shot examples
│       ├── chains/            # Week 2 — LCEL composition, routing
│       │   ├── classify.py    # document-type classifier
│       │   └── router.py      # RunnableBranch routing
│       ├── tools/             # Week 3 — @tool definitions
│       │   ├── search.py
│       │   ├── calculator.py
│       │   └── retriever.py   # minimal RAG retriever tool
│       ├── agents/            # Week 3 — ReAct (classic) + LangGraph
│       │   ├── react_classic.py
│       │   └── react_graph.py
│       ├── memory/            # conversational memory for follow-ups
│       ├── memo/              # Week 4 — cited memo writer
│       └── serving/           # Week 4 — FastAPI app
├── eval/                      # Week 4 — datasets + evaluators (LangSmith)
│   ├── datasets/
│   └── evaluators.py
├── tests/
└── data/                      # sample documents (git-ignored if large)
```

Keep modules small and single-purpose.

---

## 5. Conventions & code style

- **Formatting:** `ruff format` (or `black`) + `ruff` for linting. Run before
  considering work done.
- **Imports:** Import from the *current* canonical locations. Splitters live in
  `langchain_text_splitters`; community loaders in
  `langchain_community.document_loaders`; core abstractions in `langchain_core`.
  Provider models come from their own packages (`langchain_openai`, etc.).
- **Naming:** Chains are named for what they produce (`extraction_chain`,
  `classify_chain`), not how they're built. Pydantic schemas are nouns
  (`CompanyFinancials`). Tools are verbs (`search_web`, `calculate_ratio`).
- **Docstrings:** Every public function gets a docstring stating purpose, the
  LangChain concept it demonstrates, and any non-obvious tradeoff.
- **No bare dicts for structured data.** If the LLM returns structure, it returns
  a Pydantic model. Validate at the boundary.
- **Async where it matters.** Expose `.ainvoke`/`.astream` paths for anything
  that will be served via FastAPI; don't block the event loop.

---

## 6. Architectural decisions already made (respect these)

- **Configurable model layer.** Models are constructed via `init_chat_model`
  with `.configurable_fields()` so provider/temperature can change at runtime.
  Never hardcode a single model deep inside a chain.
- **Structured output is built two ways on purpose.** `extraction/structured.py`
  uses `.with_structured_output()`; `extraction/manual_parse.py` uses
  `PydanticOutputParser` + format instructions + `OutputFixingParser`. The
  second exists to demonstrate what the first hides. Keep both.
- **LCEL everywhere.** Composition uses `prompt | model | parser`, with
  `RunnableBranch` for routing, `RunnableParallel` for concurrent extraction,
  `RunnablePassthrough` for threading context, `RunnableLambda` for reshaping,
  and `.with_fallbacks()` for resilience.
- **The ReAct agent is built twice.** `react_classic.py` uses
  `create_react_agent` + `AgentExecutor` to expose the raw
  Thought→Action→Observation loop. `react_graph.py` rebuilds the same behavior
  in LangGraph. The point is the *contrast* — document it in `DECISIONS.md`.
- **Deliberate "chain not agent" case.** At least one workflow is implemented as
  a plain routed chain specifically because the control flow is deterministic.
  Knowing when an agent is overkill is a core lesson; do not "upgrade" this to
  an agent.
- **RAG is intentionally minimal.** A small retriever exists only as an agent
  tool.
- **Provenance survives the pipeline.** Metadata (source, page, document_type,
  ticker, date) is enriched at ingestion and must propagate through chunking and
  extraction so the memo writer can produce real citations.

---

## 7. Domain notes (financial / fintech)

- Documents are financial: earnings reports, filings, market news. Expect
  tables, footnotes, and numbers that simpler PDF loaders mangle — prefer a
  layout-aware loader (Unstructured) for table-heavy filings.
- Structured schemas should reflect real financial semantics: currency and
  units must be explicit fields (never assume USD), dates are typed, and
  numeric fields use validators to catch nonsense.
- The author works on UPI infrastructure — when illustrating concepts, fintech/
  payments analogies are welcome and land well.
- **This is a learning project on public/sample data.** Do not wire it to any
  real production, proprietary, or regulated data source. Use only public
  filings and sample documents in `data/`.

---

## 8. Testing & evaluation

- **Unit tests** (`pytest`) for deterministic logic: schema validation, metadata
  propagation, tool input/output, parsers against fixed strings.
- **LLM behavior is evaluated, not unit-tested.** Use the LangSmith eval suite in
  `eval/`: a dataset of documents with known-correct extractions, exact-match
  evaluators for structured fields, and an LLM-as-judge evaluator for memo
  quality. Changing a prompt means re-running eval and recording the delta.
- **Tracing on by default.** LangSmith tracing should be enabled for runs so
  every chain/agent step is observable. Cost and token usage are tracked via
  callbacks.
- Don't write flaky tests that assert exact LLM wording. Assert structure,
  types, presence of citations, and value ranges instead.

---

## 9. Build sequence (don't jump ahead without reason)

1. **Week 1 — Foundations:** configurable models, Pydantic schemas, ingestion
   (loaders/splitters/metadata), structured extraction (both paths),
   `OutputFixingParser`.
2. **Week 2 — Composition:** LCEL chains, classifier, `RunnableBranch` routing,
   `RunnableParallel`, fallbacks, batch/stream/async surfaces.
3. **Week 3 — Agency:** `@tool` definitions, classic ReAct agent, LangGraph
   rebuild, the deliberate chain-not-agent case, conversational memory.
4. **Week 4 — Production:** LangSmith tracing + eval suite, retries/backoff,
   caching, FastAPI serving, README + DECISIONS writeup.

Each phase should reach a runnable, demonstrable state before the next begins.
Where a later phase reveals a flaw in an earlier one, fix it and log why — that
"the design broke, so I reached for X" narrative is the whole point.

---

## 10. What to do when uncertain

- If an API might be deprecated or moved: check `pyproject.toml` versions and
  current docs; state your uncertainty rather than guessing.
- If a request would expand scope materially: pause and confirm.
- If two approaches are both valid: implement the one that teaches more, and
  note the alternative in a comment and in `DECISIONS.md`.
- If something can't be done safely or correctly: say so plainly instead of
  producing plausible-looking but wrong code.