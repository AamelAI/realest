# record_outcome

Listing agent only. Paste these into **Add webhook tool**.

- **Name:** `record_outcome`
- **Method:** `POST`
- **URL:** `https://zipping-scarf-actress.ngrok-free.dev/agent/outcome`
- **Authentication:** none
- **Headers:** none

## Description

```
Call this at the end of the call with everything the listing agent actually said. Only fill a field if they said it. Never guess. After it returns, you can hang up.
```

## Body

Type: **JSON**

**JSON description:**

```
Facts from the human listing agent. Omit any field they did not mention.
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
- **Value Type:** Dynamic Variable → `listing_id`

```
Pass {{listing_id}}. Never invent it.
```

#### available

- **Data type:** boolean
- **Identifier:** `available`
- **Required:** no
- **Value Type:** LLM Prompt

```
True if they said the unit is still available. False if gone or leased. Omit if unsaid.
```

#### addons

- **Data type:** array of strings
- **Identifier:** `addons`
- **Required:** no
- **Value Type:** LLM Prompt

```
Mandatory extra costs they named, e.g. parking $180. Array of short phrases.
```

#### pets_allowed

- **Data type:** string
- **Identifier:** `pets_allowed`
- **Required:** no
- **Value Type:** LLM Prompt

```
Exactly what they said about pets. Do not paraphrase into a policy.
```

#### viewing_slot

- **Data type:** string
- **Identifier:** `viewing_slot`
- **Required:** no
- **Value Type:** LLM Prompt

```
Viewing time they offered, if any.
```

#### answers

- **Data type:** string
- **Identifier:** `answers`
- **Required:** no
- **Value Type:** LLM Prompt

```
Their answers to extra questions, as short phrases.
```

#### source

- **Data type:** string
- **Identifier:** `source`
- **Required:** no
- **Value Type:** LLM Prompt

```
Who said it and when, e.g. Mark, 1:42pm.
```
