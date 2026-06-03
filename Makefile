PYTHON ?= python3

.PHONY: test install-dev build-hook clean

install-dev:
	$(PYTHON) -m pip install -e '.[dev]'

test:
	$(PYTHON) -m pytest

build-hook:
	$(MAKE) -C c

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	$(MAKE) -C c clean
