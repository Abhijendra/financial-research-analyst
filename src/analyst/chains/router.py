from langchain_core.runnables import Runnable,\
    RunnablePassthrough, RunnableLambda, RunnableBranch

from analyst.chains.classify import build_classify_chain
from analyst.chains.extractors import build_earnings_chain, \
    build_filing_chain, build_news_chain, build_default_chain
from analyst.schemas.provenance import DocumentType

def build_router_chain(model: Runnable | None = None):

    earning_chain = build_earnings_chain(model)
    filing_chain = build_filing_chain(model)
    news_chain = build_news_chain(model)
    default_chain = build_default_chain(model)

    classified = RunnablePassthrough.assign(classification=build_classify_chain(model))

    branched = RunnableBranch(
        (lambda x: x["classification"].document_type == "earnings_report", earning_chain),
        (lambda x: x["classification"].document_type in ["annual_filing", "quarterly_filing"], filing_chain),
        (lambda x: x["classification"].document_type in ["press_release", "news_article"], news_chain),
        RunnableLambda(lambda x: default_chain)
    )

    # to make classification visible to the caller using RunnablePassthrough
    final_chain = classified | RunnablePassthrough.assign(extraction=branched)

    return final_chain
    