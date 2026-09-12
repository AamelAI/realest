.PHONY: dev tunnel web seed check install help

help:
	@grep -E '^[a-z]+:' Makefile | grep -v '^\.PHONY' | sed 's/:.*//' | sed 's/^/  make /'

install:            ## one-time: python deps + web deps
	uv sync
	cd web && npm install

dev:                ## FastAPI on :8000
	uv run uvicorn main:app --reload --port 8000 --app-dir server

tunnel:             ## public URL the voice provider can reach
	ngrok http 8000

web:                ## Next.js on :3000
	cd web && npm run dev

seed:               ## validate + write data/listings.json
	uv run python scripts/seed.py

check:              ## validate listings without writing
	uv run python scripts/seed.py --check
