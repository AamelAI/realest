# record_preferences

Renter agent only. Paste these into **Add webhook tool**.

- **Name:** `record_preferences`
- **Method:** `POST`
- **URL:** `https://zipping-scarf-actress.ngrok-free.dev/agent/preferences`
- **Authentication:** none
- **Headers:** none

## Description

```
Call this as soon as the caller has described what they want: bedrooms, neighbourhoods, budget, parking, or pets. Call it AGAIN any time they change or reprioritize. Do not wait until the end of the call. After it returns, read the "speak" field aloud. Use the returned session_id on every later tool call. Never invent a session_id.
```

## Body

Type: **JSON**

**JSON description:**

```
Preferences the caller just said. Only include fields they actually mentioned.
```

### Properties

#### session_id

- **Data type:** string
- **Identifier:** `session_id`
- **Required:** yes
- **Value Type:** Dynamic Variable → `session_id`

```
Pass {{session_id}}. If empty, omit it — the server will mint one. Never invent an id.
```

#### beds

- **Data type:** integer
- **Identifier:** `beds`
- **Required:** no
- **Value Type:** LLM Prompt

```
Number of bedrooms they want. Integer only. Omit if they did not say.
```

#### baths

- **Data type:** integer
- **Identifier:** `baths`
- **Required:** no
- **Value Type:** LLM Prompt

```
Number of bathrooms they want. Integer only. Omit if they did not say.
```

#### areas

- **Data type:** array of strings
- **Identifier:** `areas`
- **Required:** no
- **Value Type:** LLM Prompt

```
Neighbourhoods they named, e.g. King West, Liberty Village. Array of strings.
```

#### max_rent

- **Data type:** integer
- **Identifier:** `max_rent`
- **Required:** no
- **Value Type:** LLM Prompt

```
Maximum monthly rent in CAD. Integer only, no dollar sign.
```

#### parking

- **Data type:** boolean
- **Identifier:** `parking`
- **Required:** no
- **Value Type:** LLM Prompt

```
True if they need parking. False if they said they do not. Omit if unsaid.
```

#### pets

- **Data type:** string
- **Identifier:** `pets`
- **Required:** no
- **Value Type:** LLM Prompt

```
Exactly what they said: dog, cat, or none.
```

#### priority_order

- **Data type:** array of strings
- **Identifier:** `priority_order`
- **Required:** no
- **Value Type:** LLM Prompt

```
What matters most first, e.g. transit, price, parking. Array of strings. Only if they ranked things.
```
