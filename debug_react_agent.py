#!/usr/bin/env python3
"""
Debug script to test ReAct agent locally and identify the exact error.
"""

import asyncio
import os
from src.config import settings
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

async def test_langchain_llm():
    """Test LangChain ChatOpenAI initialization and basic call."""
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage
        
        print("🔧 Testing LangChain ChatOpenAI initialization...")
        
        # Test LangChain ChatOpenAI initialization
        llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        
        print(f"✅ LLM initialized successfully with model: {settings.openai_model}")
        
        # Test a simple call
        print("🔧 Testing LLM call...")
        test_message = HumanMessage(content="Hello, this is a test. Please respond with 'Test successful'.")
        response = await llm.agenerate([[test_message]])
        
        print(f"✅ LLM response: {response.generations[0][0].text}")
        return True
        
    except Exception as e:
        print(f"❌ LangChain LLM test failed: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        return False

async def test_react_agent():
    """Test ReAct agent initialization and basic functionality."""
    try:
        from src.processing.react_agent import process_query_with_agent
        
        print("🔧 Testing ReAct agent...")
        
        # Simple test query
        test_query = "Hello, can you help me?"
        
        # Mock search function for testing
        async def mock_search_function(query_embedding, search_type, limit, filters, similarity_threshold):
            return [{
                "id": "test-id",
                "score": 0.9,
                "text": "This is a test document for the RAG system.",
                "metadata": {
                    "document_id": "test-doc-id",
                    "filename": "test.txt",
                    "chunk_id": 0
                }
            }]
        
        # Mock search params
        search_params = {
            "query_embedding": [0.1] * 1536,  # Mock embedding
            "search_type": "hybrid",
            "limit": 5,
            "filters": None,
            "similarity_threshold": 0.7
        }
        
        # Test the agent
        result = await process_query_with_agent(
            query=test_query,
            search_function=mock_search_function,
            search_params=search_params,
            vector_store=None
        )
        
        print(f"✅ ReAct agent response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ ReAct agent test failed: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting ReAct Agent Debug Tests...")
    print(f"📋 OpenAI Model: {settings.openai_model}")
    print(f"📋 API Key Set: {'Yes' if settings.openai_api_key else 'No'}")
    print()
    
    # Test 1: LangChain LLM
    print("=" * 50)
    print("TEST 1: LangChain ChatOpenAI")
    print("=" * 50)
    llm_success = await test_langchain_llm()
    print()
    
    # Test 2: ReAct Agent
    print("=" * 50)
    print("TEST 2: ReAct Agent")
    print("=" * 50)
    agent_success = await test_react_agent()
    print()
    
    # Summary
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"LangChain LLM: {'✅ PASS' if llm_success else '❌ FAIL'}")
    print(f"ReAct Agent: {'✅ PASS' if agent_success else '❌ FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())
