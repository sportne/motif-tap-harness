PYTHON ?= python3

.PHONY: test lint format format-check install-dev build-hook clean

install-dev:
	$(PYTHON) -m pip install -e '.[dev]'

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff check --select I --fix .
	$(PYTHON) -m ruff format .

format-check:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

build-hook:
	$(MAKE) -C c

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	$(MAKE) -C c clean
