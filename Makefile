PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
CC ?= cc

.PHONY: test lint format format-check check doctor install-dev build-hook build-calculator clean

install-dev:
	$(PYTHON) -m pip install -e '.[dev]'

check: lint format-check test build-hook

doctor:
	@missing=0; \
	if [ -x "$(PYTHON)" ] || command -v "$(PYTHON)" >/dev/null 2>&1; then \
		echo "OK   python: using $(PYTHON)"; \
	else \
		echo "FAIL python: $(PYTHON) was not found; create a venv and run 'make install-dev PYTHON=.venv/bin/python'"; \
		missing=1; \
	fi; \
	if $(PYTHON) -c "import pytest" >/dev/null 2>&1; then \
		echo "OK   pytest: importable"; \
	else \
		echo "FAIL pytest: missing; run 'make install-dev' inside your virtual environment"; \
		missing=1; \
	fi; \
	if $(PYTHON) -c "import ruff" >/dev/null 2>&1; then \
		echo "OK   ruff: importable"; \
	else \
		echo "FAIL ruff: missing; run 'make install-dev' inside your virtual environment"; \
		missing=1; \
	fi; \
	if command -v make >/dev/null 2>&1; then \
		echo "OK   make: found"; \
	else \
		echo "FAIL make: missing from PATH"; \
		missing=1; \
	fi; \
	if command -v $(firstword $(CC)) >/dev/null 2>&1; then \
		echo "OK   cc: found $(CC)"; \
	else \
		echo "FAIL cc: $(CC) missing from PATH"; \
		missing=1; \
	fi; \
	if printf '#include <X11/Intrinsic.h>\n#include <X11/CoreP.h>\n' | $(CC) $(CFLAGS) -E -x c - >/dev/null 2>&1; then \
		echo "OK   X11/Xt headers: available"; \
	else \
		echo "FAIL X11/Xt headers: missing; install libxt-dev and libx11-dev or your platform equivalents"; \
		missing=1; \
	fi; \
	if command -v xdotool >/dev/null 2>&1; then \
		echo "OK   xdotool: found"; \
	else \
		echo "WARN xdotool: optional for fast checks; required for GUI replay"; \
	fi; \
	if command -v cnee >/dev/null 2>&1; then \
		echo "OK   cnee: found"; \
	else \
		echo "WARN cnee: optional for fast checks; required for recording"; \
	fi; \
	if command -v docker >/dev/null 2>&1 || command -v podman >/dev/null 2>&1; then \
		echo "OK   container runtime: docker or podman found"; \
	else \
		echo "WARN container runtime: optional for fast checks; required for local live-loop validation"; \
	fi; \
	exit $$missing

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
