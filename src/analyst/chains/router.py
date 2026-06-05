from langchain_core.runnables import Runnable, RunnableBranch, RunnablePassthrough

from analyst.chains.classify import build_classify_chain
from analyst.chains.extractors import (
    build_default_chain,
    build_earnings_chain,
    build_filing_chain,
    build_news_chain,
)


def build_router_chain(
    model: Runnable | None = None,
    classify_chain=None,
    earning_chain=None,
    filing_chain=None,
    news_chain=None,
    default_chain=None,
):

    earning_chain = earning_chain or build_earnings_chain(model)
    filing_chain = filing_chain or build_filing_chain(model)
    news_chain = news_chain or build_news_chain(model)
    default_chain = default_chain or build_default_chain(model)

    classify_chain = classify_chain or RunnablePassthrough.assign(
        classification=build_classify_chain(model)
    )

    branched = RunnableBranch(
        (
            lambda x: x["classification"].document_type == "earnings_report",
            earning_chain,
        ),
        (
            lambda x: (
                x["classification"].document_type
                in ["annual_filing", "quarterly_filing"]
            ),
            filing_chain,
        ),
        (
            lambda x: (
                x["classification"].document_type in ["press_release", "news_article"]
            ),
            news_chain,
        ),
        default_chain,
    )

    # to make classification visible to the caller using RunnablePassthrough
    final_chain = classify_chain | RunnablePassthrough.assign(extraction=branched)

    return final_chain
