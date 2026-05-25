from langchain_core.runnables import RunnableLambda
from analyst.chains.classify import build_classify_chain
from analyst.schemas.classification import DocumentClassification

class FakeChatModel:

    def __init__(self):
        self.bound_schema = None 

    def with_structured_output(self, document_classification: DocumentClassification):
        return RunnableLambda(lambda _: DocumentClassification(document_type="earnings_report", confidence=0.8, reason="x")) 

# def test_negative_build_classify_chains():
#     model = FakeChatModel()
#     chain = build_classify_chain(model=model)
#     res = chain.invoke({"document_text":"ABC"})
#     assert res.document_type == "other"
    
def test_positive_build_classify_chains():
    model = FakeChatModel()
    chain = build_classify_chain(model=model)
    res = chain.invoke({"document_text":"ABC"})
    assert res.document_type == "earnings_report"