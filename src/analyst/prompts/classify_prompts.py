from typing import get_args

from langchain_core.prompts import ChatPromptTemplate

from analyst.schemas.provenance import DocumentType

# Pull the allowed labels straight from the Literal so the prompt cannot
# drift from the schema. Single source of truth = `DocumentType`.
_ALLOWED_LABELS = ", ".join(get_args(DocumentType))

_SYSTEM = (
    "You are a financial document classifier.\n"
    "Choose exactly one label for the document from this set: "
    f"{_ALLOWED_LABELS}.\n"
    "\n"
    "Also return:\n"
    "  - confidence: a float in [0, 1] reflecting how sure you are.\n"
    "  - reason: one short sentence citing the specific cue in the text "
    "(header, section title, phrasing) that led to the label.\n"
    "\n"
    "Rules:\n"
    "  - Use only evidence present in the supplied text. Do not guess from "
    "world knowledge about the company or ticker.\n"
    "  - If the document does not clearly fit any specific label, return "
    "'other' with a low confidence rather than forcing a specialized label. "
    "A wrong specialized label is worse than an honest 'other'."
)

# `document_text` is expected to be pre-truncated by the caller (a
# RunnableLambda upstream slices to ~2k chars). ChatPromptTemplate uses
# str.format, which does NOT support slicing inside `{...}`.
CLASSIFICATION_PROMPT: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM),
        ("human", "Document:\n\n{document_text}"),
    ]
)