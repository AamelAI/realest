# start_calls

Renter agent only. Paste these into **Add webhook tool**.

- **Name:** `start_calls`
- **Method:** `POST`
- **URL:** `https://zipping-scarf-actress.ngrok-free.dev/agent/start-calls`
- **Authentication:** none
- **Headers:** none

## Description

```
Call this only after the caller confirmed which listings to verify. BEFORE calling it, ask if there is anything else they want asked on those calls. After it returns, read the "speak" field aloud. listing_ids must be real ids from the last record_preferences shortlist (like L061), never "Listing 2" or an address.
```

## Body

Type: **JSON**

**JSON description:**

```
Which shortlist listings to call, plus any extra questions for the listing agent.
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
