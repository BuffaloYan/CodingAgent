.PHONY: venv install install-dev update-deps setup-browser test run lint fmt help browser-start browser-stop browser-status

VENV    := .venv
PYTHON  := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip

help:
	@echo "Usage:"
	@echo "  make venv         Create .venv (run once)"
	@echo "  make install      Install exact pinned deps from requirements.txt"
	@echo "  make install-dev  Fresh install + regenerate requirements.txt"
	@echo "  make update-deps  Upgrade all deps and regenerate requirements.txt"
	@echo "  make test         Run all tests"
	@echo "  make run          Start the Gradio app"
	@echo "  make lint         Lint with ruff"
	@echo "  make fmt          Format with ruff"

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	@echo "✅ venv created at $(VENV)/"

venv: $(VENV)/bin/activate

# ── Normal install: fast, uses pinned requirements.txt ─────────────────
install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# ── Install Playwright browser binaries ─────────────────────────────────
setup-browser: venv
	$(VENV)/bin/playwright install chromium
	@echo "✅ Chromium installed for headless browser tools"

# ── Dev install: installs from pyproject.toml then locks versions ───────
install-dev: venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	$(PIP) freeze > requirements.txt
	@echo "✅ requirements.txt updated ($(shell wc -l < requirements.txt | tr -d ' ') packages)"

# ── Upgrade all deps to latest and re-lock ──────────────────────────────
update-deps: venv
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -e ".[dev]"
	$(PIP) freeze > requirements.txt
	@echo "✅ requirements.txt updated ($(shell wc -l < requirements.txt | tr -d ' ') packages)"

test: venv
	$(VENV)/bin/pytest tests/ -v

run: venv
	$(PYTHON) -m ui.app

lint: venv
	$(VENV)/bin/ruff check .

fmt: venv
	$(VENV)/bin/ruff format .
	$(VENV)/bin/ruff check . --fix

# ── Docker Browser ──────────────────────────────────────────────────────
browser-start: ## Pull image & start browser container
	@docker rm -f agent-browser 2>/dev/null || true
	docker pull jlesage/firefox
	docker run -d --name agent-browser --shm-size=512m -p 5800:5800 jlesage/firefox
	@echo "✅ Browser running at http://localhost:5800"

browser-stop: ## Stop & remove browser container
	docker stop agent-browser && docker rm agent-browser
	@echo "✅ Browser container stopped and removed"

browser-status: ## Show container status
	@docker inspect --format '{{.State.Status}}' agent-browser 2>/dev/null || echo "not created"

