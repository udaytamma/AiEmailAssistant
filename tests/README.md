# Email Assistant Testing Suite

Comprehensive testing infrastructure for the Email Assistant application with integration, unit, and contract tests.

## Overview

This testing suite ensures the Email Assistant works correctly across all components:

- **Integration Tests**: End-to-end workflows (fetch → categorize → cache → digest)
- **Unit Tests**: Individual components (cache, email utils, display utils)
- **Contract Tests**: External API interactions (Gmail, Gemini)

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test utilities
├── pytest.ini               # Pytest configuration (in project root)
├── fixtures/                # Test data
│   ├── sample_emails.json   # Real emails from digest (no PII)
│   ├── categorized_emails.json
│   └── gemini_responses.json
├── integration/             # Integration tests
│   └── test_email_flow.py
└── unit/                    # Unit tests
    ├── test_cache_manager.py
    ├── test_email_utils.py
    ├── test_display_utils.py
    └── test_api_contracts.py
```

## Running Tests

### Install Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run Test Suites

**Basic Tests** (Fast, most critical - ~10-20 seconds):
```bash
python run_tests.py basic
```

**Extended Tests** (Moderate coverage - ~30-45 seconds):
```bash
python run_tests.py extended
```

**Comprehensive Tests** (Full coverage - ~1-2 minutes):
```bash
python run_tests.py comprehensive
```

### Run with pytest directly

```bash
# Run all tests
pytest -v

# Run only basic tests
pytest -v -m basic

# Run basic + extended
pytest -v -m "basic or extended"

# Run with coverage report
pytest -v --cov=src --cov-report=html
```

## Test Markers

Tests are marked for categorization:

- `@pytest.mark.basic` - Most critical tests (run these first)
- `@pytest.mark.extended` - Additional health checks
- `@pytest.mark.comprehensive` - Full test suite
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.contract` - API contract tests

## Web Interface

View and run tests from the web interface:

1. Start the web server:
   ```bash
   python src/web/server.py
   ```

2. Navigate to: http://localhost:8001/tests

3. Click buttons to run test suites and view results

## Test Coverage

Current coverage targets:

- **Overall**: 70% minimum (enforced by pytest)
- **Cache Manager**: High coverage (LRU, expiry, timestamps)
- **Email Utils**: High coverage (fetching, timestamp conversion)
- **Display Utils**: Moderate coverage (digest generation, grouping)

View coverage report:
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## Key Test Scenarios

### Integration Tests

1. **Complete E2E Flow**: Fetch → Categorize → Cache → Digest
2. **Incremental Fetching**: Only process new emails
3. **Cache Expiry**: Auto-cleanup of old entries
4. **API Failure Handling**: Graceful fallbacks

### Unit Tests

**Cache Manager**:
- Get/Set/Has operations
- LRU eviction (oldest removed when full)
- Timestamp tracking for incremental fetching
- Metadata persistence

**Email Utils**:
- Email fetching from Gmail API
- Timestamp conversion to Gmail epoch format
- Query building with filters

**Display Utils**:
- Digest structure generation
- Category grouping (Need-Action, FYI, etc.)
- Summary regeneration logic

### Contract Tests

**Gemini API**:
- Categorization response parsing
- Markdown fence stripping (```json removal)
- Error handling (invalid JSON, API failures)

**Gmail API**:
- Message list response structure
- Message get response structure
- Query format validation

## Fixtures

### Shared Fixtures (conftest.py)

- `sample_emails` - Real emails from digest
- `sample_categorized_emails` - Emails with AI categorization
- `mock_gemini_model` - Mock Gemini responses
- `mock_gmail_service` - Mock Gmail API
- `test_cache_manager` - Cache with temp storage
- `frozen_time` - Fixed datetime for testing

### Helper Functions

```python
# Create test email
email = pytest.create_test_email(
    email_id="test_123",
    from_addr="test@example.com",
    subject="Test Subject"
)

# Create categorized email
categorized = pytest.create_test_categorized_email(
    email_id="test_123",
    category="FYI",
    summary="Test summary"
)
```

## Continuous Integration

For CI/CD integration:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    pip install -r requirements-dev.txt
    python run_tests.py comprehensive
```

## Troubleshooting

**Tests fail with import errors**:
- Ensure you're running from project root
- Activate virtual environment: `source .venv/bin/activate`

**Freezegun import errors**:
- Install dev dependencies: `pip install -r requirements-dev.txt`

**Cache tests fail**:
- Check file permissions in `/tmp` directory
- Ensure cache directory is writable

**Integration tests timeout**:
- Increase timeout in `pytest.ini`: `--timeout=60`

## Best Practices

1. **Run Basic tests first** - Quick validation before commits
2. **Run Comprehensive before PR** - Full validation
3. **Keep fixtures updated** - Use real digest emails
4. **Add comments to tests** - Explain what's being tested
5. **Test edge cases** - Empty lists, invalid data, API failures

## Future Enhancements

- [ ] Performance benchmarking tests
- [ ] Load testing for concurrent email processing
- [ ] Mutation testing for test quality validation
- [ ] Integration with CI/CD pipeline
- [ ] Automated nightly test runs

---

**Questions?** Check the main README or open an issue.
