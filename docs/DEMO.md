# The four demo listings — task `0.8`

Picked from the 124 seeded rentals. **All four are real rows in `data/listings.json`**,
unedited except one mislabelled neighbourhood (`L028`, 6020 Bathurst, was tagged
King West — it is North York). Nothing was fabricated to make the script work.

## The brief the caller speaks

> "One bedroom, King West, Liberty Village or down by the water, under twenty-eight
> hundred. I've got a dog."

`beds=1 · areas=[King West, Liberty Village, Waterfront] · max_rent=2800 · pets=dog`
**Do not mention parking in the opening brief.** It is the lever for the reorder.

## The reorder beat

Mid-call the caller says:

> "Actually — parking matters more than anything."

`parking=true · priority_order=["parking"]` → **3 of 4 cards change position.**

| | before | after |
|---|---|---|
| 1 | L013 $2,221 | L013 $2,221 |
| 2 | L061 $2,495 | L063 $2,070 |
| 3 | L054 $2,797 | L061 $2,495 |
| 4 | L063 $2,070 | L054 $2,797 |

## The four, and what each call reveals

| id | address | listed | role on camera |
|---|---|---|---|
| `L013` | 370 Queens Quay West, Waterfront | $2,221 | **DEAD** — "leased Tuesday." Was #1. Sinks to #4 |
| `L054` | 57 Spadina Avenue, King West | $2,797 | **PRICE WRONG** — parking is $180 on top → **$2,977**, over budget |
| `L061` | 25 Ordnance Street, Liberty Village | $2,495 | **BOOKED** — available, locker included, Saturday 2:00pm. *Cats only, and the caller has a dog* |
| `L063` | 131 Mill Street, Waterfront | $2,070 | **NO ANSWER** — email drafted, shown on the card with Send |

### Final order after the calls

`L063 (no answer) · L061 (booked) · L054 ($2,977, over) · L013 (dead)`

The top pick dies and drops to last. That is the shot.

## Still to do

**Every `agent_phone` in the file is the placeholder `+14165550100`.** Before
filming, the four rows above need three teammates' real numbers — one person per
call, and they need to know which listing they are playing and the script above.
We never dial anyone outside the team.
