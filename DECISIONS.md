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

## LCEL Composition & Routing (Week 2)

1. **`RunnableBranch` over a Python `if/else`.** Routing could trivially be a few `if` statements in a plain function, but that drops the work *out* of the Runnable graph. Keeping the switch inside `RunnableBranch` means the routing step keeps everything LCEL gives for free: it streams, it batches, it runs async, and — most importantly — LangSmith traces the branch decision as a node you can inspect. A hand-rolled `if` is invisible to the tracer and forces you to re-implement `.batch`/`.astream` glue by hand. The rule of thumb: when the control flow is deterministic *and* lives on the data path, encode it as a Runnable, not as host-language branching.

2. **The classifier emits `confidence` and we downgrade low-confidence labels to `"other"`.** The model is asked for a label, a short rationale, and a `confidence` in `[0,1]`. A `RunnableLambda` post-step rewrites `document_type` to `"other"` whenever `confidence < 0.5`. The cost is one extra float and a three-line lambda; the payoff is a cheap guard against *silent* mis-routing. A doubtful document routed to a specialized extractor assumes structure that may not exist (e.g. running the financials extractor on a press release) and fails quietly with garbage. Routing a doubtful doc through the generic `default_chain` instead is the safe default — degrade to less extraction, never to wrong extraction. The confidence field also gives Week 4's eval suite something to threshold on.

3. **Classification reads only the first ~2k characters, not the whole document.** Document type is a header-level signal — "FORM 10-K", "Q3 2024 Earnings Call", a press-release dateline — and it sits at the top of the document. Feeding an entire filing to the classifier would burn tokens (and latency) on text that carries no additional classification signal. Truncating the input is a pure cost win with no measurable accuracy loss for this task. (Note the contrast: the *extraction* chains downstream still see the full chunked document — truncation is correct for classification specifically *because* the signal is front-loaded, not a blanket policy.)

4. **`.with_fallbacks([secondary])` over a manual `try/except`.** Provider outages and rate-limits are the single most common cause of live-demo failures. The LCEL way is one line: wrap the primary model so that any exception transparently retries on a cheaper secondary model read from `FALLBACK_MODEL`. A hand-written `try/except` around the call would work, but it lives outside the Runnable graph (invisible to the tracer), has to be repeated at every call site, and tends to grow ad-hoc retry/backoff logic. `with_fallbacks` keeps the resilience *in* the chain where the tracer can see which model actually served each request, and composes identically with `.batch`/`.astream`.

5. **Routing is a chain, deliberately — not an agent.** This is the explicit "chain not agent" case promised in `CLAUDE.md` §6. Every routing decision here is a rule on a closed set of `DocumentType` values: the control flow is fully knowable in advance and drawable on a whiteboard. An agent would let the *model* decide the route on every call — paying for an extra LLM reasoning loop, introducing nondeterminism, and making the path un-traceable as a fixed graph — to implement what is fundamentally a `switch` statement. We use the deterministic primitive (`RunnableBranch`) precisely so that Week 3's ReAct agent has a clear foil: agents earn their loop tax only when the next step genuinely *cannot* be known ahead of time. Knowing when an agent is overkill is the lesson; this chain is the control group.