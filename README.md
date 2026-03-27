# Country Information Agent

A production-ready AI agent that answers questions about countries using the REST Countries API. Built with **LangGraph** for multi-step reasoning.

## Features

- **Multi-step workflow**: Intent identification → Field extraction → Tool invocation → Answer synthesis
- **Natural language understanding**: Extracts country names and requested fields from queries
- **Graceful error handling**: Handles invalid inputs and missing data
- **Production-ready**: Structured code with proper logging, error handling, and typed interfaces

## Example Queries

- "What is the population of Germany?"
- "What currency does Japan use?"
- "What is the capital and population of Brazil?"

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Country Agent Pipeline                    │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────┐
│  1. Intent Identification        │
│     Classify query type          │
│     (country_info/comparison)    │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  2. Field Extraction             │
│     Extract country name         │
│     Identify requested fields    │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  3. Tool Invocation              │
│     Call REST Countries API      │
│     Fetch structured data        │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  4. Answer Synthesis             │
│     Generate natural response    │
│     Handle missing data          │
└──────────────────────────────────┘
```

## Project Structure

```
country_agent/
├── agents/
│   └── country_agent.py      # LangGraph workflow
├── gateway/
│   └── fastapi_app.py        # FastAPI endpoints
├── tools/
│   └── country_api.py        # REST Countries client
├── config/
│   └── settings.py           # Configuration
├── utils/
│   └── logger.py            # Utilities
├── main.py                   # Entry point
└── requirements.txt          # Dependencies
```

## Setup

### 1. Install Dependencies

```bash
cd country_agent
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=your_GROQ_api_key_here
PORT=8000
LOG_LEVEL=INFO
```

### 3. Run the Application

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### Ask a Question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the population of Germany?"}'
```

**Response:**

```json
{
  "query": "What is the population of Germany?",
  "answer": "Germany (Federal Republic of Germany) has a population of 83,190,556.",
  "status": "success"
}
```

### Alternative Endpoint

```bash
curl -X POST http://localhost:8000/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What currency does Japan use?"}'
```

## Supported Fields

The agent can extract and answer questions about:

- `population` - Total population
- `capital` - Capital city
- `currency` - Currency information
- `language` - Official languages
- `region` - Geographic region
- `subregion` - Subregion
- `area` - Land area in km²
- `flag` - Flag image URL
- `timezone` - Timezones
- `calling_code` - International calling codes

## Technical Details

### LangGraph Workflow

The agent uses a **4-node graph**:

1. **Intent Identification**: Uses LLM to classify query intent and confidence
2. **Field Extraction**: Extracts country name and maps fields to schema
3. **Tool Invocation**: Async call to REST Countries API with error handling
4. **Answer Synthesis**: Generates natural language response using structured data

### Production Considerations

- **Error handling**: Each node has try-catch with fallback responses
- **Type safety**: Full Pydantic models for state management
- **Logging**: Structured logging at each workflow step
- **Timeouts**: HTTP client with configurable timeouts
- **Resource management**: Proper cleanup of HTTP sessions

## Constraints Met

✅ **LangGraph used** (not single prompt)  
✅ **Intent identification step**  
✅ **Tool invocation step**  
✅ **Answer synthesis step**  
✅ **Production service design**  
✅ **No authentication**  
✅ **No database**  
✅ **No embeddings**  
✅ **No RAG**

