# Contributing to todo-bridge

Thank you for your interest in contributing to todo-bridge! This document provides guidelines for contributing to the project.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/todo-bridge.git
   cd todo-bridge
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/todo_converter

# Run type checking
mypy src/

# Run linting
ruff check src/ tests/

# Format code
ruff format src/ tests/
```

## 📁 Project Structure

```
todo-bridge/
├── src/todo_converter/      # Main package
│   ├── __init__.py         # Package initialization
│   ├── __main__.py         # CLI entry point
│   ├── base.py             # Abstract base converter
│   ├── csv_converter.py    # CSV format converter
│   ├── markdown_converter.py # Markdown format converter
│   ├── converter.py        # Main converter interface
│   └── models.py           # Data models
├── tests/                  # Test suite
├── demo_tasks.csv          # CSV demo file
├── demo_tasks.md           # Markdown demo file

└── README.md               # Project documentation
```

## 💻 Development Guidelines

### Code Style
- **Python 3.8+** compatibility
- **Type hints** required for all functions
- **Docstrings** required for all public methods (PEP 257)
- **Line length**: 88 characters (Black default)
- **Import sorting**: Use isort/ruff

### Testing
- **pytest** for all tests
- **Comprehensive coverage** for new features
- **Test file naming**: `test_*.py`
- **Test method naming**: `test_*`

### Commit Messages
Use conventional commit format:
```
type(scope): description

feat(csv): add support for time estimates in decimal format
fix(markdown): handle nested tasks with mixed indentation
docs(readme): update installation instructions
test(csv): add test for malformed CSV files
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `style`, `chore`

## 🔧 Adding New Features

### Adding a New Input Format

1. **Create converter class** in `src/todo_converter/`:
   ```python
   from .base import BaseConverter
   
   class NewFormatConverter(BaseConverter):
       def parse(self) -> None:
           # Implementation here
           pass
   ```

2. **Add to supported formats** in `converter.py`:
   ```python
   SUPPORTED_FORMATS = {
       ".csv": CSVConverter,
       ".md": MarkdownConverter,
       ".new": NewFormatConverter,  # Add this
   }
   ```

3. **Write comprehensive tests** in `tests/test_new_format_converter.py`

4. **Update documentation** in README.md

### Adding New Super Productivity Features

1. **Update models** in `models.py` if needed
2. **Modify base converter** in `base.py` for common functionality
3. **Update specific converters** as needed
4. **Add tests** for the new feature
5. **Update demo files** to showcase the feature

## 🐛 Bug Reports

When reporting bugs, please include:

- **Python version** and operating system
- **Input file format** and sample data (if possible)
- **Expected vs actual behavior**
- **Full error message** and stack trace
- **Steps to reproduce**

## 💡 Feature Requests

For new features, please describe:

- **Use case** and motivation
- **Proposed solution** or implementation
- **Alternative solutions** considered
- **Impact on existing functionality**

## 📋 Pull Request Process

1. **Create feature branch**: `git checkout -b feature/your-feature-name`
2. **Make changes** following the guidelines above
3. **Add tests** for new functionality
4. **Update documentation** if needed
5. **Run full test suite**: `pytest && mypy src/ && ruff check`
6. **Commit with conventional format**
7. **Push to your fork** and create pull request
8. **Fill out PR template** with details

### PR Checklist
- [ ] Tests pass (`pytest`)
- [ ] Type checking passes (`mypy src/`)
- [ ] Linting passes (`ruff check`)
- [ ] Documentation updated
- [ ] Demo files updated (if applicable)
- [ ] Conventional commit messages
- [ ] PR description explains changes

## 🎯 Areas for Contribution

We welcome contributions in these areas:

### High Priority
- **New input formats** (JSON, XML, YAML, etc.)
- **Enhanced time parsing** (more flexible formats)
- **Better error handling** and user feedback
- **Performance optimizations** for large files

### Medium Priority
- **Additional Super Productivity features** (custom fields, etc.)
- **Configuration options** (custom mappings, etc.)
- **Better CLI interface** (progress bars, etc.)
- **Documentation improvements**

### Low Priority
- **GUI interface** (desktop app)
- **Web interface** (online converter)
- **API endpoints** (REST API)
- **Plugins system**

## 🆘 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and ideas
- **Code Review**: We provide thorough code reviews

## 📜 Code of Conduct

Please be respectful and inclusive in all interactions. We follow the standard open source community guidelines for respectful collaboration.
