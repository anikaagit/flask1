.PHONY: help install run run-bg stop status lint fmt test db-init

help:
	@echo "Targets:"
	@echo "  make install   - Install Python deps into venv (creates venv if missing)"
	@echo "  make run       - Run server in foreground (python3 main.py)"
	@echo "  make run-bg    - Run server in background (nohup -> /tmp/flask1_server.log)"
	@echo "  make stop      - Stop background server (if running)"
	@echo "  make status    - Show background server status + tail logs"
	@echo "  make db-init   - Initialize DB via scripts/db_init.py"
	@echo "  make lint      - Syntax check key modules"
	@echo "  make fmt       - (No-op) Placeholder for formatter"
	@echo "  make test      - Run pytest (if installed)"

venv/bin/activate:
	python3 -m venv venv
	venv/bin/python -m pip install --upgrade pip

install: venv/bin/activate
	venv/bin/python -m pip install -r requirements.txt
	@if [ -f requirements-dev.txt ]; then venv/bin/python -m pip install -r requirements-dev.txt; fi

run: install
	venv/bin/python main.py

run-bg: install
	@mkdir -p /tmp
	@nohup venv/bin/python main.py >/tmp/flask1_server.log 2>&1 & echo $$! >/tmp/flask1_server.pid
	@echo "Started server PID $$(cat /tmp/flask1_server.pid)"

stop:
	@if [ -f /tmp/flask1_server.pid ]; then \
		kill $$(cat /tmp/flask1_server.pid) 2>/dev/null || true; \
		rm -f /tmp/flask1_server.pid; \
		echo "Stopped"; \
	else \
		echo "No /tmp/flask1_server.pid found"; \
	fi

status:
	@if [ -f /tmp/flask1_server.pid ]; then \
		PID=$$(cat /tmp/flask1_server.pid); \
		ps -p $$PID -o pid,cmd || true; \
		tail -n 30 /tmp/flask1_server.log 2>/dev/null || true; \
	else \
		echo "No background server PID file"; \
	fi

lint: install
	venv/bin/python -m py_compile main.py api/game_api.py api/npc_api.py api/quiz_api.py api/analytics.py model/npc.py model/question.py model/game_session.py model/player_interaction.py

fmt:
	@echo "No formatter configured."

test: install
	@set -e; \
	venv/bin/python -m pytest -q || rc=$$?; \
	if [ "$$rc" = "5" ]; then echo "No tests collected (ok)."; exit 0; fi; \
	exit $$rc

db-init: install
	venv/bin/python scripts/db_init.py
