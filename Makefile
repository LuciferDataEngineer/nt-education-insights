PYTHONPATH := src
export PYTHONPATH

.PHONY: all transform quality analysis static test lint dashboard

all:
	python -m ntedu.cli all

transform:
	python -m ntedu.cli transform

quality:
	python -m ntedu.cli quality

analysis:
	python -m ntedu.cli analysis

static:
	python -m ntedu.cli static

test:
	pytest

lint:
	ruff check src tests dashboard

dashboard:
	streamlit run dashboard/app.py --server.port 8765 --server.address 127.0.0.1
