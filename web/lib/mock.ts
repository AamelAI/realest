import type { Card, SessionState } from "./types";

/**
 * Template data so the shell can be designed and reviewed without a phone.
 * Real rows come from data/listings.json merged with live SessionState.
 *
 * Deliberately covers every status at once — it is the only way to check that
 * a dead card and a verified card read differently at a glance.
 */
export const MOCK_CARDS: Card[] = [
  {
    listing_id: "L080", address: "80 Lynn Williams St", rent: 3295, beds: 2, baths: 2,
    neighbourhood: "Liberty Village", property_type: "Condo", sqft: 742,
    parking_included: true, pets: "cats only", amenities: ["locker", "gym"],
    transit_note: "3 min to Exhibition GO",
    photo_url: "https://images.rentals.ca/property-pictures/medium/toronto-on/469271/apartment-2239901077.jpg",
    agent_name: "Priya",
    status: "booked", rank: 1,
    outcome: {
      available: true, real_rent: 3295, addons: [], pets_allowed: "cats only",
      viewing_slot: "Saturday 2:00pm", answers: { locker: "included" },
      source: "Priya · 1:42pm",
    },
  },
  {
    listing_id: "L061", address: "700 Wellington St W", rent: 3250, beds: 2, baths: 2,
    neighbourhood: "King West", property_type: "Apartment", sqft: 810,
    parking_included: true, pets: "ask", amenities: ["concierge"],
    transit_note: "8 min to King streetcar",
    photo_url: "https://images.rentals.ca/property-pictures/medium/toronto-on/1021023/apartment-2239930288.jpg",
    agent_name: "Dana",
    status: "verified", rank: 2,
    outcome: {
      available: true, real_rent: 3430, addons: ["parking $180", "locker $40"],
      pets_allowed: null, viewing_slot: null, answers: {}, source: "Dana · 1:41pm",
    },
  },
  {
    listing_id: "L033", address: "748 Bathurst Street", rent: 3390, beds: 2, baths: 1,
    neighbourhood: "The Annex", property_type: "Apartment", sqft: 690,
    parking_included: false, pets: "pets OK", amenities: ["bike storage"],
    transit_note: "5 min to Spadina Station",
    photo_url: "https://images.rentals.ca/property-pictures/medium/toronto-on/1194978/apartment-2240596756.jpg",
    agent_name: "Marco",
    status: "no_answer", rank: 3,
    outcome: null,
    email_draft:
      "Hi Marco — following up about 748 Bathurst. Is the unit still available, is parking an extra cost, and do you allow dogs? Could we view it Saturday afternoon?",
  },
  {
    listing_id: "L007", address: "155 Strachan Ave", rent: 3180, beds: 2, baths: 1,
    neighbourhood: "Liberty Village", property_type: "Condo", sqft: 705,
    parking_included: true, pets: "ask", amenities: ["roof deck", "gym"],
    transit_note: "4 min to King streetcar",
    photo_url: "https://images.rentals.ca/property-pictures/medium/toronto-on/454607/apartment-2239910818.jpg",
    agent_name: "Mark",
    status: "dead", rank: 4,
    outcome: {
      available: false, real_rent: null, addons: [], pets_allowed: null,
      viewing_slot: null, answers: {}, source: "Mark · 1:40pm",
    },
  },
  {
    listing_id: "L112", address: "39 Niagara Street", rent: 3120, beds: 2, baths: 1,
    neighbourhood: "King West", property_type: "Apartment", sqft: 668,
    parking_included: false, pets: null, amenities: ["balcony"],
    transit_note: "7 min to King streetcar",
    photo_url: "https://images.rentals.ca/property-pictures/medium/toronto-on/300047/apartment-2239878489.jpg",
    agent_name: "Sofia",
    status: "calling", rank: 5, outcome: null,
  },
  {
    listing_id: "L044", address: "25 Ordnance Street", rent: 3390, beds: 2, baths: 2,
    neighbourhood: "Liberty Village", property_type: "Apartment", sqft: 780,
    parking_included: true, pets: "ask", amenities: ["gym", "party room"],
    transit_note: "6 min to Exhibition GO",
    photo_url: "https://images.rentals.ca/property-pictures/medium/toronto-on/1090896/apartment-2239944320.jpg",
    agent_name: "Ben",
    status: "pending", rank: 6, outcome: null,
  },
];

export const MOCK_STATE: SessionState = {
  session_id: "template",
  preferences: { beds: 2, areas: ["King West", "Liberty Village"], max_rent: 3400, parking: true },
  listings: MOCK_CARDS,
  agent_says: "Your top pick is gone — leased Tuesday. Wellington is really $3,430 once parking and a locker are in.",
  updated_at: Date.now() / 1000,
};
