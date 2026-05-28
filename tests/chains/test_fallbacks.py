from langchain_core.runnables import Runnable, RunnableLambda
from analyst.models import get_resilient_model


def test_fallback():
    def always_fails(x): raise RuntimeError("primary down")
    def always_succeed(x): return "from-fallback"
    primary = RunnableLambda(always_fails)
    secondary = RunnableLambda(always_succeed)

    chain = primary.with_fallbacks([secondary])
    result = chain.invoke("hi")
    assert result == "from-fallback"