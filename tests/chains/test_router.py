import pytest
from langchain_core.runnables import RunnableLambda

from analyst.chains.router import build_router_chain
from analyst.schemas.classification import DocumentClassification


@pytest.mark.parametrize(
    "doc_type,expected_branch",
    [
        ("earnings_report", "earnings"),
        ("annual_filing", "filing"),
        ("quarterly_filing", "filing"),
        ("news_article", "news"),
        ("press_release", "news"),
        ("other", "default"),
    ],
)
def test_router_routes(doc_type, expected_branch):

    calls = []

    def make_spy(name):
        def spy(x):
            calls.append(name)
            return {"branch_that_run": name}

        return RunnableLambda(spy)

    def make_fake_classify(doc_type):
        classification = DocumentClassification(
            document_type=doc_type, confidence=0.9, reason="test"
        )
        # must ADD the key to the dict, like RunnablePassthrough.assign does
        return RunnableLambda(lambda x: {**x, "classification": classification})

    chain = build_router_chain(
        classify_chain=make_fake_classify(doc_type),
        earning_chain=make_spy("earnings"),
        filing_chain=make_spy("filing"),
        news_chain=make_spy("news"),
        default_chain=make_spy("default"),
    )

    chain.invoke({"document_text": "anything"})

    assert calls == [expected_branch]
