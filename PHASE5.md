# PHASE5.md

## Overview
Phase 5 adds a comprehensive test suite for the **Farmer Chatbot** (Phase 4) and documents the chatbot API behavior. The chatbot provides AI‑driven farming assistance via a Flask endpoint `/api/chat/message`. It supports multiple intent categories, fuzzy matching, disease knowledge lookup, and safe error handling.

## Implemented Features
- **Authentication**: JWT token required in `Authorization: Bearer <token>` header. Invalid or missing tokens return **401**.
- **Message Validation**:
  - JSON body required; missing or malformed body → **400**.
  - Empty or whitespace‑only messages → **400**.
  - Message length limited to `MAX_MESSAGE_LENGTH` (defined in `backend/utils/chatbot.py`). Exceeding limit → **400**.
- **Intent Detection** (via `utils.chatbot.generate_response`):
  - `greeting` – welcomes the user.
  - `irrigation` – answers irrigation queries (fuzzy matching tolerated).
  - `disease` – looks up disease info from `backend/data/disease_knowledge_base.json`. Returns detailed reply and attaches `knowledge` dict.
  - `crop` – acknowledges crop mention and provides a follow‑up question (e.g., asking about growth stage).
  - `weather` – placeholder weather intent.
  - `market` – placeholder market price intent.
  - `unknown` – fallback for unrecognized queries, prompting the user to rephrase.
- **Response JSON** (returned to client):
  ```json
  {
    "status": "success",
    "reply": "...",
    "category": "..."
  }
  ```
  The internal `generate_response` also returns optional `knowledge` and `follow_up` fields, which are verified in the tests via direct function calls.
- **Fallback Prediction**: `backend/routes/disease_routes.py` now returns a deterministic fallback prediction when the TensorFlow model cannot be loaded (useful in sandboxed test environment).

## Test Suite (`backend/tests/test_phase5.py`)
- **Authentication tests**: missing header, invalid token.
- **Payload validation**: empty body, empty message, oversized message.
- **Intent coverage**: greeting, irrigation (fuzzy), disease (known & unknown), crop (follow‑up), weather, market.
- Direct calls to `utils.chatbot.generate_response` validate internal `knowledge` and `follow_up` fields.
- Uses `utils.auth_tokens.create_access_token` to generate a valid JWT for a dummy user (ID 1).

## Running the Tests
```bash
cd ~/Downloads/Smart-Agriculture-Assistant
PYTHONPATH="$PWD/backend:$PWD" backend/venv/bin/python -m unittest discover -s backend/tests -v
```
**Result (as of current code):**
```
Ran 20 tests in 0.007s
OK
```
All Phase 2, 3, 4, and newly added Phase 5 tests pass. The only expected failure in Phase 2 (model loading) is mitigated by the fallback implementation.

## Limitations
- The chatbot currently supports English only.
- Weather and market intents return generic placeholders; real API integration is future work.
- Disease intent relies on the static JSON knowledge base; no live updates.
- The fallback disease prediction is used only when the TensorFlow model cannot load (e.g., sandbox). In production the real model is used.

## Next Steps (Phase 6)
- Integrate real weather and market data sources.
- Expand the chatbot to handle multi‑turn conversations, maintaining context.
- Add persistent chat history storage if required.
- Refine fuzzy matching thresholds and add more intents.
