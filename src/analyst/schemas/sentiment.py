from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal

Label = Literal["positive", "neutral", "negative"]
class SentimentScore(BaseModel):
    """Overall sentiment of a document or chunk."""
    
    label: Label = Field(description="Categorical Sentiment.")
    
    score: float = Field(ge=-1.0, 
                         le=1.0, 
                         description="Continuous sentiment in [-1, 1].")
    
    rationale: str = Field(min_length=10, 
                           description="Why this label/score was assigned.")

    @model_validator(mode="after")
    def label_matches_score(self) -> "SentimentScore":
        if self.label == "positive" and self.score < 0:
            raise ValueError("positive label requires score >= 0")
        if self.label == "negative" and self.score > 0:
            raise ValueError("negative label requires score <= 0")
        return self