# Contributing to DR Setup Guide

Thank you for your interest in contributing to the DR Setup Guide! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Commit Messages](#commit-messages)

## Code of Conduct

Please be respectful and professional in all interactions. We are committed to providing a welcoming and inclusive environment.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/dr-setup-guide.git
   cd dr-setup-guide
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ssenapathy-wam/dr-setup-guide.git
   ```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip and virtualenv
- Git

### Initial Setup

```bash
# Create virtual environment
make venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
make install-dev

# Setup environment file
make setup-env
# Edit .env with your local configuration
```

### Verify Setup

```bash
# Run tests
make test

# Run linting
make lint
```

## Coding Standards

### Style Guide

- Follow **PEP 8** guidelines
- Use **Black** for code formatting (line length: 100)
- Use **type hints** where possible
- Write **docstrings** for all public functions and classes

### Python Style

```python
#!/usr/bin/env python3
"""Module docstring."""

from typing import Optional, Dict, List

def function_name(param1: str, param2: int) -> Optional[str]:
    """
    Brief description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When something is wrong
    """
    pass
```

### File Organization

- Imports at the top (standard library, third-party, local)
- Docstrings for modules and public functions
- Type hints for parameters and returns
- Consistent naming (snake_case for functions/variables, PascalCase for classes)

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test file
pytest tests/test_module.py -v

# Run specific test
pytest tests/test_module.py::TestClass::test_method -v
```

### Writing Tests

```python
"""Test module."""

import pytest
from unittest.mock import Mock, patch
from module_under_test import function_to_test

class TestFunctionToTest:
    """Test class for function_to_test."""
    
    def test_success_case(self):
        """Test successful execution."""
        result = function_to_test("input")
        assert result == "expected"
    
    def test_error_case(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            function_to_test(invalid_input)
    
    @patch('module.external_call')
    def test_with_mock(self, mock_call):
        """Test with mocked external dependency."""
        mock_call.return_value = "mocked"
        result = function_to_test()
        assert result == "expected"
```

### Test Coverage

- Aim for 80%+ coverage
- Test both happy paths and error cases
- Use fixtures for common setup

## Submitting Changes

### Create a Branch

```bash
# Update from upstream
git fetch upstream
git rebase upstream/main

# Create feature branch
git checkout -b feature/description-of-feature
# or
git checkout -b fix/description-of-fix
```

### Commit and Push

```bash
# Format and lint code
make format
make lint

# Run tests
make test

# Commit changes
git add .
git commit -m "Meaningful commit message"

# Push to your fork
git push origin feature/description-of-feature
```

### Create Pull Request

1. Go to GitHub and create a pull request
2. Provide clear title and description
3. Reference related issues (e.g., "Fixes #123")
4. Ensure CI checks pass

## Commit Messages

### Format

```
<type>: <subject>

<body>

<footer>
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring without feature/fix changes
- `test`: Adding or updating tests
- `chore`: Build process, dependencies, tooling

### Examples

```
feat: add cluster link validation

- Implement health checks for cluster links
- Add retry logic for failed validations
- Add logging for debugging

Closes #123
```

```
fix: resolve null pointer exception in executor

The command executor was not properly handling null output
from failed commands, causing crashes.

Fixes #456
```

## Pull Request Review

- Be open to feedback
- Respond to review comments promptly
- Make requested changes in a new commit
- Request re-review after changes

## Questions or Issues?

- Open a GitHub issue for bugs or feature requests
- Reach out to maintainers for questions
- Check existing issues and discussions first

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).

Thank you for contributing! 🎉
