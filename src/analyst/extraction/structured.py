"""Structured-output extraction — the 'modern easy path'.

Demonstrates `ChatModel.with_structured_output(Schema)`: provider-native
tool/function calling binds a Pydantic schema as the model's reply shape,
giving validated Pydantic instances directly. Contrast with
`extraction/manual_parse.py`, which builds the same thing by hand using
`PydanticOutputParser` + `OutputFixingParser` — kept side by side per
CLAUDE.md §6 so the tradeoff is visible.
"""
from langchain_core.runnables import Runnable, RunnableParallel
from analyst.models import get_resilient_model
from analyst.prompts.extraction_prompts import FINANCIALS_PROMPT, RISKS_PROMPT, SENTIMENT_PROMPT
from analyst.schemas.financials import CompanyFinancials
from analyst.schemas.risk import RiskFactorList
from analyst.schemas.sentiment import SentimentScore

def build_financials_extractor(model: Runnable | None = None) -> Runnable:
    """Extract `CompanyFinancials` from a single chunk.

    LCEL: `prompt | model.with_structured_output(Schema)`. The model is
    constrained at the API level (tool-calling), so the return value is a
    validated Pydantic instance, not a string to parse.
    """    
    model = model or get_resilient_model()
    return FINANCIALS_PROMPT | model.with_structured_output(CompanyFinancials)

def build_risks_extractor(model: Runnable | None = None) -> Runnable:
    """Extract a `RiskFactorList` from a single chunk.

    Binds the list *wrapper* (not `RiskFactor` directly) because
    `with_structured_output` accepts exactly one root schema — a list of
    items must be held inside a container model.
    """    
    model = model or get_resilient_model()
    return RISKS_PROMPT | model.with_structured_output(RiskFactorList)

def build_sentiment_extractor(model: Runnable | None = None) -> Runnable:
    """Extract a `SentimentScore` from a single chunk.

    The schema's `model_validator` enforces label↔score sign agreement; the
    prompt mirrors that rule so the model rarely produces invalid combos.
    """    
    model = model or get_resilient_model()
    return SENTIMENT_PROMPT | model.with_structured_output(SentimentScore)

def build_full_extractor(model: Runnable | None = None) -> Runnable:
    """Run all three extractors concurrently against a single chunk.

    Demonstrates `RunnableParallel`: independent LCEL branches fan out from
    the same input, giving max-of-three latency instead of sum-of-three.
    The shared `model` is resolved once at the top so all branches reuse the
    same configurable instance (one model object, three concurrent calls).
    """
    model = model or get_resilient_model()
    return RunnableParallel(
        financials=build_financials_extractor(model),
        risks=build_risks_extractor(model),
        sentiment=build_sentiment_extractor(model)
    )


# if __name__ == "__main__":

#     fin = build_full_extractor().invoke(
#         {
#             "document_text": """
# Tech Titan and Retail Giant Post Latest Financial Results
# MUMBAI & NEW YORK — Tech giant Cupertino Innovations (trading on NASDAQ under the ticker AAPL) dropped its highly anticipated financial scorecard for the final three months of its fiscal stretch. For the three-month period ending December 28, 2025 (2025-12-28), which corresponds to its Q1 frame, the company clocked a massive revenue of 119.6. Heavy investments in artificial intelligence infrastructure, however, compressed bottom-line margins, dragging down net income to a loss of -3.4. This translated to a diluted earnings per share figure of -0.45. Company executives confirmed that all figures in this specific North American filing are denominated in billions of USD.Meanwhile, halfway across the world, Indian retail behemoth Reliance Industries reported performance metrics for its fiscal third quarter (Q3), which concluded on December 31, 2025 (2025-12-31). Listed under the symbol RELIANCE, the conglomerate registered a gross revenue of 24,820 crore. Net profit data was withheld during the preliminary press call, and management did not disclose an explicit eps calculation for the quarter. All operational metrics for the domestic entity were reported strictly in INR.
# """
#         }
#     )
#     print(fin)