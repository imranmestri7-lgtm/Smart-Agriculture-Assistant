# Phase 2 – Disease Knowledge Base & Database Expansion

## Overview
This phase adds a structured plant‑disease knowledge base for the 38 classes supported by the trained TensorFlow model and extends the database schema to store diagnosis history.

### Key Components
- **`backend/data/disease_knowledge_base.json`** – JSON file with entries for each class label (including the `healthy` class). Each entry contains:
  - `disease_name`
  - `crop`
  - `symptoms`
  - `possible_causes`
  - `prevention`
  - `care_recommendations`
  - `treatment` (only when safe and verified).
- **`backend/utils/disease_knowledge.py`** – Helper functions that:
  - Load the JSON knowledge base.
  - Provide lookup by class label.
  - Gracefully handle unknown or unsupported labels and low‑confidence predictions.
- **`backend/routes/disease_routes.py`** – Updated to:
  - Return a `knowledge` field in the prediction response.
  - Use the helper for healthy‑plant and fallback handling.
- **Database migration** – `backend/migrations/001_phase2_disease_schema.sql` adds columns `predicted_class` and `notes` to `diagnosis_history`. The script **deletes and reinserts** symptom, prevention, and treatment rows to ensure consistency (it does **not** preserve existing child rows).

## Verification Checklist
| Item | Status |
|------|--------|
| Knowledge‑base covers all 38 model class labels (including healthy) | ✅ Verified (JSON contains 38 entries) |
| Safe handling for healthy, unsupported, missing, low‑confidence predictions | ✅ Implemented in `disease_knowledge` helpers |
| Image preprocessing matches `backend/train_model.py` | ✅ Normalisation uses MobileNetV2 preprocessing and correct size |
| Python source compilation – no syntax errors | ✅ No compile errors detected |
| Unit‑test suite `backend/tests/test_phase2.py` | **6 PASS**, **1 FAIL** – the failing test expects the model to be reachable; TensorFlow cannot be loaded in the sandbox, so the endpoint returns 503 as designed |
| Database migration applied | ❌ Not executed – migration would delete/re‑insert child rows; manual run pending |
| Documentation `PHASE2.md` created | ✅ This file |

## Limitations & Open Items
- The test `test_predict_endpoint` fails because TensorFlow cannot be imported in the sandbox environment. The application correctly returns a 503 status when the model is unavailable.
- The migration script has not been run; running it would remove existing symptom/prevention/treatment rows and re‑insert them, which may affect current data.
- Real MySQL connector is not available in the sandbox; a stub package was added to allow test import. In production the proper connector must be installed.

## Next Steps (Phase 3) – Not executed yet
- Implement fallback dummy model or mock to allow prediction tests to pass.
- Run the migration after confirming data backup.
- Add multilingual support for knowledge‑base entries.
- Integrate weather and irrigation modules.
