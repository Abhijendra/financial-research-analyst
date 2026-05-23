from pydantic import BaseModel, Field
from typing import Optional, Literal


class RiskFactor(BaseModel):
    """A single risk disclosed in a filing, with the supporting excerpt."""

    category: Literal["market", "credit", "operational", "regulatory", "liquidity", "cyber", "geopolitical", "other"] = Field(description="Risk taxonomy bucket.")

    description: str = Field(min_length=10, 
                             description="One sentence summary of the risk.")
    
    severity: Literal["high", "medium", "low"] = Field(description="Analyst-assigned severity.")
    
    source_excerpt: str = Field(min_length=10, 
                                description="Verbatim quote from the document supporting this risk; used for citation.")