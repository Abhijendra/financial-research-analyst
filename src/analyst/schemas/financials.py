from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date

class CompanyFinancials(BaseModel):
    """Headline financials for a single company in a single reporting period."""

    ticker: str = Field(description="Exchange ticker symbol, e.g. AAPL, RELIANCE.")

    period: Literal["Q1", "Q2", "Q3", "Q4", "FY"] = Field(description="Reporting period: Q1-Q4 or full year (FY).")
    
    revenue: float = Field(ge=0, description="Total revenue for the period, in `units` of `currency`.")
    
    net_income: Optional[float] = Field(default=None, 
                                        description="net profit; may be negative.") 
    
    eps: Optional[float] = Field(default=None, 
                                 description="Earning Per Share")

    currency: Literal["USD", "INR", "EUR", "GBP", "JPY"] = Field(description="ISO 4217 currency code of the figures.")
    
    units: Literal["thousands", "millions", "billions", "crore", "lakh"] = Field(description="Scale of the numeric fields, e.g. 'millions', 'crore'.")
    
    reporting_date: date = Field(description="End date of the reporting period, ISO 8601.")
