# Spec: LCEL Composition, Classifier and Routing

## Overview
Week 2 of the roadmap is **composition**: stop building one-shot chains and
start wiring them together with LCEL. We will (1) build a small `classify`
chain that labels a document as one of the `DocumentType` values, (2) use
`RunnableBranch` to route each document to the right extractor based on that
label, (3) keep `RunnableParallel` for the fan-out we already have inside
`structured.py`, (4) add `.with_fallbacks(...)` so a flaky primary model
degrades gracefully to a cheaper/secondary one, and (5) expose
batch / stream / async surfaces on the final pipeline so the same object can
serve one doc, many docs, or a FastAPI request without rewrites. The point of
this week is to *feel* the difference between a chain (deterministic control
flow you can draw on a whiteboard) and an agent (the model decides) — every
routing decision here is rule-based on purpose, so Week 3's agent contrast
lands hard.

## Depends on
- Week 1 complete: `config.py`, `models.py`, ingestion, schemas, and both
  extraction paths (`extraction/structured.py`, `extraction/manual_parse.py`).
- `Provenance` and `DocumentType` in `schemas/provenance.py` — the classifier
  emits a `DocumentType` and the router keys off it.
- `get_chat_model()` factory — used everywhere a model is needed, never
  hardcoded.

## Implementation steps
Build incrementally. Each step should leave the repo importable and tested
before moving on.

1. **Classifier schema** — in `src/analyst/schemas/` add `classification.py`
   with a small Pydantic model:
   ```
   class DocumentClassification(BaseModel):
       document_type: DocumentType
       confidence: float = Field(ge=0, le=1)
       reason: str
   ```
   Reason: we ask the LLM for the label *and* a short rationale + confidence so
   the router can fall back to `"other"` on low confidence instead of trusting
   a coin-flip answer. Confidence is also useful in eval later.

2. **Classifier prompt** — `src/analyst/prompts/classify_prompts.py` with one
   `ChatPromptTemplate`. System message lists the allowed labels (pull from
   `DocumentType` so the prompt cannot drift from the schema) and instructs
   the model to choose exactly one. Human message contains `{document_text}`
   truncated to the first ~2k chars — classification doesn't need the whole
   filing and we save tokens.

3. **`src/analyst/chains/classify.py`** — implement
   `build_classify_chain(model=None) -> Runnable`:
   ```
   prompt | model.with_structured_output(DocumentClassification)
   ```
   Pure LCEL, structured output, no string parsing. Add a thin
   `RunnableLambda` post-step that downgrades `document_type` to `"other"`
   when `confidence < 0.5`. Reason: we'd rather route a doubtful doc through
   a generic path than to a specialized one that assumes structure that isn't
   there.

4. **Per-type extraction chains** — under `src/analyst/chains/` add
   `extractors.py` (or extend `structured.py`) with small wrappers:
   - `earnings_chain` → full extractor (financials + risks + sentiment) — the
     existing `build_full_extractor`.
   - `filing_chain` → financials + risks only; sentiment is meaningless on a
     10-K.
   - `news_chain` → sentiment + risks only; financials are usually absent.
   - `default_chain` → sentiment only, as a safe minimum.
   Each is just an LCEL composition of pieces we already have — no new model
   calls invented. Reason: this is *why* `RunnableParallel` was built as
   separate factories in Week 1; we get to recompose them cheaply now.

5. **`src/analyst/chains/router.py`** — implement `build_router_chain(model=None)`:
   - Step A: classify the document.
   - Step B: feed the original input + the classification into a
     `RunnableBranch` keyed on `document_type`.
   ```
   RunnableBranch(
       (lambda x: x["classification"].document_type == "earnings_report", earnings_chain),
       (lambda x: x["classification"].document_type in {"annual_filing", "quarterly_filing"}, filing_chain),
       (lambda x: x["classification"].document_type in {"news_article", "press_release"}, news_chain),
       default_chain,  # fallback branch
   )
   ```
   Compose the full pipeline with `RunnablePassthrough.assign(classification=classify_chain)`
   so both the original `document_text` and the classification flow into the
   branch. Reason: `RunnableBranch` is the *deterministic* routing primitive —
   use it where the rules are clear so we don't pay an agent's loop tax for a
   `switch` statement.

6. **Fallbacks** — wrap the primary model with
   `.with_fallbacks([secondary_model])` inside `get_chat_model` (or in a new
   `get_resilient_model()` helper to keep the simple factory simple). The
   secondary should be a cheaper model (e.g. a smaller Haiku/GPT-mini) read
   from `config.py` (`FALLBACK_MODEL`). Reason: provider outages and
   rate-limits are the #1 cause of demo failures; one line of LCEL turns that
   into a soft degrade.

7. **Batch / stream / async surfaces** — no new code needed for `.invoke`,
   `.batch`, `.stream`, `.ainvoke`, `.abatch`, `.astream` — they come free
   from the Runnable interface. But add a small `scripts/demo_router.py` that
   exercises all of: `.invoke(one_doc)`, `.batch([many_docs])`, and
   `async for chunk in chain.astream(one_doc)`. Reason: this is the lesson
   itself — LCEL gives you these for free if you compose with Runnables and
   don't reach for ad-hoc Python glue.

8. **Tests** — `tests/chains/`:
   - `test_classify.py`: monkeypatch a fake chat model that returns a fixed
     `DocumentClassification`; assert (a) chain returns the expected type,
     (b) the `confidence < 0.5` post-step downgrades to `"other"`.
   - `test_router.py`: with a fake classifier that returns each `DocumentType`
     in turn, assert the router invokes the matching branch (use spy
     `RunnableLambda`s as branches so we don't call a real model).
   - `test_fallbacks.py`: build a chain whose primary model always raises;
     assert the fallback is called and its result is returned.
   Do not assert exact LLM wording.

9. **`DECISIONS.md`** — one paragraph each for:
   - `RunnableBranch` over an `if/else` in Python (keeps everything inside
     the Runnable graph: tracing, batch, async all keep working).
   - Classifier emits `confidence` + a low-confidence downgrade (cheap guard
     against silent mis-routing).
   - Truncating input for classification (cost; classification signal is in
     the header).
   - `with_fallbacks` over manual try/except (one-line resilience that the
     tracer can see).
   - Chain-not-agent for routing (this is the "deliberate chain" case
     promised in `CLAUDE.md` §6 — call it out so Week 3's agent has something
     to be contrasted *with*).

## Files to change
- `src/analyst/chains/classify.py` — currently empty, implement.
- `src/analyst/chains/router.py` — currently empty, implement.
- `src/analyst/chains/__init__.py` — export the public builders.
- `src/analyst/config.py` — add `FALLBACK_MODEL` (and temperature if needed).
- `src/analyst/models.py` — add `get_resilient_model()` helper (or extend
  `get_chat_model` with a `with_fallbacks=True` flag — pick one and document
  why in `DECISIONS.md`).
- `DECISIONS.md` — append the five entries above.
- `.env.example` — list `FALLBACK_MODEL`.

## Files to create
- `src/analyst/schemas/classification.py`
- `src/analyst/prompts/classify_prompts.py`
- `src/analyst/chains/extractors.py` (per-document-type LCEL wrappers)
- `tests/chains/__init__.py`
- `tests/chains/test_classify.py`
- `tests/chains/test_router.py`
- `tests/chains/test_fallbacks.py`
- `scripts/demo_router.py` (manual demo of invoke/batch/stream/async)

## New dependencies
No new dependencies. Everything needed (`langchain-core` Runnables,
`RunnableBranch`, `RunnableParallel`, `RunnablePassthrough`, `RunnableLambda`,
`with_fallbacks`) ships in the already-pinned `langchain-core`.

## Definition of done
- [ ] `python -c "from analyst.chains.classify import build_classify_chain; print(build_classify_chain())"` prints a `Runnable` without error.
- [ ] `python -c "from analyst.chains.router import build_router_chain; print(build_router_chain())"` prints a `Runnable`.
- [ ] `pytest tests/chains/` passes (classify, router, fallbacks).
- [ ] `python scripts/demo_router.py` runs against one sample doc from `data/` and prints (a) the classification + confidence, (b) the chosen branch's output, (c) one streamed run, and (d) a batched run over ≥2 docs — all without code changes between modes.
- [ ] Killing network / using an invalid primary model still produces output via the fallback (verifiable by setting `DEFAULT_MODEL` to a nonexistent name in `.env` and re-running the demo).
- [ ] Low-confidence classifier outputs (forced via the fake model in tests) route to `default_chain`, not to a typed branch.
- [ ] `ruff check src/analyst/chains/ src/analyst/schemas/classification.py` and `ruff format --check` are clean.
- [ ] `DECISIONS.md` has the five new entries, each one paragraph, each defensible in an interview.
- [ ] No new secrets in tracked files (`git grep -E "sk-[A-Za-z0-9]"` returns nothing).
