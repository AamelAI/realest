.PHONY: dev tunnel web seed check listings preview spike tools install doctor help

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

listings:           ## rebuild listings from the raw scrape: make listings PHONE=+1416... EMAIL=you@x.com
	uv run python scripts/scrape_rentals.py --phone "$(PHONE)" --email "$(EMAIL)"

spike:              ## place one test call: make spike TO=+14165551234
	uv run python scripts/spike_call.py --to "$(TO)"

tools:              ## rewrite agent/tools.json webhook URLs: make tools URL=https://x.ngrok.app
	@python3 -c "import pathlib,sys,re; p=pathlib.Path('agent/tools.json'); t=p.read_text(); \
u='$(URL)'.rstrip('/'); n=re.sub(r'https?://[^/\"]*(?=/agent/)|REPLACE_WITH_NGROK', u, t); \
p.write_text(n); print('✓ agent/tools.json now points at', u)"
	@echo "  → re-sync tools in the provider dashboard, then place a fresh test call"

preview:            ## QA page: every listing + link to the real rentals.ca page
	uv run python scripts/preview.py && open data/preview.html

seed:               ## validate + write data/listings.json
	uv run python scripts/seed.py

check:              ## validate listings without writing
	uv run python scripts/seed.py --check

doctor:             ## is this machine ready to build?
	uv run python scripts/doctor.py
