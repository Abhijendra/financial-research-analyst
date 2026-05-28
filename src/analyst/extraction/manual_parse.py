"""Manual structured extraction — the 'under-the-hood path'.

Exists to show what `ChatModel.with_structured_output(Schema)` hides. Instead
of provider-native tool-calling, we wire the three primitives by hand:

1. `PydanticOutputParser` — owns the schema; supplies
   `.get_format_instructions()` (string the LLM sees) and `.parse(text)`
   (string → validated Pydantic).
2. The LLM returns a plain string — no hidden binding; we're responsible for
   telling it what JSON shape to emit, via the format instructions injected
   into the prompt at build time.
3. `OutputFixingParser` — wraps the base parser; on a parse failure it sends
   the bad output back to an LLM for a one-shot repair, then re-parses.

Tradeoff vs `extraction/structured.py`: more code and an extra LLM hop on
failure, but works on any text-returning model (no tool-calling required) and
makes the raw reply inspectable. Kept side by side per CLAUDE.md §6.
"""

from langchain_core.runnables import Runnable, RunnableParallel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_classic.output_parsers.fix import OutputFixingParser
from analyst.models import get_resilient_model
from analyst.prompts.manual_extraction_prompts import MANUAL_FINANCIALS_PROMPT, MANUAL_RISKS_PROMPT, MANUAL_SENTIMENT_PROMPT
from analyst.schemas.financials import CompanyFinancials
from analyst.schemas.risk import RiskFactorList
from analyst.schemas.sentiment import SentimentScore
# from analyst.extraction.structured import attach_provenance  # re-used, not redefined

def build_financials_extractor(model: Runnable | None = None) -> Runnable:
    """Extract `CompanyFinancials` via the manual path.

    Composes `PydanticOutputParser` (schema → format instructions + .parse)
    with `OutputFixingParser` (one-shot LLM repair on parse failure). The
    parser's format instructions are baked into the prompt with `.partial()`
    so the call signature mirrors the structured-path factory exactly:
    callers still invoke with just `{"document_text": ...}`. Tradeoff vs
    `structured.build_financials_extractor`: no provider-native binding —
    works on any text-returning model, at the cost of one extra hop on a
    malformed reply.
    """
    model = model or get_resilient_model()
    parser = PydanticOutputParser(pydantic_object=CompanyFinancials)
    fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=model)
    prompt = MANUAL_FINANCIALS_PROMPT.partial(
        format_instructions=parser.get_format_instructions()
    )
    return prompt | model | fixing_parser

def build_risks_extractor(model: Runnable | None = None) -> Runnable:
    """Extract a `RiskFactorList` via the manual path.

    Same three-piece wiring as the financials factory
    (`PydanticOutputParser` + format-instructions injection +
    `OutputFixingParser`). Binds the list *wrapper* `RiskFactorList` (not
    `RiskFactor`) because the parser, like `with_structured_output`, needs a
    single root model — a bare `list[...]` won't produce usable format
    instructions.
    """
    model = model or get_resilient_model()
    parser = PydanticOutputParser(pydantic_object=RiskFactorList)
    fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=model)
    prompt = MANUAL_RISKS_PROMPT.partial(
        format_instructions=parser.get_format_instructions()
    )
    return prompt | model | fixing_parser

def build_sentiment_extractor(model: Runnable | None = None) -> Runnable:
    """Extract a `SentimentScore` via the manual path.

    Same `PydanticOutputParser` + format-instructions + `OutputFixingParser`
    composition. The schema's label↔score sign validator still runs at parse
    time; on violation, `OutputFixingParser` gets a chance to repair before
    the call raises. Tradeoff vs the structured path: more visible failure
    surface — the raw text reply is inspectable, which is exactly why this
    path is useful when a model's tool-calling is unreliable.
    """
    model = model or get_resilient_model()
    parser = PydanticOutputParser(pydantic_object=SentimentScore)
    fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=model)
    prompt = MANUAL_SENTIMENT_PROMPT.partial(
        format_instructions=parser.get_format_instructions()
    )
    return prompt | model | fixing_parser

def build_full_extractor(model: Runnable | None = None) -> Runnable:
    """Run all three manual extractors concurrently against a single chunk.

    `RunnableParallel` fans out the three independent LCEL branches from the
    same input, so total latency is max-of-three instead of sum-of-three. The
    output dict shape (`financials`, `risks`, `sentiment`) is identical to
    `structured.build_full_extractor` — by design, so downstream code is
    drop-in interchangeable between the two paths.
    """
    model = model or get_resilient_model()
    return RunnableParallel(
        financials=build_financials_extractor(model),
        risks=build_risks_extractor(model),
        sentiment=build_sentiment_extractor(model)
    )

if __name__ == "__main__":

    fin = build_full_extractor().invoke(
        {
            "document_text": """
Tech Titan and Retail Giant Post Latest Financial Results
MUMBAI & NEW YORK — Tech giant Cupertino Innovations (trading on NASDAQ under the ticker AAPL) dropped its highly anticipated financial scorecard for the final three months of its fiscal stretch. For the three-month period ending December 28, 2025 (2025-12-28), which corresponds to its Q1 frame, the company clocked a massive revenue of 119.6. Heavy investments in artificial intelligence infrastructure, however, compressed bottom-line margins, dragging down net income to a loss of -3.4. This translated to a diluted earnings per share figure of -0.45. Company executives confirmed that all figures in this specific North American filing are denominated in billions of USD.Meanwhile, halfway across the world, Indian retail behemoth Reliance Industries reported performance metrics for its fiscal third quarter (Q3), which concluded on December 31, 2025 (2025-12-31). Listed under the symbol RELIANCE, the conglomerate registered a gross revenue of 24,820 crore. Net profit data was withheld during the preliminary press call, and management did not disclose an explicit eps calculation for the quarter. All operational metrics for the domestic entity were reported strictly in INR.
"""
        }
    )
    print(fin)