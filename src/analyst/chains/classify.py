from langchain_core.runnables import Runnable, RunnableLambda

from analyst.models import get_chat_model
from analyst.schemas.classification import DocumentClassification
from analyst.prompts.classify_prompts import CLASSIFICATION_PROMPT

LOW_CONFIDENCE_THRESHOLD =0.5

def downgrade_if_unsure(c: DocumentClassification) -> DocumentClassification:

    if c.confidence < LOW_CONFIDENCE_THRESHOLD:
        original = c.document_type
        c.document_type = "other"
        c.reason = f"low confidence ({c.confidence:.2f}); original guess was {original}"
    return c

def build_classify_chain(model: Runnable | None = None) -> Runnable:
    model = model or get_chat_model()
    truncate = RunnableLambda(lambda x: {"document_text":x["document_text"][:2000]})
    downgrade_if_required = RunnableLambda(downgrade_if_unsure)
    chain = truncate | CLASSIFICATION_PROMPT | model.with_structured_output(DocumentClassification) | downgrade_if_required
    return chain