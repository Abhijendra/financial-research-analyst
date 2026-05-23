# Spec: Structured Output Extraction

## Overview
Implement `src/analyst/extraction/structured.py` — the "modern easy path" for
turning unstructured financial text into validated Pydantic objects using
`ChatModel.with_structured_output(Schema)`. This is the first of the two
extraction paths mandated by `CLAUDE.md` §6; the under-the-hood counterpart
(`PydanticOutputParser` + `OutputFixingParser`) lives in
`extraction/manual_parse.py` and will be built next. This file covers
per-schema extractors for `CompanyFinancials`, `RiskFactor` (as a list
wrapper), and `SentimentScore`, a `RunnableParallel` composition that runs all
three concurrently against a single chunk, and a small post-step that attaches
`Provenance` (ingestion metadata) to the LLM output without asking the model
to invent it.

## Depends on
- **Schemas** (done): `CompanyFinancials`, `RiskFactor`, `SentimentScore`,
  `Provenance` in `src/analyst/schemas/`.
- **Configurable model layer** (NOT done): `src/analyst/models.py` is empty.
  Must be implemented first — extractors take a model as a parameter and the
  factory must use `init_chat_model(...).configurable_fields(...)` per
  `CLAUDE.md` §6.
- **Config loading** (NOT done): `src/analyst/config.py` is empty. Needed so
  `models.py` can read API keys / default model from `.env`.
- Ingestion module (done) — produces the `document_text` + metadata that this
  module consumes.

## Implementation steps
Build incrementally; each step should leave the repo runnable.

1. **Write `src/analyst/config.py`** — a tiny typed `Settings` class
   (Pydantic `BaseSettings` or plain Pydantic + `python-dotenv`) that loads
   `OPENAI_API_KEY`, `DEFAULT_MODEL`, `DEFAULT_TEMPERATURE`, and
   `LANGSMITH_*` from `.env`. No secrets in source.

2. **Write `src/analyst/models.py`** — single factory
   `get_chat_model(model: str | None = None, temperature: float = 0.0)` that
   returns `init_chat_model(...)` with `.configurable_fields(model=...,
   temperature=...)`. Default temperature 0 (extraction is not creative).

3. **Add a list wrapper for risks** — in `src/analyst/schemas/risk.py` add
   `class RiskFactorList(BaseModel): risks: list[RiskFactor]`.
   Reason: `with_structured_output` can return only one RiskFactor; but
   practically there can be many risks.

4. **Write the prompt(s)** — in `src/analyst/prompts/` (create the folder),
   define `extraction_prompts.py` with one `ChatPromptTemplate` per schema.
   System message: "You are a financial data extractor. Use only facts present
   in the supplied text. If a required field is not in the text, the
   extraction must fail rather than be invented." Human message contains
   `{document_text}`.

5. **Write `src/analyst/extraction/structured.py`** with four public factories:
   - `build_financials_extractor(model: BaseChatModel | None = None) -> Runnable`
   - `build_risks_extractor(model: BaseChatModel | None = None) -> Runnable`
   - `build_sentiment_extractor(model: BaseChatModel | None = None) -> Runnable`
   - `build_full_extractor(model: BaseChatModel | None = None) -> Runnable`

   Each builds: `prompt | model.with_structured_output(Schema)`.
   `build_full_extractor` returns a `RunnableParallel` with keys
   `financials`, `risks`, `sentiment` so a single `.invoke({"document_text":
   ...})` runs all three concurrently.

6. **Provenance attachment** — add a helper
   `attach_provenance(extraction: dict, provenance: Provenance) -> dict` (or a
   `RunnableLambda`) that wraps the parallel output. Do NOT include
   `Provenance` in any LLM schema — it comes from ingestion metadata, not the
   model. Document this clearly in the docstring.

7. **Docstrings** — every public function gets a docstring stating purpose,
   the LangChain concept it demonstrates, and the tradeoff vs the manual path.

8. **Tests** — `tests/extraction/test_structured.py`:
   - Type-only test: each factory returns a `Runnable`.
   - Schema-binding test: monkeypatch a fake chat model whose
     `with_structured_output` records the schema it was called with; assert
     the right schema was passed.
   - Provenance test: `attach_provenance` does not mutate the LLM output and
     produces the expected combined dict.
   Do not assert exact LLM wording (`CLAUDE.md` §8).

9. **Smoke run** — a `__main__` block (or a tiny script in `scripts/`) that
   loads one sample document from `data/`, runs `build_full_extractor`, and
   prints the parsed objects. Manual sanity check, not a unit test.

10. **Update `DECISIONS.md`** — one paragraph each for:
    - `with_structured_output` over `PydanticOutputParser` (native
      tool-calling → no string parsing).
    - Temperature 0 for extraction.
    - List wrapper schema for multi-item extraction.
    - `RunnableParallel` over sequential calls (latency, independence).
    - Provenance attached post-hoc, not asked of the LLM (hallucination risk).

## Files to change
- `src/analyst/config.py` — fill in `Settings`.
- `src/analyst/models.py` — fill in `get_chat_model`.
- `src/analyst/schemas/risk.py` — add `RiskFactorList`.
- `src/analyst/extraction/structured.py` — implement the module.
- `DECISIONS.md` — append the five decision entries listed above.
- `.env.example` — ensure it lists `OPENAI_API_KEY`, `DEFAULT_MODEL`,
  `DEFAULT_TEMPERATURE`, `LANGSMITH_*`.

## Files to create
- `src/analyst/prompts/__init__.py`
- `src/analyst/prompts/extraction_prompts.py`
- `tests/extraction/__init__.py`
- `tests/extraction/test_structured.py`
- `scripts/smoke_extract.py` (optional, for the manual smoke run)

## New dependencies
No new dependencies — `langchain`, `langchain-core`, `langchain-openai`, and
`pydantic` are already pinned in `pyproject.toml`. If `python-dotenv` or
`pydantic-settings` is not yet present and is chosen for `config.py`, pin it
and note why in `DECISIONS.md`.

## Definition of done
- [ ] `python -c "from analyst.models import get_chat_model; print(get_chat_model())"` prints a configured chat model without error.
- [ ] `python -c "from analyst.extraction.structured import build_full_extractor; print(build_full_extractor())"` returns a `RunnableParallel`.
- [ ] `pytest tests/extraction/test_structured.py` passes.
- [ ] `python scripts/smoke_extract.py data/<sample>.pdf` prints a populated `CompanyFinancials`, a non-empty `RiskFactorList`, and a `SentimentScore` whose `label` matches the sign of `score`.
- [ ] The smoke run output, when fed through `attach_provenance`, includes the source path, document type, and (where known) the page — none of which were generated by the LLM.
- [ ] `ruff check src/analyst/extraction/structured.py` and `ruff format --check` are clean.
- [ ] `DECISIONS.md` has the five new entries, each one paragraph, each defensible in an interview.
- [ ] No API keys appear in any tracked file (`git grep -E "sk-[A-Za-z0-9]"` returns nothing).
