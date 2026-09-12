# book_viewing

Renter agent only. Paste these into **Add webhook tool**.

- **Name:** `book_viewing`
- **Method:** `POST`
- **URL:** `https://zipping-scarf-actress.ngrok-free.dev/agent/book`
- **Authentication:** none
- **Headers:** none

## Description

```
Call this only when the caller confirms a specific viewing time on a specific listing. After it returns, read the "speak" field aloud.
```

## Body

Type: **JSON**

**JSON description:**

```
The listing and time the caller just confirmed.
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
- **Required:** yes
- **Value Type:** LLM Prompt

```
The agreed time as they said it, e.g. Saturday 2:00pm.
```
