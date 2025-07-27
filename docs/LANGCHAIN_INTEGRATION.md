# LangChain Integration for Document Chunking

## Overview

We've refactored the document chunking implementation to use LangChain's text splitters instead of custom implementations. This provides several benefits and aligns with industry best practices.

## Why LangChain?

### 1. **Battle-Tested Implementation**
- LangChain's text splitters are used in production by thousands of companies
- Edge cases and bugs have been discovered and fixed by the community
- Regular updates and improvements from a dedicated team

### 2. **Better Token Handling**
- The `TokenTextSplitter` uses the same tokenizer as OpenAI models
- This ensures chunks fit within model context windows
- Prevents token boundary issues that can corrupt embeddings

### 3. **Smarter Semantic Splitting**
- `RecursiveCharacterTextSplitter` respects document structure
- Tries multiple separators in order: paragraphs → sentences → words
- Maintains context better than naive splitting

### 4. **Less Code to Maintain**
- Reduced our chunking.py from 222 lines to 189 lines
- Removed complex regex patterns and edge case handling
- Focus on business logic instead of text processing details

## Implementation Details

### Fixed-Size Chunking
```python
self.splitter = CharacterTextSplitter(
    chunk_size=self.chunk_size,
    chunk_overlap=self.overlap,
    length_function=len,
    separator="",  # No separator for true fixed-size
    strip_whitespace=False
)
```

### Semantic Chunking
```python
self.splitter = RecursiveCharacterTextSplitter(
    chunk_size=self.max_chunk_size,
    chunk_overlap=50,  # Small overlap for context
    length_function=len,
    separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
    keep_separator=True
)
```

### Sliding Window (Token-Based)
```python
self.splitter = TokenTextSplitter(
    chunk_size=self.window_size,
    chunk_overlap=overlap,
    model_name="gpt-3.5-turbo"  # Same tokenizer as our LLM
)
```

## Benefits Realized

1. **Improved Accuracy**: Token-aware splitting ensures chunks work well with OpenAI embeddings
2. **Better Performance**: LangChain's optimized implementations are faster
3. **Easier Maintenance**: Updates come from `pip install --upgrade`
4. **More Features**: Easy to add new splitting strategies (Markdown, Code, etc.)

## Future Enhancements

With LangChain, we can easily add:
- `MarkdownTextSplitter` for markdown documents
- `PythonCodeTextSplitter` for code files
- `HTMLHeaderTextSplitter` for web content
- Custom splitters for domain-specific formats

## Trade-offs

- **Additional Dependency**: LangChain adds ~50MB to the installation
- **Less Control**: We rely on LangChain's implementation choices
- **Version Management**: Need to track LangChain updates

Overall, the benefits far outweigh the trade-offs for a production RAG system.