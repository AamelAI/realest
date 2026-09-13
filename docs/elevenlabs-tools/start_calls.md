# start_calls

Renter agent only. Paste these into **Add webhook tool**.

- **Name:** `start_calls`
- **Method:** `POST`
- **URL:** `https://zipping-scarf-actress.ngrok-free.dev/agent/start-calls`
- **Authentication:** none
- **Headers:** none

## Description

```
Call this only after the caller confirmed which listings to verify. BEFORE calling it, ask when they are free for viewings and pass that as availability, then ask if there is anything else they want asked on those calls. The moment you call it, say: "Wait until I gather all the information from the real estate agents." Then stay silent until it returns — that can take a minute — and read the speak field aloud. Do not guess results or fill the silence. listing_ids must be real ids from the last record_preferences shortlist (like L061), never "Listing 2" or an address.
```

## Body

Type: **JSON**

**JSON description:**

```
Which shortlist listings to call, the renter's viewing availability, plus any extra questions for the listing agent.
```

### Properties

#### session_id

- **Data type:** string
- **Identifier:** `session_id`
- **Required:** yes
- **Value Type:** Dynamic Variable → `session_id`

```
Pass {{session_id}} or the session_id from the last tool result. Never invent it.
```

#### listing_ids

- **Data type:** array of strings
- **Identifier:** `listing_ids`
- **Required:** yes
- **Value Type:** LLM Prompt

```
Real listing ids from the shortlist, e.g. L061. Array of strings. Not addresses.
```

#### extra_questions

- **Data type:** array of strings
- **Identifier:** `extra_questions`
- **Required:** no
- **Value Type:** LLM Prompt

```
Extra things the caller wants asked, each as a short phrase. Array of strings.
```

#### availability

- **Data type:** string
- **Identifier:** `availability`
- **Required:** no
- **Value Type:** LLM Prompt

```
When the renter can view, as one short phrase, e.g. weeknights after 6 or Saturday morning. Empty if they did not say.
```
