## Golden Guide to write schema

1. Every field gets a description. With .with_structured_output(), descriptions become part of the prompt the model sees. A schema without descriptions is a half-written prompt.
2. Optional[...] vs required matters more than it looks. Required fields the document doesn't contain → the model invents values. Default to Optional for for anything that isn't guaranteed to appear in every document.
3. Constrain numerics with ge/le/gt/lt. Use ge/le (inclusive) unless you have a real reason to exclude endpoints.
4. Cross-field invariants → model_validator. Single-field invariants → field_validator or Field(...).
5. Provenance lives on the data, not next to it. Before extraction, it is good to add schemas/provenance.py with source: str, page: Optional[int], document_type: str, ticker: Optional[str], date: Optional[date]. Then each top-level extraction model gets a provenance: Provenance field. This is what makes the memo writer in Week 4 able to cite.
6. Literal > str wherever you have a closed set of values. This is the cheapest validation in Pydantic and it doubles as documentation for the LLM.

### Provenance schema
- document_type is a Literal, not free text. Week 2's classifier will write into this field, and Week 2's router (RunnableBranch) will read it. A closed set keeps the router exhaustive.
- page is Optional because not every source has pages (news articles, transcripts).
- ticker lives on Provenance, not just on CompanyFinancials. Risks and sentiment also need to be attributable to a company — putting it on provenance avoids duplicating the field across every extraction schema.
- published_date is separate from CompanyFinancials.reporting_date. A 10-K filed in March 2025 reports on fiscal year 2024. Conflating them silently corrupts time-series analysis later.

## models.py
1. Why ChatOpenAI instead of OpenAI?