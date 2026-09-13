# book_viewing

Renter agent only. Paste these into **Add webhook tool**.

- **Name:** `book_viewing`
- **Method:** `POST`
- **URL:** `https://zipping-scarf-actress.ngrok-free.dev/agent/book`
- **Authentication:** none
- **Headers:** none

## Description

```
Call this the moment the caller books or passes. This tool texts the confirmation to the renter and the listing agent (or a rejection). Always call it — never only say it is booked. After it returns, read the speak field aloud.
```

## Body

Type: **JSON**

**JSON description:**

```
The listing, time, and whether the renter is confirming or passing.
```

### Properties

#### session_id

- **Data type:** string
- **Identifier:** `session_id`
- **Required:** yes
- **Value Type:** Dynamic Variable → `session_id`

```
Pass {{session_id}}. Never invent it.
```

#### caller_phone

- **Data type:** string
- **Identifier:** `caller_phone`
- **Required:** no
- **Value Type:** Dynamic Variable → `system__caller_id`

```
Inbound caller. Do not invent it.
```

#### listing_id

- **Data type:** string
- **Identifier:** `listing_id`
- **Required:** yes
- **Value Type:** LLM Prompt

```
Real listing id from the shortlist, e.g. L061.
```

#### slot

- **Data type:** string
- **Identifier:** `slot`
- **Required:** no
- **Value Type:** LLM Prompt

```
The agreed time as they said it, e.g. Saturday 2:00pm.
```

#### decision

- **Data type:** string
- **Identifier:** `decision`
- **Required:** no
- **Value Type:** LLM Prompt

```
confirm to book and text the landlord a confirmation. reject to text them that the renter is passing. Default confirm.
```
