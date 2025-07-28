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
if 'similarity_threshold' not in st.session_state:
    st.session_state.similarity_threshold = 0.4
if 'batch_job_id' not in st.session_state:
    st.session_state.batch_job_id = None
if 'batch_processing_delay' not in st.session_state:
    st.session_state.batch_processing_delay = 1.0

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
    
    # Similarity threshold configuration
    st.subheader("🎯 Search Settings")
    similarity_threshold = st.slider(
        "Default Similarity Threshold",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.similarity_threshold,
        step=0.05,
        help="Lower values return more results, higher values return only the most similar results"
    )
    if similarity_threshold != st.session_state.similarity_threshold:
        st.session_state.similarity_threshold = similarity_threshold
    
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📤 Upload Documents", "📦 Batch Upload", "🔍 Search & Query", "📚 Document Library", "💬 Chat Interface", "📊 System Logs", "⚡ Performance Profiling"])

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
            ["sliding_window", "semantic", "sentence"],
            help="How to split the document into chunks"
        )
        
        if chunking_strategy == "sliding_window":
            chunk_size = st.number_input("Chunk Size", min_value=100, max_value=2000, value=512, key="single_chunk_size")
            chunk_overlap = st.number_input("Chunk Overlap", min_value=0, max_value=500, value=50, key="single_chunk_overlap")
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

# Tab 2: Batch Upload
with tab2:
    st.header("Batch Upload")
    st.markdown("Upload multiple documents at once with progress tracking.")
    
    # Check if there's an ongoing job
    if st.session_state.batch_job_id:
        st.info(f"📊 Tracking Job: {st.session_state.batch_job_id}")
        
        # Poll job status
        try:
            response = requests.get(f"{st.session_state.api_base_url}/jobs/{st.session_state.batch_job_id}")
            if response.status_code == 200:
                job_data = response.json()
                
                # Progress metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Files", job_data['total'])
                with col2:
                    st.metric("Completed", job_data['completed'], delta=f"+{job_data['completed']}")
                with col3:
                    st.metric("Failed", job_data['failed'], delta=f"-{job_data['failed']}" if job_data['failed'] > 0 else None)
                
                # Progress bar
                progress = (job_data['completed'] + job_data['failed']) / job_data['total'] if job_data['total'] > 0 else 0
                st.progress(progress)
                
                # Current file
                if job_data['current_file']:
                    st.write(f"🔄 Processing: **{job_data['current_file']}**")
                
                # Document status table
                st.subheader("Document Status")
                doc_data = []
                for doc_id, doc_info in job_data['documents'].items():
                    status_icon = {
                        'completed': '✅',
                        'failed': '❌',
                        'processing': '🔄'
                    }.get(doc_info['status'], '⏳')
                    
                    doc_data.append({
                        'Status': status_icon,
                        'Filename': doc_info['filename'],
                        'Error': doc_info.get('error', '')
                    })
                
                if doc_data:
                    df = pd.DataFrame(doc_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Check if job is complete
                if job_data['status'] == 'completed':
                    st.success("✅ Batch processing completed!")
                    st.balloons()
                    if st.button("Process Another Batch"):
                        st.session_state.batch_job_id = None
                        st.rerun()
                else:
                    # Auto-refresh every 2 seconds
                    time.sleep(2)
                    st.rerun()
                    
            else:
                st.error("Failed to fetch job status")
                if st.button("Start New Batch"):
                    st.session_state.batch_job_id = None
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error: {str(e)}")
            if st.button("Start New Batch"):
                st.session_state.batch_job_id = None
                st.rerun()
    
    else:
        # File upload interface
        uploaded_files = st.file_uploader(
            "Choose files",
            type=['pdf', 'txt', 'json'],
            accept_multiple_files=True,
            help="Select multiple files (max 100 files)"
        )
        
        if uploaded_files:
            st.write(f"📁 Selected {len(uploaded_files)} files")
            
            # Show file list
            file_data = []
            total_size = 0
            for file in uploaded_files:
                file_size = file.size / 1024  # KB
                total_size += file_size
                file_data.append({
                    'Filename': file.name,
                    'Type': file.type or 'Unknown',
                    'Size': f"{file_size:.1f} KB"
                })
            
            df = pd.DataFrame(file_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.write(f"**Total size:** {total_size:.1f} KB")
            
            # Chunking options
            st.subheader("Processing Options")
            col1, col2, col3 = st.columns(3)
            with col1:
                chunking_strategy = st.selectbox(
                    "Chunking Strategy",
                    ["sliding_window", "semantic", "sentence"],
                    help="Strategy to split documents into chunks"
                )
            with col2:
                if chunking_strategy == "sliding_window":
                    chunk_size = st.number_input("Chunk Size", min_value=100, max_value=2000, value=512, key="batch_chunk_size")
                    chunk_overlap = st.number_input("Chunk Overlap", min_value=0, max_value=500, value=50, key="batch_chunk_overlap")
                else:
                    chunk_size = None
                    chunk_overlap = None
            with col3:
                processing_delay = st.slider(
                    "Processing Delay (seconds)",
                    min_value=0.0,
                    max_value=5.0,
                    value=st.session_state.batch_processing_delay,
                    step=0.5,
                    help="Artificial delay between documents for demo purposes"
                )
                st.session_state.batch_processing_delay = processing_delay
            
            # Upload button
            if st.button("🚀 Upload All Files", type="primary", use_container_width=True):
                with st.spinner("Starting batch upload..."):
                    try:
                        # Prepare files for upload
                        files = []
                        for uploaded_file in uploaded_files:
                            files.append(
                                ('files', (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type))
                            )
                        
                        # Prepare parameters
                        params = {
                            "chunking_strategy": chunking_strategy,
                            "processing_delay": processing_delay
                        }
                        if chunk_size:
                            params["chunk_size"] = chunk_size
                        if chunk_overlap:
                            params["chunk_overlap"] = chunk_overlap
                        
                        # Send request
                        response = requests.post(
                            f"{st.session_state.api_base_url}/batch-ingest",
                            files=files,
                            params=params
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.session_state.batch_job_id = result['job_id']
                            st.success(f"✅ Batch upload started! Job ID: {result['job_id']}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {response.text}")
                            
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

# Tab 3: Search & Query
with tab3:
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
            similarity_threshold = st.slider("Similarity Threshold", 0.0, 1.0, st.session_state.similarity_threshold, 0.05)
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

# Tab 4: Document Library
with tab4:
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

# Tab 5: Chat Interface
with tab5:
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
                        "search_type": "hybrid",
                        "similarity_threshold": st.session_state.similarity_threshold
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

# Tab 6: System Logs
with tab6:
    st.header("System Logs")
    st.markdown("View real-time system logs and trace requests by correlation ID.")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        correlation_id_filter = st.text_input(
            "Filter by Correlation ID",
            placeholder="e.g., a4f3e2d1-8b9c-4d5e-6f7a",
            help="Enter a correlation ID to trace a specific request"
        )
    with col2:
        log_level_filter = st.selectbox(
            "Filter by Level",
            ["All", "error", "warning", "info", "debug"],
            help="Filter logs by severity level"
        )
    with col3:
        log_limit = st.slider(
            "Number of Logs",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            help="Maximum number of logs to display"
        )
    
    # Auto-refresh option
    auto_refresh = st.checkbox("Auto-refresh (every 5 seconds)", value=False)
    
    # Refresh button
    if st.button("🔄 Refresh Logs", type="primary", use_container_width=True) or auto_refresh:
        try:
            # Build query parameters
            params = {"limit": log_limit}
            if correlation_id_filter:
                params["correlation_id"] = correlation_id_filter
            if log_level_filter != "All":
                params["level"] = log_level_filter
            
            # Fetch logs
            response = requests.get(f"{st.session_state.api_base_url}/logs", params=params)
            
            if response.status_code == 200:
                logs_data = response.json()
                logs = logs_data.get("logs", [])
                
                # Show filter info
                if logs_data.get("filtered_by"):
                    st.info(f"🔍 Filtered by: {logs_data['filtered_by']}")
                
                st.write(f"📋 Showing {len(logs)} of {logs_data['count']} logs")
                
                if logs:
                    # Create tabs for different views
                    view1, view2, view3 = st.tabs(["📋 Table View", "📜 Timeline View", "📊 Statistics"])
                    
                    with view1:
                        # Prepare data for table
                        table_data = []
                        for log in logs:
                            level = log.get("level", "info")
                            level_icon = {
                                "error": "🔴",
                                "warning": "🟡", 
                                "warn": "🟡",
                                "info": "🔵",
                                "debug": "⚪"
                            }.get(level.lower(), "⚪")
                            
                            table_data.append({
                                "Level": f"{level_icon} {level}",
                                "Timestamp": log.get("timestamp", ""),
                                "Event": log.get("event", log.get("msg", "")),
                                "Correlation ID": log.get("correlation_id", "")[:8] + "..." if log.get("correlation_id") else "",
                                "Details": str(log)[:100] + "..."
                            })
                        
                        df = pd.DataFrame(table_data)
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Details": st.column_config.TextColumn(
                                    "Details",
                                    help="Click to expand",
                                    max_chars=100
                                )
                            }
                        )
                        
                        # Expandable details
                        with st.expander("🔍 View Full Log Details"):
                            selected_index = st.number_input(
                                "Log Index (0-based)",
                                min_value=0,
                                max_value=len(logs)-1 if logs else 0,
                                value=0,
                                help="Enter the index of the log to view details"
                            )
                            if logs:
                                st.json(logs[selected_index])
                    
                    with view2:
                        # Timeline view
                        for i, log in enumerate(logs):
                            level = log.get("level", "info")
                            level_color = {
                                "error": "#ff4444",
                                "warning": "#ffaa00", 
                                "warn": "#ffaa00",
                                "info": "#4444ff",
                                "debug": "#888888"
                            }.get(level.lower(), "#888888")
                            
                            timestamp = log.get("timestamp", "")
                            event = log.get("event", log.get("msg", ""))
                            corr_id = log.get("correlation_id", "")
                            
                            st.markdown(f"""
                            <div style="border-left: 3px solid {level_color}; padding-left: 1rem; margin-bottom: 1rem;">
                                <small style="color: #666;">{timestamp}</small><br>
                                <strong>{event}</strong><br>
                                {f'<small>Correlation: {corr_id[:12]}...</small>' if corr_id else ''}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if i >= 20:  # Limit timeline view to 20 items
                                st.info(f"Showing first 20 of {len(logs)} logs. Use table view to see all.")
                                break
                    
                    with view3:
                        # Statistics
                        st.subheader("Log Statistics")
                        
                        # Level distribution
                        level_counts = {}
                        event_counts = {}
                        
                        for log in logs:
                            level = log.get("level", "unknown")
                            level_counts[level] = level_counts.get(level, 0) + 1
                            
                            event = log.get("event", "unknown")
                            event_counts[event] = event_counts.get(event, 0) + 1
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Log Levels:**")
                            for level, count in sorted(level_counts.items(), key=lambda x: x[1], reverse=True):
                                st.write(f"- {level}: {count}")
                        
                        with col2:
                            st.write("**Top Events:**")
                            for event, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                                st.write(f"- {event}: {count}")
                        
                        # Time range
                        if logs:
                            timestamps = [log.get("timestamp", "") for log in logs if log.get("timestamp")]
                            if timestamps:
                                st.write(f"**Time Range:**")
                                st.write(f"- First: {min(timestamps)}")
                                st.write(f"- Last: {max(timestamps)}")
                
                else:
                    st.info("No logs found matching the filters.")
            
            else:
                st.error(f"Failed to fetch logs: {response.text}")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(5)
        st.rerun()
    
    # Help section
    with st.expander("ℹ️ How to Use System Logs"):
        st.markdown("""
        ### Finding Correlation IDs
        1. When you make a request (upload, search, etc.), check the response headers
        2. Look for `X-Correlation-ID` in the browser's developer tools
        3. Or check the API response in the Network tab
        
        ### Log Levels
        - **🔴 Error**: Critical issues that need attention
        - **🟡 Warning**: Important notices but not critical
        - **🔵 Info**: General information about operations
        - **⚪ Debug**: Detailed debugging information
        
        ### Tips
        - Use correlation ID to trace a complete request flow
        - Filter by error level to quickly find issues
        - Enable auto-refresh to monitor real-time activity
        """)

# Tab 7: Performance Profiling
with tab7:
    st.header("Performance Profiling")
    st.markdown("Analyze system performance and identify bottlenecks from request logs.")
    
    # Refresh button
    if st.button("📊 Analyze Performance", type="primary", use_container_width=True):
        with st.spinner("Analyzing performance data..."):
            try:
                response = requests.get(f"{st.session_state.api_base_url}/profiling")
                
                if response.status_code == 200:
                    data = response.json()
                    stats = data['stats']
                    bottlenecks = data['bottlenecks']
                    
                    # Overall metrics
                    st.subheader("📈 Overall Performance Metrics")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Total Requests Analyzed",
                            stats['total_requests']
                        )
                    
                    if stats['duration_stats']:
                        with col2:
                            st.metric(
                                "Avg Request Time",
                                f"{stats['duration_stats']['avg']:.2f}s"
                            )
                        with col3:
                            st.metric(
                                "P95 Request Time",
                                f"{stats['duration_stats']['p95']:.2f}s"
                            )
                        with col4:
                            st.metric(
                                "Max Request Time",
                                f"{stats['duration_stats']['max']:.2f}s"
                            )
                    
                    # Bottleneck Analysis
                    if bottlenecks:
                        st.subheader("🔍 Bottleneck Analysis")
                        st.markdown("Operations sorted by average duration (slowest first):")
                        
                        # Create bottleneck visualization
                        bottleneck_data = []
                        for b in bottlenecks[:5]:  # Top 5 bottlenecks
                            phase_name = b['phase'].replace('_', ' ').title()
                            bottleneck_data.append({
                                'Operation': phase_name,
                                'Avg Duration (s)': f"{b['avg_duration']:.3f}",
                                'Max Duration (s)': f"{b['max_duration']:.3f}",
                                '% of Total': f"{b['percentage']:.1f}%"
                            })
                        
                        df_bottlenecks = pd.DataFrame(bottleneck_data)
                        st.dataframe(df_bottlenecks, use_container_width=True, hide_index=True)
                        
                        # Visual representation
                        if len(bottlenecks) > 0:
                            st.markdown("### Time Distribution")
                            for b in bottlenecks[:5]:
                                phase_name = b['phase'].replace('_', ' ').title()
                                percentage = b['percentage']
                                
                                # Create a progress bar visualization
                                progress_html = f"""
                                <div style="margin-bottom: 10px;">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                        <span>{phase_name}</span>
                                        <span>{b['avg_duration']:.3f}s ({percentage:.1f}%)</span>
                                    </div>
                                    <div style="background-color: #e0e0e0; border-radius: 5px; height: 20px;">
                                        <div style="background-color: {'#ff4444' if percentage > 50 else '#ffaa00' if percentage > 20 else '#4444ff'}; 
                                                    width: {percentage}%; height: 100%; border-radius: 5px;">
                                        </div>
                                    </div>
                                </div>
                                """
                                st.markdown(progress_html, unsafe_allow_html=True)
                    
                    # Phase Statistics
                    if stats['phase_stats']:
                        st.subheader("📊 Detailed Phase Statistics")
                        
                        phase_tabs = st.tabs(list(stats['phase_stats'].keys()))
                        
                        for idx, (phase, phase_stats) in enumerate(stats['phase_stats'].items()):
                            with phase_tabs[idx]:
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Average", f"{phase_stats['avg']:.3f}s")
                                with col2:
                                    st.metric("Minimum", f"{phase_stats['min']:.3f}s")
                                with col3:
                                    st.metric("Maximum", f"{phase_stats['max']:.3f}s")
                                with col4:
                                    st.metric("P50 (Median)", f"{phase_stats['p50']:.3f}s")
                    
                    # Recent Requests Timeline
                    if stats.get('recent_requests'):
                        st.subheader("📅 Recent Request Timeline")
                        st.markdown("Last 10 processed requests:")
                        
                        timeline_data = []
                        for req in stats['recent_requests']:
                            if req.get('total_duration'):
                                timeline_data.append({
                                    'Correlation ID': req['correlation_id'][:12] + '...',
                                    'Total Duration': f"{req['total_duration']:.2f}s",
                                    'Phases': len(req.get('phase_durations', {})),
                                    'Timestamp': req.get('start_time', 'N/A')
                                })
                        
                        if timeline_data:
                            df_timeline = pd.DataFrame(timeline_data)
                            st.dataframe(df_timeline, use_container_width=True, hide_index=True)
                    
                    # Recommendations
                    st.subheader("💡 Performance Recommendations")
                    if bottlenecks and bottlenecks[0]['phase'] == 'embeddings_generation':
                        st.info("""
                        **Embedding Generation is the primary bottleneck:**
                        - Consider using a faster embedding model
                        - Implement embedding caching for common text chunks
                        - Increase batch size for embedding requests
                        - Use local embedding models for better performance
                        """)
                    elif bottlenecks and bottlenecks[0]['phase'] == 'text_extraction':
                        st.info("""
                        **Text Extraction is slow:**
                        - Consider preprocessing PDFs in advance
                        - Use OCR optimization for scanned documents
                        - Implement parallel PDF processing
                        """)
                    elif stats['duration_stats'] and stats['duration_stats']['avg'] > 10:
                        st.warning("""
                        **Overall processing time is high:**
                        - Review your infrastructure resources
                        - Consider horizontal scaling
                        - Implement request queuing
                        """)
                    else:
                        st.success("System performance looks good! No major bottlenecks detected.")
                    
                else:
                    st.error(f"Failed to fetch profiling data: {response.text}")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Help section
    with st.expander("ℹ️ Understanding Performance Metrics"):
        st.markdown("""
        ### Metrics Explained
        
        **Request Time Metrics:**
        - **Average**: Mean processing time across all requests
        - **P95**: 95% of requests complete faster than this time
        - **Maximum**: Longest request processing time
        
        **Bottleneck Analysis:**
        - Shows which operations consume the most time
        - Percentage indicates proportion of total request time
        - Red bars (>50%) indicate critical bottlenecks
        
        **Phase Statistics:**
        - Detailed breakdown for each processing phase
        - P50 (median) is often more representative than average
        
        ### Common Bottlenecks
        1. **Embedding Generation**: Usually the slowest operation
        2. **Text Extraction**: Can be slow for large PDFs
        3. **Vector Storage**: May indicate database performance issues
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>Built with ❤️ using FastAPI, Qdrant, and OpenAI | 
    <a href="https://github.com/anthropics/claude-code" style="color: #667eea;">View Documentation</a></p>
</div>
""", unsafe_allow_html=True)