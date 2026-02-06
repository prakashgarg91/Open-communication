# Contributing to Vākya / Open Communication

नमस्ते! (Namaste!) Thank you for your interest in contributing to the Vākya protocol. 🙏

## How to Contribute

### Reporting Issues
- Use GitHub Issues to report bugs or request features
- Include reproduction steps, expected vs actual behavior
- Tag issues with appropriate labels

### Code Contributions

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/your-feature`
3. **Make changes** following the code style below
4. **Write tests** for new functionality
5. **Run tests**: `pytest tests/ -v`
6. **Lint**: `ruff check vakya/`
7. **Submit a Pull Request**

### Code Style

- Python 3.10+ with type hints
- Use `ruff` for formatting and linting
- Docstrings for all public classes and functions
- Sanskrit terms should be used consistently (see `docs/sanskrit-glossary.md`)
- Tests for all new features

### Areas Where Help is Needed

- **AI Adapters**: Add support for more AI providers (Google Gemini, Mistral, Cohere, etc.)
- **Language Bindings**: JavaScript/TypeScript, Go, Rust implementations
- **Documentation**: Tutorials, examples, translations
- **Testing**: More test coverage, integration tests
- **Protocol Design**: Proposals for protocol extensions (via Issues)
- **Security**: Encryption, authentication mechanisms
- **Performance**: Benchmarking, optimization

### Protocol Changes

For changes to the Vākya protocol specification:
1. Open an Issue describing the proposed change
2. Discuss with the community
3. Submit a PR to `docs/protocol-spec.md` with the changes
4. Update the reference implementation to match

## Development Setup

```bash
git clone https://github.com/prakashgarg91/Open-communication.git
cd Open-communication
pip install -e ".[dev,all]"
pytest tests/ -v
```

## Code of Conduct

Be respectful, inclusive, and constructive. We welcome contributors from all backgrounds.

---

*सर्वे भवन्तु सुखिनः, सर्वे सन्तु निरामयाः*
*May all be happy, may all be free from illness*
