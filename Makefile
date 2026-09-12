.PHONY: dev tunnel web seed check listings preview bridge spike tools install doctor help

help:
	@grep -E '^[a-z]+:' Makefile | grep -v '^\.PHONY' | sed 's/:.*//' | sed 's/^/  make /'

install:            ## one-time: python deps + web deps
	uv sync
	cd web && npm install

dev:                ## FastAPI on :8000
	uv run uvicorn main:app --reload --port 8000 --app-dir server

tunnel:             ## public URL Twilio can reach (uses NGROK_DOMAIN from .env)
	@D=$$(grep -E '^NGROK_DOMAIN=' .env 2>/dev/null | cut -d= -f2- | tr -d ' '); \
	if [ -n "$$D" ]; then echo "→ static: https://$$D"; ngrok http --url=$$D 8000; \
	else echo "! NGROK_DOMAIN not set in .env — using a RANDOM url that dies on restart."; \
	     echo "  Claim your free static domain: https://dashboard.ngrok.com/domains"; \
	     ngrok http 8000; fi

web:                ## Next.js on :3000
	cd web && npm run dev

deploy:             ## push the page to Vercel (free Hobby tier)
	cd web && npx vercel --prod

listings:           ## rebuild listings from the raw scrape: make listings PHONE=+1416... EMAIL=you@x.com
	uv run python scripts/scrape_rentals.py --phone "$(PHONE)" --email "$(EMAIL)"

bridge:             ## Twilio <-> OpenAI Realtime audio bridge (terminal 1)
	uv run python scripts/spike_bridge.py

spike:              ## place one test call: make spike TO=+14165551234 [ROLE=renter]
	uv run python scripts/spike_call.py --to "$(TO)" $(if $(ROLE),--role $(ROLE),)

preview:            ## QA page: every listing + link to the real rentals.ca page
	uv run python scripts/preview.py && open data/preview.html

seed:               ## validate + write data/listings.json
	uv run python scripts/seed.py

check:              ## validate listings without writing
	uv run python scripts/seed.py --check

doctor:             ## is this machine ready to build?
	uv run python scripts/doctor.py
