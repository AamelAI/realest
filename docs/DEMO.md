# The four demo listings — task `0.8`

Picked from the seeded Toronto rentals. **All four are real rows in
`data/listings.json`** — real addresses, real rents, the listings' own photos.
Nothing was fabricated or substituted to make the script work.

## The brief the caller speaks

> "Two bedroom, Yorkville or the Annex, under thirty-four hundred. I've got a dog."

`beds=2 · areas=[Yorkville, The Annex] · max_rent=3400 · pets=dog`

**Do not mention parking in the opening brief.** It is the lever for the reorder.

## The reorder beat

Mid-call the caller says:

> "Actually — parking matters more than anything."

`parking=true · priority_order=["parking"]` → **all 4 cards change position.**

| | before | after |
|---|---|---|
| 1 | L092 $3,000 | L095 $3,290 |
| 2 | L095 $3,290 | L086 $2,690 |
| 3 | L086 $2,690 | L100 $2,290 |
| 4 | L100 $2,290 | L092 $3,000 |

## The four, and what each call reveals

| id | address | listed | role on camera |
|---|---|---|---|
| `L092` | 155 Yorkville Avenue | $3,000 | **DEAD** — "leased Tuesday." Opens at #1, ends at #4 |
| `L095` | 322 Dupont Street, The Annex | $3,290 | **PRICE WRONG** — parking is $180 on top → **$3,470**, over budget |
| `L086` | 155 Yorkville Avenue | $2,690 | **BOOKED** — available, Saturday 2:00pm. *Cats only, and the caller has a dog* |
| `L100` | 660 Huron Street, The Annex | $2,290 | **NO ANSWER** — email drafted, shown on the card with Send |

### Final order after the calls

`L086 (booked) · L100 (no answer) · L095 ($3,470, over) · L092 (dead)`

The card that opened at #1 dies and drops to last. That is the shot.

## Why these four

- **Every photo is a real interior or building shot.** 33 of the seeded listings
  carry 16:9 property-manager ad graphics as their first photo — "Two Months Rent
  Free", "½ Month Free" stickers. All four here are clear of that. `L086` uses its
  own second photo, because the feed's first is the building exterior.
- **Rents are plausible for the neighbourhood.** The feed mixes room shares in
  with whole units; `MIN_RENT` in `scripts/scrape_rentals.py` now drops them, so
  no $1,050 three-bath "apartment" floats to the top of a shortlist.
- **The Annex scores as a neighbour of Yorkville**, not an exact match, so the
  card shows its real neighbourhood and still ranks honestly.

## Demo listing-agent number

Every seeded row (and any number the caller speaks) dials **`+1+111111111111`**.
The outbound call uses the **Listing** ElevenLabs agent (`ELEVENLABS_LISTING_AGENT_ID`),
not the renter. Say *"call the shortlist"* or *"call 437-555-0100"* — `start_calls`
treats that number as the listing agent for the current cards.

Rebuild the catalogue with:

```
make listings PHONE=+1+111111111111 EMAIL=you@example.com
make seed
```

Set `TRANSPORT=voice`, `VOICE_PROVIDER=elevenlabs`, and `DEMO_AGENT_PHONE=+1+111111111111`.
Trial Twilio only rings **Verified Caller IDs** — add this number there first.
