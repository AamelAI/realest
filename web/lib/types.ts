// Mirror of server/schemas.py. Keep in sync — silent shape drift shows up as
// blank cards during the demo.

export type CallStatus =
  | "pending" | "calling" | "verified" | "dead" | "no_answer" | "booked";

export type CallOutcome = {
  available: boolean | null;
  real_rent: number | null;      // listed rent + mandatory add-ons
  addons: string[];              // "parking $180", "locker $40"
  pets_allowed: string | null;
  viewing_slot: string | null;
  answers: Record<string, string>;
  source: string;                // "Mark · 1:42pm" — provenance for the card
};

/**
 * What the page renders: a Listing joined with its live ListingState.
 * The server does the join in /api/state so the page never fetches twice.
 */
export type Card = {
  listing_id: string;
  address: string;
  rent: number;
  beds: number;
  baths: number;
  neighbourhood: string;
  property_type: string;
  sqft: number | null;
  parking_included: boolean;
  pets: string | null;
  amenities: string[];
  transit_note: string;
  photo_url: string;
  agent_name: string;

  status: CallStatus;
  rank: number;
  outcome: CallOutcome | null;
  email_draft?: string | null;
};

export type SessionState = {
  session_id: string;
  preferences: {
    beds?: number | null;
    baths?: number | null;
    areas?: string[];
    max_rent?: number | null;
    parking?: boolean | null;
    pets?: string | null;
    priority_order?: string[];
    extra_questions?: string[];
  };
  listings: Card[];   // already ranked. NEVER sort this in the page.
  agent_says: string;
  updated_at: number;
};

export const DEFAULT_STATE: SessionState = {
  session_id: "",
  preferences: {},
  listings: [],
  agent_says: "",
  updated_at: 0,
};
