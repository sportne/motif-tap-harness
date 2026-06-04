PYTHON ?= python3

.PHONY: test lint format format-check install-dev build-hook build-calculator clean

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

build-calculator:
	$(MAKE) -C examples/motif_calc

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	$(MAKE) -C c clean
	$(MAKE) -C examples/motif_calc clean
