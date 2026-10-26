# Phase 3 — Authentication and Diagnosis History

## Overview

Phase 3 integrates JWT authentication with plant disease predictions
and provides authenticated farmers with access to their diagnosis history.

## Implemented Features

- JWT access tokens are generated after successful email login and OTP
  verification.
- Access tokens expire after 12 hours.
- Disease prediction requests can include a Bearer token.
- Authenticated predictions are saved to `diagnosis_history`.
- Diagnosis history is available through `GET /api/disease/history`.
- History queries are filtered by the verified token's user ID.
- The history endpoint rejects missing and invalid or expired tokens.
- The history endpoint validates and limits the requested record count.
- The frontend displays saved diagnoses and supports refreshing history.
- Database errors return controlled API error responses.

## Files Added or Updated

- `backend/utils/auth_tokens.py`
- `backend/routes/auth_routes.py`
- `backend/routes/disease_routes.py`
- `backend/tests/test_phase3.py`
- `js/login.js`
- `js/disease.js`
- `disease.html`

## Verification

- Phase 2 regression tests: 7 tests.
- Phase 3 authentication and history tests: 5 tests.
- Browser test: prediction completed and the new diagnosis appeared
  in the history section.
- JavaScript syntax checks passed.
- Python compilation checks passed.

Run the test suites using:

```bash
PYTHONPATH="$PWD/backend:$PWD" \
  ./backend/venv/bin/python -m unittest \
  backend/tests/test_phase2.py \
  backend/tests/test_phase3.py -v
```

## Security Notes

- Diagnosis history is filtered by the authenticated user's ID.
- Clients cannot choose the user ID for a history query.
- JWT secrets must remain private and must not be committed to Git.
- Automated history tests use a mocked database.

## Remaining Project Work

- Farmer chatbot.
- English, Marathi, and Hindi interface and responses.
- Frontend animations and responsive UI polish.
- End-to-end testing and final documentation.
