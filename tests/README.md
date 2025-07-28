# RAG System Tests

This directory contains the test suite for the RAG system. The tests are organized by module and aim to provide comprehensive coverage of the codebase.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py         # Pytest configuration and fixtures
├── test_api.py         # API endpoint tests
├── test_chunking.py    # Document chunking tests
├── test_config.py      # Configuration tests
├── test_embeddings.py  # Embedding generation tests
├── test_job_tracker.py # Job tracking tests
├── test_monitoring.py  # Monitoring/logging tests
├── test_validation.py  # Validation tests
└── test_vector_db.py   # Vector database tests
```

## Running Tests

To run all tests with coverage:
```bash
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```

To run specific test files:
```bash
pytest tests/test_api.py -v
```

## Test Features

- **Retry Mechanism**: OpenAI API calls have automatic retry with exponential backoff
- **Mocking**: External dependencies (Redis, Qdrant, OpenAI) are mocked for unit tests
- **Fixtures**: Common test data and mock objects are provided via pytest fixtures
- **Coverage**: Target is 80% code coverage across all modules

## Notes

- The `react_agent.py` module is excluded from coverage as it's experimental
- Integration tests requiring actual services should be marked with `@pytest.mark.integration`
- Tests use environment variable mocking to avoid requiring actual API keys