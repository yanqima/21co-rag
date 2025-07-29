"""
LangChain ReAct Agent for intelligent query processing.
Uses LangChain's ReAct agent to decide whether to search for context or answer directly.
"""

from typing import List, Dict, Any, Optional
from langchain.agents import AgentType, initialize_agent
from langchain.tools import Tool
from langchain.schema import BaseMessage
from langchain.memory import ConversationBufferMemory
# Using custom LLM instead of ChatOpenAI
from src.config import settings
from src.monitoring.logger import get_logger
from src.processing.redis_memory import get_conversation_memory

logger = get_logger(__name__)


class DocumentSearchTool:
    """Tool for searching documents in the RAG system."""
    
    def __init__(self, search_function, search_params, embedding_generator):
        self.search_function = search_function
        self.search_params = search_params
        self.embedding_generator = embedding_generator
        self.last_search_results = []  # Track results for source extraction
    
    async def search(self, query: str) -> str:
        """Search documents and return formatted results."""
        try:
            # Generate embedding for the agent's query
            query_embeddings = await self.embedding_generator.generate_embeddings([query])
            query_embedding = query_embeddings[0]["embedding"]
            
            # Create search params with the new query embedding
            search_params = {
                "query_embedding": query_embedding,
                "search_type": self.search_params.get("search_type", "hybrid"),
                "limit": self.search_params.get("limit", 5),
                "filters": self.search_params.get("filters"),
                "similarity_threshold": self.search_params.get("similarity_threshold", 0.7)
            }
            
            # Call search function with all parameters
            results = await self.search_function(
                query_embedding=query_embedding,
                search_type=search_params["search_type"],
                limit=search_params["limit"],
                filters=search_params["filters"],
                similarity_threshold=search_params["similarity_threshold"],
                query_text=query if search_params["search_type"] == "hybrid" else None
            )
            self.last_search_results = results  # Store for source extraction
            logger.info(f"Search found {len(results)} results for query: {query}")
            
            if not results:
                return "No relevant documents found for this query."
            
            # Format results for the agent with clear context
            formatted_results = []
            formatted_results.append(f"Found {len(results)} relevant documents. Here are the top results:\n")
            
            for i, result in enumerate(results[:3]):  # Top 3 results
                formatted_results.append(
                    f"\nSource {i+1} (Relevance: {result.get('score', 0):.1%}):\n"
                    f"{result['text']}\n"
                    f"[From: {result['metadata'].get('filename', 'Unknown')}]"
                )
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            logger.error("document_search_failed", error=str(e))
            self.last_search_results = []
            return f"Error searching documents: {str(e)}"


class SystemInfoTool:
    """Tool for getting system information."""
    
    def __init__(self, vector_store):
        self.vector_store = vector_store
    
    async def get_info(self, query: str) -> str:
        """Get system information based on query."""
        query_lower = query.lower()
        
        try:
            # Always return document count for any query to this tool
            # The agent will decide when to use this tool
            documents, total = await self.vector_store.list_documents(0, 1)
            
            if "list" in query_lower or "what are" in query_lower or "them" in query_lower:
                # Get document list
                documents, total = await self.vector_store.list_documents(0, 20)
                if not documents:
                    return "No documents have been uploaded yet."
                
                doc_list = [f"The system currently contains {total} documents:"]
                for doc in documents:
                    doc_list.append(f"- {doc['filename']} ({doc['document_type'].upper()}, {doc['chunk_count']} chunks)")
                
                return "\n".join(doc_list)
            else:
                # Default to document count
                return f"The system currently contains {total} documents."
                
        except Exception as e:
            logger.error("system_info_failed", error=str(e))
            return f"Error getting system information: {str(e)}"


class LangChainReActAgent:
    """LangChain ReAct agent for intelligent query processing."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.llm = None
            self.agent = None
            self.doc_search_tool = None  # Store reference to track sources
            self.system_info_tool = None
            # Use Redis-based memory for persistence across requests
            self.memory = None  # Will be set per session
            self._initialized = True
    
    def _initialize_llm(self):
        """Initialize the custom LLM for the agent."""
        if self.llm is None:
            try:
                from src.processing.custom_llm import CustomOpenAILLM
                self.llm = CustomOpenAILLM(
                    model=settings.openai_model,
                    temperature=0.7,
                    api_key=settings.openai_api_key
                )
                logger.info("custom_llm_initialized", model=settings.openai_model)
            except Exception as e:
                logger.error("custom_llm_initialization_failed", error=str(e))
                # Fallback to a simple response system
                self.llm = None
    
    def _create_tools(self, search_function, search_params, vector_store, embedding_generator):
        """Create tools for the ReAct agent."""
        self.doc_search_tool = DocumentSearchTool(search_function, search_params, embedding_generator)
        self.system_info_tool = SystemInfoTool(vector_store)
        
        async def search_documents(query: str) -> str:
            """Search through uploaded documents for relevant information."""
            return await self.doc_search_tool.search(query)
        
        async def get_system_info(query: str) -> str:
            """Get information about the RAG system (document count, list, etc.)."""
            return await self.system_info_tool.get_info(query)
        
        return [
            Tool(
                name="search_documents",
                description="Search through uploaded documents to find information about ANY topic, concept, or question. Always use this tool when the user asks about specific subjects, facts, definitions, or content-related questions.",
                func=lambda q: search_documents(q),
                coroutine=search_documents
            ),
            Tool(
                name="get_system_info",
                description="Get information about the RAG system itself, such as how many documents are uploaded, list of documents, or system status. Use this ONLY for questions about the system, not for content questions.",
                func=lambda q: get_system_info(q),
                coroutine=get_system_info
            )
        ]
    
    async def process_query(self, query: str, search_function, search_params, vector_store, embedding_generator, session_id: str = "default"):
        """Process query using LangChain ReAct agent with custom LLM."""
        try:
            # Initialize LLM if not already done
            self._initialize_llm()
            
            if self.llm is None:
                logger.warning("LLM not initialized, using fallback")
                return await self._fallback_processing(query, search_function, search_params)
            
            # Update tools for this query (but don't recreate agent)
            self._create_tools(search_function, search_params, vector_store, embedding_generator)
            
            # Get or create Redis-based memory for this session
            session_memory = get_conversation_memory(session_id)
            
            # Initialize agent only once, but update memory for each session
            if self.agent is None:
                # Create sync wrapper functions for async tools
                def sync_search_documents(query: str) -> str:
                    """Synchronous wrapper for async document search."""
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        return loop.run_until_complete(self.doc_search_tool.search(query))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        return asyncio.run(self.doc_search_tool.search(query))
                
                def sync_get_system_info(query: str) -> str:
                    """Synchronous wrapper for async system info."""
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        return loop.run_until_complete(self.system_info_tool.get_info(query))
                    except RuntimeError:
                        # If no event loop is running, create a new one
                        return asyncio.run(self.system_info_tool.get_info(query))
                
                tools = [
                    Tool(
                        name="search_documents",
                        description="Search through uploaded documents for relevant information. Use this when you need to find specific information from the knowledge base.",
                        func=sync_search_documents
                    ),
                    Tool(
                        name="get_system_info", 
                        description="Get information about the RAG system, such as document count or list of available documents.",
                        func=sync_get_system_info
                    )
                ]
                
                # Custom system message for the agent
                system_message = f"""You are a helpful AI assistant with access to a document knowledge base.

Your role:
- Help users find information from uploaded documents
- Answer questions based on the available knowledge
- Be conversational and helpful
- Remember our conversation history

Available tools:
- search_documents: Search for relevant information in the knowledge base
- get_system_info: Get information about the system and available documents

Guidelines:
- When someone asks a factual question, ALWAYS search documents first
- Provide specific, accurate answers based on the search results
- If no relevant information is found, say so clearly
- For greetings or general questions, you can respond directly
- Always be helpful and conversational
- Remember what we've discussed before

Important: When you use search_documents, make sure to:
- Use relevant keywords from the user's question
- Search before attempting to answer factual questions
- Base your answers on the search results

For simple greetings like "hello" or "hi":
- Respond naturally without using any tools

Remember: When someone asks "What is X?" or any factual question, ALWAYS search documents first!"""
                
                # Initialize agent with custom prompt (only once)
                self.agent = initialize_agent(
                    tools=tools,
                    llm=self.llm,
                    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                    memory=session_memory,
                    verbose=True,
                    handle_parsing_errors=True,
                    agent_kwargs={
                        "system_message": system_message
                    }
                )
                logger.info(f"ReAct agent initialized with Redis memory for session: {session_id}")
            else:
                # Update the agent's memory for the current session
                self.agent.memory = session_memory
                logger.debug(f"Updated agent memory for session: {session_id}")
            
            # Process the query with the agent (preserving memory)
            response = await self.agent.arun(input=query)
            
            # Extract sources from the agent's tool usage
            sources = self._extract_sources_from_memory()
            
            return {
                "results": sources,
                "answer": response,
                "total_results": len(sources),
                "agent_action": "react_agent_response"
            }
            
        except Exception as e:
            logger.error("react_agent_failed", error=str(e))
            return await self._fallback_processing(query, search_function, search_params)
    
    def _extract_sources_from_memory(self) -> List[Dict[str, Any]]:
        """Extract source information from agent memory/tool usage."""
        if self.doc_search_tool and hasattr(self.doc_search_tool, 'last_search_results'):
            results = self.doc_search_tool.last_search_results
            logger.info(f"Extracting {len(results)} source results from memory")
            return results
        logger.warning("No doc_search_tool or last_search_results found")
        return []
    
    def clear_conversation_history(self):
        """Clear the conversation history."""
        if self.memory:
            self.memory.clear()
    
    async def _fallback_processing(self, query: str, search_function, search_params) -> Dict[str, Any]:
        """Fallback processing when LangChain agent fails."""
        logger.info("using_fallback_processing")
        
        # Simple greeting detection
        query_lower = query.lower().strip()
        greetings = ['hello', 'hi', 'hey', 'how are you', 'good morning', 'good afternoon', 'good evening']
        
        if any(greeting in query_lower for greeting in greetings):
            answer = "Hello! I'm your RAG assistant. I can help you search through your documents and answer questions about their content. How can I assist you today?"
            
            return {
                "results": [],
                "answer": answer,
                "total_results": 0,
                "agent_action": "direct_response"
            }
        
        # For other queries, search documents
        try:
            results = await search_function(**search_params)
            
            if results:
                # Import here to avoid circular imports
                from src.api.routes import generate_rag_answer
                answer = await generate_rag_answer(query, results)
            else:
                answer = "I couldn't find relevant information in your documents to answer that question. Could you try rephrasing or asking about something else?"
            
            return {
                "results": results,
                "answer": answer,
                "total_results": len(results),
                "agent_action": "search_and_answer"
            }
            
        except Exception as e:
            logger.error("fallback_search_failed", error=str(e))
            return {
                "results": [],
                "answer": "I'm having trouble processing your request right now. Please try again.",
                "total_results": 0,
                "agent_action": "error_response"
            }


# Create a singleton instance
_agent_instance = LangChainReActAgent()


async def process_query_with_agent(
    query: str,
    search_function,
    search_params: Dict[str, Any],
    vector_store=None,
    embedding_generator=None,
    session_id: str = "default"
) -> Dict[str, Any]:
    """
    Process query using LangChain ReAct agent.
    
    Args:
        query: User's query
        search_function: Function to perform document search
        search_params: Parameters for search function
        vector_store: Vector store instance for system info (optional)
        embedding_generator: Embedding generator for dynamic query embeddings
        session_id: Session identifier for persistent conversation memory
        
    Returns:
        Query response with results and answer
    """
    # Process query with LangChain ReAct agent
    result = await _agent_instance.process_query(query, search_function, search_params, vector_store, embedding_generator, session_id)
    
    return result