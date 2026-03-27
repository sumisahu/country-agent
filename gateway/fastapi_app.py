"""
FastAPI Gateway for Country Agent
Production-ready API endpoints.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from utils.helpers import setup_logging, truncate_string
from models.schemas import QueryRequest, QueryResponse, HealthResponse
from agents.country_agent import CountryAgent
from tools.country_api import get_country_client

# Setup logging
logger = setup_logging(name="Country-Agent", level="INFO")


# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Country Agent API...")
    
    # Initialize agent
    app.state.agent = CountryAgent()
    logger.info("Country Agent initialized")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Country Agent API...")
    client = get_country_client()
    await client.close()
    logger.info("Cleanup complete")


app = FastAPI(
    title="Country Information Agent",
    description="AI-powered agent for answering questions about countries using LangGraph",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== API ENDPOINTS ====================

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """
    Ask a question about a country.
    
    Examples:
    - "What is the population of Germany?"
    - "What currency does Japan use?"
    - "What is the capital and population of Brazil?"
    """
    try:
        agent = app.state.agent
        result = await agent.ask(request.query)
        
        # Log truncated answer for monitoring
        answer_preview = truncate_string(result["answer"], 80)
        logger.info(f"Query: '{request.query}' | Answer: {answer_preview}")
        
        return QueryResponse(
            query=result["query"],
            answer=result["answer"],
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )


@app.post("/agent/query", response_model=QueryResponse)
async def agent_query(request: QueryRequest):
    """
    Alternative endpoint for agent queries (same as /ask).
    Matches the pattern from the main project structure.
    """
    return await ask_question(request)
