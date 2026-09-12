// Mirror of server/schemas.py. Keep in sync - silent shape drift shows up as
// blank cards during the demo.

export type CallStatus =
  | "pending" | "calling" | "verified" | "dead" | "no_answer" | "booked";

export type CallOutcome = {
  available: boolean | null;
  real_rent: number | null;
  addons: string[];
  pets_allowed: string | null;
  viewing_slot: string | null;
  answers: Record<string, string>;
  source: string;
  raw_transcript: string;
};

export type ListingState = {
  listing_id: string;
  status: CallStatus;
  rank: number;
  outcome: CallOutcome | null;
  email_draft: string | null;
};

export type SessionState = {
  session_id: string;
  preferences: Record<string, unknown>;
  listings: ListingState[];   // already ranked. NEVER sort this in the page.
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
