PY?=python3

.PHONY: setup dev lint test build

setup:
	$(PY) -m pip install -r requirements.txt

dev:
	$(PY) -m src.main

lint:
	$(PY) -m compileall -q src

test:
	@echo "No tests yet"

build:
	zip -r dist.zip src docs AGENTS.md || true

.PHONY: assets
assets:
	$(PY) scripts/select_assets.py --player $(player) --melee $(melee) --ranger $(ranger)
