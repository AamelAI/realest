import type { Card, SessionState } from "./types";

/**
 * The template at `/`: the four demo listings from docs/DEMO.md, in the state
 * the demo ends in, so the design can be reviewed without a phone call.
 *
 * Every listing field is copied from data/listings.json. The call outcomes are
 * the ones docs/DEMO.md scripts. Sources carry the agent's name only — the demo
 * didn't record call times, and this page never invents one.
 */
const listing = {
  property_type: "Condo",
  sqft: null,
  amenities: [],
  email_draft: null,
} satisfies Partial<Card>;

export const MOCK_CARDS: Card[] = [
  {
    ...listing,
    listing_id: "L086", address: "155 Yorkville Avenue", rent: 2690, beds: 2, baths: 1,
    neighbourhood: "Yorkville", parking_included: true, pets: "cats only",
    transit_note: "3 min to Bay Station",
    photo_url: "https://images.rentals.ca/property-pictures/medium/toronto-on/1118361/condo-1083935149.jpg",
    agent_name: "Dana",
    status: "booked", rank: 1,
    outcome: {
      available: true, real_rent: null, addons: [], pets_allowed: "cats only",
      viewing_slot: "Saturday 2:00pm", answers: {}, source: "Dana",
    },
  },
  {
    ...listing,
    listing_id: "L100", address: "660 Huron Street", rent: 2290, beds: 2, baths: 1,
    neighbourhood: "The Annex", property_type: "Apartment", parking_included: true, pets: "cats only",
    transit_note: "5 min to Spadina Station",
    photo_url: "https://images.rentals.ca/property-pictures/medium/toronto-on/1542020/apartment-2241348367.jpg",
    agent_name: "Raj",
    status: "no_answer", rank: 2, outcome: null,
    email_draft:
      "Subject: 660 Huron Street — still available?\n\nHi Raj,\n\nI'm an AI assistant writing on behalf of a renter. Is the unit still available, is parking an extra monthly cost, and are dogs allowed?\n\nThanks",
  },
  {
    ...listing,
    listing_id: "L095", address: "322 Dupont Street", rent: 3290, beds: 2, baths: 2,
    neighbourhood: "The Annex", parking_included: true, pets: null,
    transit_note: "5 min to Spadina Station",
    photo_url: "https://images.rentals.ca/property-pictures/medium/toronto-on/1505046/condo-2240443434.jpg",
    agent_name: "Nadia",
    status: "verified", rank: 3,
    outcome: {
      available: true, real_rent: 3470, addons: ["parking $180"], pets_allowed: null,
      viewing_slot: null, answers: {}, source: "Nadia",
    },
  },
  {
    ...listing,
    listing_id: "L092", address: "155 Yorkville Avenue", rent: 3000, beds: 2, baths: 1,
    neighbourhood: "Yorkville", property_type: "Apartment", parking_included: false, pets: "ask",
    transit_note: "3 min to Bay Station",
    photo_url: "https://images.rentals.ca/property-pictures/medium/toronto-on/1533194/apartment-2241120773.jpg",
    agent_name: "Mark",
    status: "dead", rank: 4,
    outcome: {
      available: false, real_rent: null, addons: [], pets_allowed: null,
      viewing_slot: null, answers: {}, source: "Mark",
    },
  },
];

export const MOCK_STATE: SessionState = {
  session_id: "template",
  preferences: {
    beds: 2, areas: ["Yorkville", "The Annex"], max_rent: 3400, pets: "dog",
    parking: true, priority_order: ["parking"],
  },
  listings: MOCK_CARDS,
  agent_says:
    "155 Yorkville is leased. Dupont is really $3,470 once parking is in. Dana booked you for Saturday at two.",
  updated_at: 0,
};
