"""
Country Information Agent using LangGraph
Production-ready implementation for answering questions about countries.
"""

from gateway.fastapi_app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
