.PHONY: run install lint format test clean

# Executa o jogo
run:
	@PYTHONPATH=src python3 -m game.main

# Instala o pacote no modo desenvolvimento
install:
	pip install -e .[dev]

# Verifica formatação, tipos e lint
lint:
	ruff check src tests
	black --check src tests
	pyright

# Formata o código
format:
	black src tests
	ruff --fix src tests

# Roda testes (pytest se disponível, senão unittest da stdlib)
test:
	@if python3 -c "import pytest" 2>/dev/null; then \
		PYTHONPATH=src python3 -m pytest tests -q; \
	else \
		PYTHONPATH=src python3 -m unittest discover -s tests -t . -v; \
	fi

# Limpa arquivos inúteis
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .mypy_cache .ruff_cache .pyright .coverage dist build *.egg-info
