# Spec: Manual Parse Extraction

## Overview
Implement `src/analyst/extraction/manual_parse.py` — the "under-the-hood path"
for structured extraction. Where `extraction/structured.py` leans on
`ChatModel.with_structured_output(Schema)` (which uses provider-native
tool-calling and hides the wiring), this module rebuilds the same behavior by
hand: a `PydanticOutputParser` generates JSON-schema format instructions that
get injected into the prompt, the model returns a plain text string, the
parser validates that string into a Pydantic instance, and an
`OutputFixingParser` wraps the whole thing so a malformed response gets a
second LLM-powered repair pass instead of crashing. The point is purely
pedagogical (per `CLAUDE.md` §6): seeing the format-instructions string, the
raw text reply, and the repair loop is what makes the "easy path" make sense.

## Depends on
- **Schemas** (done): `CompanyFinancials`, `RiskFactorList`, `SentimentScore`
  in `src/analyst/schemas/`.
- **Configurable model layer** (done): `analyst.models.get_chat_model`.
- **Prompts module** (done in spec 04): `FINANCIALS_PROMPT`, `RISKS_PROMPT`,
  `SENTIMENT_PROMPT`. These will need a small change — they currently have no
  slot for `{format_instructions}`, so we either extend them or define
  parallel "manual" prompts in this module. Step 2 below decides.
- **`extraction/structured.py`** (done): used as the side-by-side comparison
  point. Public surface (factory names and signatures) should mirror it so the
  two files are trivially diffable.

## Implementation steps
Build incrementally; each step should leave the repo runnable.

1. **Understand the three moving parts (read before coding).**
   - `PydanticOutputParser(pydantic_object=Schema)` — knows the schema. Gives
     you `.get_format_instructions()` (a string telling the LLM what JSON
     shape to emit) and `.parse(text)` (string → validated Pydantic).
   - The LLM, this time, returns a **plain string**. No tool-calling, no
     hidden binding. We are responsible for telling it what to emit.
   - `OutputFixingParser.from_llm(parser=..., llm=...)` — wraps the base
     parser. If `.parse()` raises, it asks an LLM to fix the bad output and
     re-parse. Demonstrates resilience without bespoke retry code.

2. **Decide where format instructions live in the prompt.** The existing
   prompts in `prompts/extraction_prompts.py` have no `{format_instructions}`
   placeholder. Two options:
   - (a) Edit the existing prompts to add a `{format_instructions}` slot in
     the system message. Simpler, but the "structured path" doesn't need it
     and will get an unused variable.
   - (b) Define `MANUAL_*_PROMPT` constants inside `manual_parse.py` (or in a
     new `prompts/manual_extraction_prompts.py`). Cleaner separation.

   **Pick (b)** — keeps the two paths independent and makes the contrast
   obvious in code review. Add the prompts at the top of `manual_parse.py`
   for now (move to `prompts/` only if reused).

3. **Write the manual prompts.** Same system instruction as the structured
   path, plus this line appended:
   `"Respond ONLY with valid JSON matching this schema:\n{format_instructions}"`.
   Human message stays `Document:\n\n{document_text}`. Use
   `ChatPromptTemplate.from_messages(...).partial(format_instructions=...)`
   so the parser's instructions are baked in at build time and callers still
   invoke with just `{"document_text": ...}` (mirrors the structured path's
   call signature).

4. **Write `src/analyst/extraction/manual_parse.py`** with four public
   factories — same names as `structured.py`, suffixed `_manual` is **not**
   needed because the module name already disambiguates:
   - `build_financials_extractor(model: Runnable | None = None) -> Runnable`
   - `build_risks_extractor(model: Runnable | None = None) -> Runnable`
   - `build_sentiment_extractor(model: Runnable | None = None) -> Runnable`
   - `build_full_extractor(model: Runnable | None = None) -> Runnable`

   Each one builds, in order:
   ```
   parser = PydanticOutputParser(pydantic_object=Schema)
   fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=model)
   prompt = MANUAL_<X>_PROMPT.partial(
       format_instructions=parser.get_format_instructions()
   )
   return prompt | model | fixing_parser
   ```
   `build_full_extractor` returns a `RunnableParallel` with keys
   `financials`, `risks`, `sentiment` — identical shape to the structured
   path so downstream code (and tests) doesn't care which path produced it.

5. **Reuse `attach_provenance`.** Do NOT duplicate it here. Import it from
   `analyst.extraction.structured` (or, better, lift it to a shared
   `extraction/_provenance.py` if the import feels backwards). Provenance
   still comes from ingestion metadata, never from the LLM.

6. **Docstrings — make the lesson explicit.** Module docstring states: "This
   module exists to show what `with_structured_output` hides." Each factory
   docstring names the three components (`PydanticOutputParser`,
   `OutputFixingParser`, the format-instructions injection) and the tradeoff
   vs the structured path (more code, no provider-native binding, but works
   on any model that returns text — including models without tool-calling).

7. **Tests** — `tests/extraction/test_manual_parse.py`:
   - Type-only test: each factory returns a `Runnable`.
   - Format-instructions test: build the prompt, render it with a dummy
     `document_text`, and assert the rendered string contains the substring
     `"JSON"` and the schema's field names (e.g. `"ticker"` for financials).
     This proves the parser's instructions actually reached the prompt.
   - Repair-path test: feed `OutputFixingParser` a deliberately malformed
     JSON string via a fake LLM that returns valid JSON on the repair call;
     assert a validated Pydantic instance comes out. Do NOT call a real LLM.
   - Do not assert exact LLM wording (`CLAUDE.md` §8).

8. **Smoke run** — optional `__main__` block (commented out, like
   `structured.py`) that invokes `build_full_extractor` against the same
   sample text used in `structured.py`. The output should be structurally
   indistinguishable from the structured path's output — that's the whole
   point.

9. **Update `DECISIONS.md`** — one paragraph each for:
   - Why both paths exist (pedagogy; not redundancy).
   - `OutputFixingParser` over manual `try/except` + retry (one LLM hop with
     a known repair prompt vs. hand-rolled control flow).
   - `prompt.partial(format_instructions=...)` over passing them at invoke
     time (call signature stays identical to the structured path → the two
     are drop-in interchangeable for callers).
   - When you would actually pick this path in production (models without
     tool-calling, providers whose structured-output API is unreliable, or
     when you need to log/inspect the raw text reply).

## Files to change
- `DECISIONS.md` — append the four decision entries listed above.
- `src/analyst/extraction/manual_parse.py` — currently empty, fill in.
- (Possibly) `src/analyst/extraction/structured.py` — only if `attach_provenance`
  is moved to a shared module; otherwise leave alone.

## Files to create
- `tests/extraction/test_manual_parse.py`
- (Optional) `src/analyst/extraction/_provenance.py` — only if step 5 chooses
  to lift `attach_provenance` to a shared location.

## New dependencies
No new dependencies. `PydanticOutputParser` and `OutputFixingParser` both live
in `langchain` / `langchain-core`, already pinned in `pyproject.toml`.

## Definition of done
- [ ] `python -c "from analyst.extraction.manual_parse import build_full_extractor; print(build_full_extractor())"` returns a `RunnableParallel`.
- [ ] `pytest tests/extraction/test_manual_parse.py` passes.
- [ ] Rendering a manual prompt with a sample `document_text` produces a
      string that contains `"JSON"` and at least one schema field name —
      proof the format instructions are actually injected.
- [ ] A deliberately malformed JSON, when run through the
      `OutputFixingParser` with a fake repair LLM, yields a validated
      Pydantic instance instead of raising.
- [ ] Invoking the manual `build_full_extractor` on the same sample text used
      by the structured path produces a dict with the same three keys
      (`financials`, `risks`, `sentiment`) holding the same Pydantic types.
- [ ] `ruff check src/analyst/extraction/manual_parse.py` and
      `ruff format --check` are clean.
- [ ] `DECISIONS.md` has the four new entries, each one paragraph, each
      defensible in an interview.
- [ ] No API keys appear in any tracked file
      (`git grep -E "sk-[A-Za-z0-9]"` returns nothing).
