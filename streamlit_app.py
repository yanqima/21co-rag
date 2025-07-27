import streamlit as st
import requests
import json
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="RAG System Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-message {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .document-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        margin-bottom: 0.5rem;
        transition: transform 0.2s;
    }
    .document-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    .search-result {
        background: #f0f8ff;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 5px;
        font-weight: 500;
        transition: opacity 0.3s;
    }
    .stButton > button:hover {
        opacity: 0.8;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_base_url' not in st.session_state:
    st.session_state.api_base_url = "http://localhost:8000/api/v1"
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Header
st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; text-align: center;">🚀 RAG System Demo</h1>
    <p style="text-align: center; margin-top: 0.5rem; opacity: 0.9;">
        Production-Ready Retrieval-Augmented Generation System
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    api_url = st.text_input(
        "API Base URL",
        value=st.session_state.api_base_url,
        help="The base URL of your RAG API"
    )
    if api_url != st.session_state.api_base_url:
        st.session_state.api_base_url = api_url
    
    st.divider()
    
    # Health check
    st.subheader("🏥 System Health")
    if st.button("Check Health", use_container_width=True):
        try:
            response = requests.get(f"{st.session_state.api_base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                st.success("✅ System is healthy!")
                st.json(health_data)
            else:
                st.error(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Connection error: {str(e)}")
    
    st.divider()
    
    # Quick stats
    st.subheader("📊 Quick Stats")
    try:
        docs_response = requests.get(f"{st.session_state.api_base_url}/documents")
        if docs_response.status_code == 200:
            docs_data = docs_response.json()
            total_docs = docs_data.get("total", 0)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Documents", total_docs)
            with col2:
                st.metric("Collections", "1")
    except:
        st.info("Connect to API to see stats")

# Main content area with tabs
tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Documents", "🔍 Search & Query", "📚 Document Library", "💬 Chat Interface"])

# Tab 1: Upload Documents
with tab1:
    st.header("Upload Documents")
    st.markdown("Upload PDF, TXT, or JSON files to add them to the knowledge base.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'txt', 'json'],
            help="Maximum file size: 50MB"
        )
    
    with col2:
        st.markdown("### Chunking Options")
        chunking_strategy = st.selectbox(
            "Strategy",
            ["fixed", "semantic", "sliding"],
            help="How to split the document into chunks"
        )
        
        if chunking_strategy == "fixed":
            chunk_size = st.number_input("Chunk Size", min_value=100, max_value=2000, value=512)
            chunk_overlap = st.number_input("Chunk Overlap", min_value=0, max_value=500, value=50)
        else:
            chunk_size = None
            chunk_overlap = None
    
    if uploaded_file is not None:
        file_details = {
            "Filename": uploaded_file.name,
            "File Type": uploaded_file.type,
            "File Size": f"{uploaded_file.size / 1024:.1f} KB"
        }
        
        st.markdown("### File Details")
        for key, value in file_details.items():
            st.write(f"**{key}:** {value}")
        
        if st.button("🚀 Upload and Process", type="primary", use_container_width=True):
            with st.spinner("Processing document..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {"chunking_strategy": chunking_strategy}
                    if chunk_size:
                        data["chunk_size"] = chunk_size
                    if chunk_overlap:
                        data["chunk_overlap"] = chunk_overlap
                    
                    response = requests.post(
                        f"{st.session_state.api_base_url}/ingest",
                        files=files,
                        params=data  # Use params instead of data for query parameters
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.markdown(f"""
                        <div class="success-message">
                            ✅ <strong>Success!</strong> Document uploaded successfully.<br>
                            <strong>Job ID:</strong> {result['job_id']}<br>
                            <strong>Document ID:</strong> {result['document_id']}<br>
                            <strong>Message:</strong> {result.get('message', 'Processing started')}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Show progress
                        progress_bar = st.progress(0)
                        for i in range(100):
                            time.sleep(0.02)
                            progress_bar.progress(i + 1)
                        st.success("Document processed and indexed!")
                    else:
                        st.error(f"Upload failed: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Tab 2: Search & Query
with tab2:
    st.header("Search & Query")
    st.markdown("Search through your documents and get AI-generated answers.")
    
    # Search input
    query = st.text_area(
        "Enter your question or search query",
        placeholder="e.g., What are the key features of the product?",
        height=100
    )
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        col1, col2, col3 = st.columns(3)
        with col1:
            use_rag = st.checkbox("Use RAG Generation", value=True)
            search_limit = st.slider("Number of Results", 1, 20, 5)
        with col2:
            similarity_threshold = st.slider("Similarity Threshold", 0.0, 1.0, 0.7, 0.05)
            search_type = st.selectbox("Search Type", ["hybrid", "vector", "keyword"], index=0)
        with col3:
            include_metadata = st.checkbox("Include Metadata", value=True)
            show_scores = st.checkbox("Show Similarity Scores", value=True)
    
    if st.button("🔍 Search", type="primary", use_container_width=True, disabled=not query):
        with st.spinner("Searching..."):
            try:
                payload = {
                    "query": query,
                    "generate_answer": use_rag,
                    "limit": search_limit,
                    "similarity_threshold": similarity_threshold,
                    "search_type": search_type
                }
                
                response = requests.post(
                    f"{st.session_state.api_base_url}/query",
                    json=payload
                )
                
                if response.status_code == 200:
                    results = response.json()
                    
                    # Show RAG answer if available
                    if use_rag and results.get("answer"):
                        st.markdown("### 🤖 AI-Generated Answer")
                        st.markdown(f"""
                        <div style="background: white; padding: 1.5rem; border-radius: 10px; 
                                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2rem;">
                            {results['answer']}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Show search results
                    st.markdown("### 📄 Source Documents")
                    if results.get("results"):
                        for i, result in enumerate(results["results"], 1):
                            with st.container():
                                col1, col2 = st.columns([4, 1])
                                with col1:
                                    st.markdown(f"""
                                    <div class="search-result">
                                        <h4 style="margin: 0; color: #667eea;">Result {i}</h4>
                                        <p style="margin: 0.5rem 0;">{result['text'][:300]}...</p>
                                        {f'<small style="color: #666;">Score: {result["score"]:.3f}</small>' if show_scores and "score" in result else ''}
                                    </div>
                                    """, unsafe_allow_html=True)
                                with col2:
                                    if include_metadata and result.get("metadata"):
                                        st.json(result["metadata"])
                    else:
                        st.info("No results found. Try adjusting your search parameters.")
                    
                    # Show processing time
                    if results.get("processing_time"):
                        st.caption(f"⏱️ Processing time: {results['processing_time']:.2f}s")
                        
                else:
                    st.error(f"Search failed: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Tab 3: Document Library
with tab3:
    st.header("Document Library")
    st.markdown("View and manage all uploaded documents.")
    
    # Refresh button
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
    
    try:
        response = requests.get(f"{st.session_state.api_base_url}/documents")
        if response.status_code == 200:
            docs_data = response.json()
            documents = docs_data.get("documents", [])
            
            if documents:
                # Display documents in a nice grid
                for doc in documents:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        
                        with col1:
                            st.markdown(f"**📄 {doc.get('filename', 'Unknown')}**")
                        with col2:
                            st.caption(f"Type: {doc.get('document_type', 'Unknown')}")
                        with col3:
                            # Convert timestamp to datetime
                            timestamp = doc.get('timestamp', 0)
                            if timestamp:
                                dt = datetime.fromtimestamp(timestamp)
                                st.caption(f"Uploaded: {dt.strftime('%Y-%m-%d %H:%M')}")
                        with col4:
                            if st.button("🗑️", key=f"delete_{doc['document_id']}", help="Delete document"):
                                try:
                                    del_response = requests.delete(
                                        f"{st.session_state.api_base_url}/documents/{doc['document_id']}"
                                    )
                                    if del_response.status_code == 200:
                                        st.success("Document deleted!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete document")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                        
                        # Show chunk count
                        if doc.get('chunk_count'):
                            st.caption(f"📊 Chunks: {doc['chunk_count']}")
                        
                        st.divider()
            else:
                st.info("No documents uploaded yet. Go to the Upload tab to add documents.")
                
        else:
            st.error(f"Failed to fetch documents: {response.status_code}")
    except Exception as e:
        st.error(f"Connection error: {str(e)}")

# Tab 4: Chat Interface
with tab4:
    st.header("Chat with your Documents")
    st.markdown("Have a conversation with your knowledge base using AI.")
    
    # Chat history
    chat_container = st.container()
    
    # Display chat history
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    payload = {
                        "query": prompt,
                        "generate_answer": True,
                        "limit": 5,
                        "similarity_threshold": 0.7,
                        "search_type": "hybrid"
                    }
                    
                    response = requests.post(
                        f"{st.session_state.api_base_url}/query",
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        results = response.json()
                        answer = results.get("answer", "I couldn't find relevant information to answer your question.")
                        
                        st.markdown(answer)
                        
                        # Add assistant response to chat history
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        
                        # Show sources in expander
                        if results.get("results"):
                            with st.expander("📚 View Sources"):
                                for i, result in enumerate(results["results"], 1):
                                    st.markdown(f"**Source {i}:** {result['text'][:200]}...")
                                    if result.get("metadata", {}).get("filename"):
                                        st.caption(f"From: {result['metadata']['filename']}")
                    else:
                        error_msg = "Sorry, I encountered an error while processing your request."
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                        
                except Exception as e:
                    error_msg = f"Connection error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>Built with ❤️ using FastAPI, Qdrant, and OpenAI | 
    <a href="https://github.com/anthropics/claude-code" style="color: #667eea;">View Documentation</a></p>
</div>
""", unsafe_allow_html=True)