"""Per-document-type extraction chains.

Recomposes the atomic extractors from `extraction/structured.py`
(`financials`, `risks`, `sentiment`) into four `RunnableParallel` recipes —
one per `DocumentType` family. No new prompts or model calls; just different
subsets of the same Lego bricks, so the router in `chains/router.py` has a
ready chain to dispatch to per classification.
"""
from langchain_core.runnables import Runnable, RunnableParallel

from analyst.extraction.structured import build_financials_extractor, build_risks_extractor, build_sentiment_extractor

from analyst.models import get_resilient_model

def build_earnings_chain(model: Runnable | None = None) -> Runnable:
    """Earnings reports — financials + risks + sentiment (everything)."""
    model = model or get_resilient_model()
    return RunnableParallel(
        financials=build_financials_extractor(model),
        risks=build_risks_extractor(model),
        sentiment=build_sentiment_extractor(model)
    )


def build_filing_chain(model: Runnable | None = None) -> Runnable:
    """10-K/10-Q filings — financials + risks; sentiment is meaningless on formal disclosures."""
    model = model or get_resilient_model()
    return RunnableParallel(
        financials=build_financials_extractor(model),
        risks=build_risks_extractor(model)
    )

def build_news_chain(model: Runnable | None = None) -> Runnable:
    """News / press releases — sentiment + risks; financials are usually absent."""
    model = model or get_resilient_model()
    return RunnableParallel(
        risks=build_risks_extractor(model),
        sentiment=build_sentiment_extractor(model)
    )

def build_default_chain(model: Runnable | None = None) -> Runnable:
    """Fallback for unknown / low-confidence docs — sentiment only as a safe minimum."""
    model = model or get_resilient_model()
    return RunnableParallel(
        sentiment=build_sentiment_extractor(model)
    )