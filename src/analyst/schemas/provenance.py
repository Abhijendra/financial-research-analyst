from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

DocumentType = Literal[
    "earnings_report",
    "annual_filing",
    "quarterly_filing",
    "press_release",
    "news_article",
    "transcript",
    "other",
]


class Provenance(BaseModel):
    """Where a piece of extracted data came from.

    Attached to every extraction result so the memo writer downstream can
    produce real citations (file + page + document type). Propagated from
    ingestion → chunking → extraction; do not drop these fields on the way.
    """

    source: str = Field(
        description="Identifier of the source document, e.g. file path, URL, or filing ID."
    )
    document_type: DocumentType = Field(
        description="Kind of document this came from; drives downstream prompt/route choices."
    )
    page: Optional[int] = Field(
        default=None,
        ge=1,
        description="1-indexed page number within the source document, if known.",
    )
    ticker: Optional[str] = Field(
        default=None,
        description="Exchange ticker the document is about, if it pertains to a single company.",
    )
    published_date: Optional[date] = Field(
        default=None,
        description="Publication or filing date of the source document, ISO 8601.",
    )
