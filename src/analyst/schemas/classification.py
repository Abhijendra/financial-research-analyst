from pydantic import BaseModel, Field
from analyst.schemas.provenance import DocumentType

class DocumentClassification(BaseModel):

    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str 

