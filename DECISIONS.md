## Schema design

1. **Every field gets a description.** With `.with_structured_output()`, descriptions are sent to the model as part of the prompt. A schema without descriptions is a half-written prompt.
2. **Optional vs required matters.** Required fields that aren't in the document → the model invents values. Default to `Optional` for anything not guaranteed to appear.
3. **Constrain numerics with `ge`/`le`.** Use inclusive bounds unless there's a real reason to exclude endpoints.
4. **Validators by scope.** Cross-field invariants → `model_validator`. Single-field → `field_validator` or `Field(...)`.
5. **Provenance lives on the data.** `schemas/provenance.py` carries `source`, `page`, `document_type`, `ticker`, `date`. Every top-level extraction model gets a `provenance` field. This is what makes Week 4's memo writer able to cite.
6. **`Literal` > `str` for closed sets.** Cheapest validation in Pydantic, and it doubles as documentation for the LLM.

### Provenance specifics
- `document_type` is a `Literal`, not free text. Week 2's classifier writes it; Week 2's router (`RunnableBranch`) reads it. A closed set keeps the router exhaustive.
- `page` is `Optional` — not every source has pages (news, transcripts).
- `ticker` lives on `Provenance`, not on `CompanyFinancials`. Risks and sentiment also need company attribution; putting it on provenance avoids duplicating the field across every schema.
- `published_date` is separate from `CompanyFinancials.reporting_date`. A 10-K filed in March 2025 reports on fiscal year 2024 — conflating them silently corrupts time-series analysis.

## models.py
1. Why `ChatOpenAI` instead of `OpenAI`?

## Structured extraction

1. **`with_structured_output` over `PydanticOutputParser`.** Uses the provider's native tool-calling to bind the schema at the API level, so the reply is a validated Pydantic object — no string parsing, no format-instruction prompt bloat. The manual path is kept in `extraction/manual_parse.py` only to show what this hides.
2. **Temperature 0 for extraction.** Extraction is not creative. Determinism > variety; sampling noise only adds drift between runs on the same document.
3. **List wrapper schema for multi-item extraction.** `with_structured_output` accepts one root schema, but a document can contain many risks. `RiskFactorList` wraps `list[RiskFactor]` so the model can return all of them in a single call.
4. **`RunnableParallel` over sequential calls.** Financials, risks, and sentiment are independent extractions over the same chunk. Fanning out gives max-of-three latency instead of sum-of-three, and the three branches share one configurable model instance.
5. **Provenance attached post-hoc, not asked of the LLM.** Source path, page, and document type come from ingestion metadata — facts we already know. Asking the model for them invites hallucinated citations, which would silently corrupt the memo writer's downstream output.


## Manual Parsing 

- `OutputFixingParser` over manual `try/except` + retry (one LLM hop with a known repair prompt vs. hand-rolled control flow).
- `prompt.partial(format_instructions=...)` over passing them at invoke time (call signature stays identical to the structured path → the two are drop-in interchangeable for callers).
- When you would actually pick this path in production (models without tool-calling, providers whose structured-output API is unreliable, or when you need to log/inspect the raw text reply).