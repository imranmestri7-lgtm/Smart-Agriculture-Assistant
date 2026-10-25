import json
import os
import sys

# Ensure backend directory is in python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config

KB_PATH = os.path.join(BASE_DIR, "data", "disease_knowledge_base.json")


def run_database_migrations():
    """
    Executes idempotent database schema updates and seeds the disease knowledge base.
    """
    print("==================================================")
    print("Starting AgriSmart Phase 2 Database Migration")
    print("==================================================")

    if not os.path.isfile(KB_PATH):
        raise FileNotFoundError(f"Knowledge base file not found: {KB_PATH}")

    with open(KB_PATH, "r", encoding="utf-8") as f:
        kb_data = json.load(f)

    conn = None
    cur = None

    try:
        conn = config.get_db_connection()
        cur = conn.cursor(dictionary=True)

        # ---------------------------------------------------------
        # 1. Update diagnosis_history columns safely
        # ---------------------------------------------------------
        print("\nStep 1: Checking diagnosis_history table columns...")
        cur.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'diagnosis_history'
        """)
        existing_cols = {row["COLUMN_NAME"] for row in cur.fetchall()}

        if "predicted_class" not in existing_cols:
            print("  -> Adding column 'predicted_class' to diagnosis_history...")
            cur.execute("""
                ALTER TABLE diagnosis_history
                ADD COLUMN predicted_class VARCHAR(150) NULL AFTER disease_id
            """)
        else:
            print("  -> Column 'predicted_class' already exists.")

        if "notes" not in existing_cols:
            print("  -> Adding column 'notes' to diagnosis_history...")
            cur.execute("""
                ALTER TABLE diagnosis_history
                ADD COLUMN notes TEXT NULL AFTER confidence
            """)
        else:
            print("  -> Column 'notes' already exists.")

        conn.commit()

        # ---------------------------------------------------------
        # 2. Seed / Sync diseases knowledge base into MySQL
        # ---------------------------------------------------------
        print(f"\nStep 2: Syncing {len(kb_data)} disease knowledge entries into database...")

        diseases_synced = 0
        symptoms_count = 0
        preventions_count = 0
        treatments_count = 0

        for class_name, entry in kb_data.items():
            # Check if disease already exists
            cur.execute("SELECT id FROM diseases WHERE disease_name = %s", (class_name,))
            row = cur.fetchone()

            if row:
                disease_id = row["id"]
                # Update description
                cur.execute(
                    "UPDATE diseases SET description = %s WHERE id = %s",
                    (entry.get("description", ""), disease_id)
                )
            else:
                cur.execute(
                    "INSERT INTO diseases (disease_name, description) VALUES (%s, %s)",
                    (class_name, entry.get("description", ""))
                )
                disease_id = cur.lastrowid

            diseases_synced += 1

            # Sync symptoms (clean replacement for this disease)
            cur.execute("DELETE FROM symptoms WHERE disease_id = %s", (disease_id,))
            for sym in entry.get("symptoms", []):
                cur.execute(
                    "INSERT INTO symptoms (disease_id, symptom) VALUES (%s, %s)",
                    (disease_id, sym)
                )
                symptoms_count += 1

            # Sync preventions
            cur.execute("DELETE FROM preventions WHERE disease_id = %s", (disease_id,))
            for prev in entry.get("prevention", []):
                cur.execute(
                    "INSERT INTO preventions (disease_id, prevention) VALUES (%s, %s)",
                    (disease_id, prev)
                )
                preventions_count += 1

            # Sync treatments
            cur.execute("DELETE FROM treatments WHERE disease_id = %s", (disease_id,))
            for treat in entry.get("safe_treatment", []):
                cur.execute(
                    "INSERT INTO treatments (disease_id, treatment) VALUES (%s, %s)",
                    (disease_id, treat)
                )
                treatments_count += 1

        conn.commit()

        print("\n==================================================")
        print("Migration Completed Successfully!")
        print(f"Diseases Synced:      {diseases_synced}")
        print(f"Symptoms Inserted:    {symptoms_count}")
        print(f"Preventions Inserted: {preventions_count}")
        print(f"Treatments Inserted:  {treatments_count}")
        print("==================================================")

        return True

    except Exception as error:
        if conn:
            conn.rollback()
        print(f"\nMigration Failed with Error: {error}")
        raise error

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    run_database_migrations()
