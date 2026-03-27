"""
Country Agent using LangGraph - Tool-based approach
Multi-step workflow for answering country-related questions.
Uses structured output tools instead of prompt engineering.
"""

from typing import Dict, Any, List, Optional, TypedDict


from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from utils.helpers import setup_logging

from tools.country_api import fetch_country_data, CountryField, CountryData
from config.settings import get_settings
from models.schemas import IntentType, IntentResult,FieldExtractionResult, AnswerResult

logger = setup_logging("Country-Agent")




# ==================== AGENT STATE ====================

class AgentState(TypedDict):
    """State maintained throughout the agent workflow."""
    user_query: str
    intent: Optional[str]
    confidence: Optional[float]
    country_name: Optional[str]
    requested_fields: List[CountryField]
    country_data: Optional[CountryData]
    api_error: Optional[str]
    answer: Optional[str]
    missing_info: List[str]
    error_stats: Optional[Dict[str, Any]]


# ==================== TOOL-BASED AGENT ====================

class CountryAgent:
    """
    Production-grade country information agent using LangGraph.
    Uses structured output tools instead of prompt engineering.
    
    Workflow:
    1. Intent Identification Tool - Structured classification
    2. Field Extraction Tool - Structured extraction
    3. Tool Invocation - REST Countries API call
    4. Answer Synthesis Tool - Structured answer generation
    """
    
    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        settings = get_settings()
        self.llm = ChatGroq(
            model=model_name,
            temperature=0.1,
            api_key=settings.GROQ_API_KEY
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow with tool nodes."""
        workflow = StateGraph(AgentState)
        
        # Add tool-based nodes
        workflow.add_node("intent_tool", self._intent_identification_tool)
        workflow.add_node("field_tool", self._field_extraction_tool)
        workflow.add_node("api_tool", self._api_invocation_tool)
        workflow.add_node("answer_tool", self._answer_synthesis_tool)
        workflow.add_node("error_handler", self._error_handler)
        
        # Define edges
        workflow.set_entry_point("intent_tool")
        
        workflow.add_conditional_edges(
            "intent_tool",
            self._should_continue_to_fields,
            {"fields": "field_tool", "error": "error_handler"}
        )
        
        workflow.add_edge("field_tool", "api_tool")
        
        workflow.add_conditional_edges(
            "api_tool",
            self._should_continue_to_answer,
            {"answer": "answer_tool", "error": "error_handler"}
        )
        
        workflow.add_edge("answer_tool", END)
        workflow.add_edge("error_handler", END)
        
        return workflow.compile()
    
    # ==================== TOOL 1: INTENT IDENTIFICATION ====================
    
    async def _intent_identification_tool(self, state: AgentState) -> AgentState:
        """Use structured output to classify intent."""
        logger.info(f"[Intent Tool] Query: {state['user_query']}")
        
        try:
            # Bind structured output to LLM
            structured_llm = self.llm.with_structured_output(IntentResult)
            
            messages = [
                ("system", """You are an intent classification system.
                
                Analyze the user's query about countries and classify it into one of these intents:
                - country_info: User wants specific information about one country
                - comparison: User wants to compare multiple countries
                - list: User wants a list of countries
                - unknown: Query is not about country information
                
                Provide a confidence score (0.0-1.0) and brief reasoning."""),
                ("human", state["user_query"])
            ]
            
            result: IntentResult = await structured_llm.ainvoke(messages)
            
            logger.info(f"[Intent Tool] Result: {result.intent} (confidence: {result.confidence})")
            
            return {
                **state,
                "intent": result.intent,
                "confidence": result.confidence
            }
            
        except Exception as e:
            logger.error(f"[Intent Tool] Error: {e}")
            return {
                **state,
                "intent": "unknown",
                "confidence": 0.0,
                "api_error": f"Intent classification failed: {str(e)}"
            }
    
    def _should_continue_to_fields(self, state: AgentState) -> str:
        """Determine next step based on intent classification."""
        intent = state.get("intent", "unknown")
        confidence = state.get("confidence", 0.0)
        
        if intent == IntentType.COUNTRY_INFO.value and confidence >= 0.6:
            return "fields"
        elif intent in ["comparison", "list"]:
            state["api_error"] = f"Query type '{intent}' is not supported yet."
            return "error"
        else:
            state["api_error"] = "I'm not sure what country information you're looking for. Try asking about a specific country's population, capital, currency, etc."
            return "error"
    
    # ==================== TOOL 2: FIELD EXTRACTION ====================
    
    async def _field_extraction_tool(self, state: AgentState) -> AgentState:
        """Use structured output to extract country name and fields."""
        logger.info(f"[Field Tool] Query: {state['user_query']}")
        
        try:
            # Bind structured output to LLM
            structured_llm = self.llm.with_structured_output(FieldExtractionResult)
            
            field_options = [f.value for f in CountryField]
            
            messages = [
                ("system", f"""You are a field extraction system.
                
                Extract from the user's query:
                1. The country name (exactly as mentioned)
                2. The fields of information requested
                
                Available fields: {', '.join(field_options)}
                
                Guidelines:
                - "What currency does Japan use?" -> fields: ["currency"]
                - "What is the capital and population of Brazil?" -> fields: ["capital", "population"]
                - Map common terms to field names (money -> "currency", people -> "population")"""),
                ("human", state["user_query"])
            ]
            
            result: FieldExtractionResult = await structured_llm.ainvoke(messages)
            
            # Map string fields to CountryField enum
            requested_fields = []
            for field_str in result.requested_fields:
                try:
                    requested_fields.append(CountryField(field_str.lower()))
                except ValueError:
                    logger.warning(f"[Field Tool] Unknown field: {field_str}")
            
            # Default to basic info if no fields
            if not requested_fields:
                requested_fields = [CountryField.POPULATION, CountryField.CAPITAL, CountryField.REGION]
            
            logger.info(f"[Field Tool] Country: {result.country_name}, Fields: {[f.value for f in requested_fields]}")
            
            return {
                **state,
                "country_name": result.country_name,
                "requested_fields": requested_fields
            }
            
        except Exception as e:
            logger.error(f"[Field Tool] Error: {e}")
            return {
                **state,
                "api_error": f"Field extraction failed: {str(e)}"
            }
    
    # ==================== TOOL 3: API INVOCATION ====================
    
    async def _api_invocation_tool(self, state: AgentState) -> AgentState:
        """Invoke the REST Countries API tool."""
        country_name = state.get("country_name")
        
        if not country_name:
            return {
                **state,
                "api_error": "No country name was extracted.",
                "country_data": None
            }
        
        logger.info(f"[API Tool] Fetching data for: {country_name}")
        
        try:
            country_data = await fetch_country_data(country_name)
            
            if country_data is None:
                return {
                    **state,
                    "api_error": f"Country '{country_name}' not found.",
                    "country_data": None
                }
            
            logger.info(f"[API Tool] Successfully fetched data for: {country_data.name}")
            
            return {
                **state,
                "country_data": country_data,
                "api_error": None
            }
            
        except Exception as e:
            logger.error(f"[API Tool] Error: {e}")
            return {
                **state,
                "api_error": f"API call failed: {str(e)}",
                "country_data": None
            }
    
    def _should_continue_to_answer(self, state: AgentState) -> str:
        """Determine next step based on API result."""
        if state.get("api_error") or state.get("country_data") is None:
            return "error"
        return "answer"
    
    # ==================== TOOL 4: ANSWER SYNTHESIS ====================
    
    async def _answer_synthesis_tool(self, state: AgentState) -> AgentState:
        """Use structured output to generate natural language answer."""
        country_data = state["country_data"]
        requested_fields = state["requested_fields"]
        
        logger.info(f"[Answer Tool] Generating answer for {country_data.name}")
        
        # Build field info
        field_info = []
        missing_info = []
        
        for field in requested_fields:
            value = country_data.get_field_value(field)
            if value:
                field_info.append(f"{field.value}: {value}")
            else:
                missing_info.append(field.value)
        
        try:
            # Bind structured output to LLM
            structured_llm = self.llm.with_structured_output(AnswerResult)
            
            messages = [
                ("system", """You are a helpful assistant providing country information.
                
                Create a natural, conversational answer based on the structured data.
                Be concise but complete. Use natural language (not bullet points)."""),
                ("human", f"""User asked: {state["user_query"]}
                
                Country: {country_data.official_name or country_data.name}
                
                Information available:
                {chr(10).join(field_info)}
                
                Missing information: {', '.join(missing_info) if missing_info else 'None'}
                
                Provide a natural response:""")
            ]
            
            result: AnswerResult = await structured_llm.ainvoke(messages)
            
            logger.info(f"[Answer Tool] Generated answer")
            
            return {
                **state,
                "answer": result.answer,
                "missing_info": missing_info
            }
            
        except Exception as e:
            logger.error(f"[Answer Tool] Error: {e}")
            
            # Fallback to templated answer
            simple_answer = f"{country_data.name}"
            if country_data.population:
                simple_answer += f" has a population of {country_data.population:,}."
            if country_data.capital:
                simple_answer += f" Its capital is {country_data.capital[0]}."
            
            return {
                **state,
                "answer": simple_answer,
                "missing_info": missing_info
            }
    
    # ==================== ERROR HANDLER ====================
    
    def _error_handler(self, state: AgentState) -> AgentState:
        """Handle errors gracefully and persist error statistics."""
        error = state.get("api_error")
        
        # Build error stats to persist
        error_stats = {
            "error_type": "api_error" if error else "unknown_error",
            "error_message": error,
            "intent_at_error": state.get("intent"),
            "confidence_at_error": state.get("confidence"),
            "country_name_at_error": state.get("country_name"),
            "requested_fields_at_error": [f.value for f in state.get("requested_fields", [])]
        }
        
        # If api_error wasn't set (conditional edge issue), determine error from intent
        if error is None:
            intent = state.get("intent", "unknown")
            if intent in ["comparison", "list"]:
                error = f"Query type '{intent}' is not supported yet."
            else:
                error = "I'm not sure what country information you're looking for. Try asking about a specific country's population, capital, currency, etc."
            error_stats["error_type"] = "intent_error"
            error_stats["error_message"] = error
        
        logger.warning(f"[Error Handler] {error}")
        
        return {
            **state,
            "api_error": error,
            "answer": error,
            "error_stats": error_stats
        }
    
    # ==================== PUBLIC API ====================
    
    async def ask(self, query: str) -> Dict[str, Any]:
        """Main entry point for asking a question."""
        logger.info(f"[Agent] Processing query: {query}")
        
        initial_state: AgentState = {
            "user_query": query,
            "intent": None,
            "confidence": None,
            "country_name": None,
            "requested_fields": [],
            "country_data": None,
            "api_error": None,
            "answer": None,
            "missing_info": []
        }
        
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "query": query,
            "answer": result.get("answer", "No answer generated."),
            "country": result.get("country_name"),
            "intent": result.get("intent"),
            "confidence": result.get("confidence"),
            "requested_fields": [f.value for f in result.get("requested_fields", [])],
            "missing_info": result.get("missing_info", [])
        }
