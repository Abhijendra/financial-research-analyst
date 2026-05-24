from langchain_core.runnables import Runnable, RunnableLambda
from analyst.extraction.structured import build_financials_extractor, build_full_extractor
from analyst.schemas.financials import CompanyFinancials

def test_return_type_of_build_():
    assert isinstance(build_financials_extractor(), Runnable)


class FakeChatModel:

    def __init__(self):
        self.bound_schema = None 

    def with_structured_output(self, schema):
        self.bound_schema = schema
         # return something pipe-compatible; a RunnableLambda works
        return RunnableLambda(lambda x: schema)  # or a sentinel

def test_schema_binding():
    fake = FakeChatModel()
    build_financials_extractor(model=fake)
    assert fake.bound_schema is CompanyFinancials

class RecordingChatModel:
    """Records every schema bound via `with_structured_output`."""

    def __init__(self):
        self.bound_schemas = []

    def with_structured_output(self, schema):
        self.bound_schemas.append(schema)
        return RunnableLambda(lambda x: schema)


def test_build_full_extractor():
    from analyst.schemas.risk import RiskFactorList
    from analyst.schemas.sentiment import SentimentScore

    fake = RecordingChatModel()
    chain = build_full_extractor(model=fake)

    assert isinstance(chain, Runnable)
    # All three branches must bind their schema on the shared model instance.
    assert set(fake.bound_schemas) == {CompanyFinancials, RiskFactorList, SentimentScore}
    assert len(fake.bound_schemas) == 3