"""
Pydantic models for Country Agent API
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import List


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    service: str = "country-agent"
    version: str = "1.0.0"


class QueryRequest(BaseModel):
    """Request model for country queries."""
    query: str = Field(
        ...,
        description="The question about a country",
        examples=["What is the population of Germany?"]
    )


class QueryResponse(BaseModel):
    """Response model for country queries."""
    query: str = Field(..., description="The original query")
    answer: str = Field(..., description="The generated answer")
    status: str = Field("success", description="Response status")


class IntentType(Enum):
    """Supported intent types."""
    COUNTRY_INFO = "country_info"
    COMPARISON = "comparison"
    LIST = "list"
    UNKNOWN = "unknown"


class CountryField(Enum):
    """Supported country data fields."""
    POPULATION = "population"
    CAPITAL = "capital"
    CURRENCY = "currency"
    LANGUAGE = "language"
    REGION = "region"
    SUBREGION = "subregion"
    AREA = "area"
    FLAG = "flag"
    TIMEZONE = "timezone"
    CALLING_CODE = "calling_code"


# ==================== STRUCTURED OUTPUT MODELS ====================

class IntentResult(BaseModel):
    """Structured output for intent identification."""
    intent: str = Field(
        ..., 
        description="Classified intent: country_info, comparison, list, or unknown"
    )
    confidence: float = Field(
        ..., 
        description="Confidence score between 0.0 and 1.0",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        ..., 
        description="Brief explanation of the classification"
    )


class FieldExtractionResult(BaseModel):
    """Structured output for field extraction."""
    country_name: str = Field(
        ..., 
        description="The country name extracted from the query"
    )
    requested_fields: List[str] = Field(
        ..., 
        description="List of fields requested: population, capital, currency, language, region, subregion, area, flag, timezone, calling_code"
    )
    reasoning: str = Field(
        ..., 
        description="Brief explanation of what was extracted"
    )


class AnswerResult(BaseModel):
    """Structured output for answer synthesis."""
    answer: str = Field(
        ..., 
        description="Natural language answer to the user's question"
    )
    missing_info: List[str] = Field(
        default_factory=list,
        description="List of requested fields that couldn't be found"
    )
