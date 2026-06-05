from langchain_core.runnables import RunnableLambda

from analyst.chains.classify import build_classify_chain
from analyst.schemas.classification import DocumentClassification


class FakeChatModel:
    def __init__(self, classification):
        self._classification = classification

    def with_structured_output(self, prompt):
        return RunnableLambda(lambda x: self._classification)


def test_build_classify_chain():
    fake_model = FakeChatModel(
        DocumentClassification(
            document_type="earnings_report", confidence=0.6, reason="x"
        )
    )
    chain = build_classify_chain(model=fake_model)
    result: DocumentClassification = chain.invoke(
        {"document_text": "Q3 earning report blah blah..."}
    )

    assert result.document_type == "earnings_report"
    assert result.confidence == 0.6


def test_downgrade_if_unsure():
    fmodel = FakeChatModel(
        DocumentClassification(
            document_type="earnings_report", confidence=0.3, reason="y"
        )
    )
    chain = build_classify_chain(model=fmodel)
    result: DocumentClassification = chain.invoke({"document_text": "blah blah..."})
    assert result.document_type == "other"
