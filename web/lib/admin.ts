export type AdminEvent = {
  t: number;
  session_id: string;
  conversation_id: string;
  role: string;
  tool: string;
  status: string;
  summary: string;
  listing_id: string;
};

export type LiveCall = {
  id: string;
  session_id: string;
  conversation_id: string;
  role: string;
  listing_id: string;
  status: string;
  current_tool: string;
  tools: string[];
  events: AdminEvent[];
  summary: string;
  transcript: string;
  rail: string[];
  el_status?: string;
};

export type HistoryCall = {
  conversation_id: string;
  role: string;
  status: string;
  direction: string;
  duration_secs: number | null;
  started_at: number;
  tools: string[];
};

export type CallDetail = {
  conversation_id: string;
  role: string;
  status: string;
  direction: string;
  duration_secs: number | null;
  started_at: number;
  turns: { role: string; text: string }[];
  tools: { name: string; params: string; result: string; error: boolean }[];
  transcript: string;
};
