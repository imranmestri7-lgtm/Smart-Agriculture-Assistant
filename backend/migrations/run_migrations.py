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

        # ---------------------------------------------------------
        # 3. Phase 6: Farms and Crops Schema
        # ---------------------------------------------------------
        print("\nStep 3: Checking farms and crops schema...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS farms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                farm_name VARCHAR(150) NOT NULL,
                location VARCHAR(200) NOT NULL,
                total_area DECIMAL(10, 2) NOT NULL,
                area_unit VARCHAR(20) NOT NULL DEFAULT 'acre',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_farms_user (user_id),
                CONSTRAINT fk_farms_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """)

        cur.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'crops'
        """)
        crops_cols = {row["COLUMN_NAME"] for row in cur.fetchall()}

        if "farm_id" not in crops_cols:
            print("  -> Adding column 'farm_id' to crops...")
            cur.execute("""
                ALTER TABLE crops
                ADD COLUMN farm_id INT NULL AFTER user_id,
                ADD CONSTRAINT fk_crops_farm FOREIGN KEY (farm_id) REFERENCES farms (id) ON DELETE CASCADE
            """)

        if "cultivated_area" not in crops_cols:
            print("  -> Adding column 'cultivated_area' to crops...")
            cur.execute("""
                ALTER TABLE crops
                ADD COLUMN cultivated_area DECIMAL(10, 2) NULL AFTER planting_date
            """)

        if "area_unit" not in crops_cols:
            print("  -> Adding column 'area_unit' to crops...")
            cur.execute("""
                ALTER TABLE crops
                ADD COLUMN area_unit VARCHAR(20) NOT NULL DEFAULT 'acre' AFTER cultivated_area
            """)

        if "growth_status" not in crops_cols:
            print("  -> Adding column 'growth_status' to crops...")
            cur.execute("""
                ALTER TABLE crops
                ADD COLUMN growth_status VARCHAR(50) NOT NULL DEFAULT 'Newly Planted' AFTER area_unit
            """)

        if "updated_at" not in crops_cols:
            print("  -> Adding column 'updated_at' to crops...")
            cur.execute("""
                ALTER TABLE crops
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at
            """)

        # ---------------------------------------------------------
        # 4. Phase 8: Notifications & Preferences Schema
        # ---------------------------------------------------------
        print("\nStep 4: Checking notifications and preferences schema...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                category VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                severity VARCHAR(20) NOT NULL DEFAULT 'info',
                is_read TINYINT(1) NOT NULL DEFAULT 0,
                link VARCHAR(255) NULL,
                unique_key VARCHAR(150) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_notifications_user (user_id),
                INDEX idx_notifications_user_read (user_id, is_read),
                INDEX idx_notifications_user_key (user_id, unique_key),
                INDEX idx_notifications_user_cat (user_id, category),
                CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                crop_reminders TINYINT(1) NOT NULL DEFAULT 1,
                irrigation_alerts TINYINT(1) NOT NULL DEFAULT 1,
                weather_alerts TINYINT(1) NOT NULL DEFAULT 1,
                disease_reminders TINYINT(1) NOT NULL DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT fk_notification_prefs_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """)

        # ---------------------------------------------------------
        # 5. Create Phase 10 IoT Smart Farm Monitoring tables
        # ---------------------------------------------------------
        print("\nStep 5: Checking IoT Smart Farm Monitoring tables...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sensors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                farm_id INT NOT NULL,
                crop_id INT NULL,
                device_id VARCHAR(100) NOT NULL UNIQUE,
                device_key_hash VARCHAR(255) NOT NULL,
                sensor_name VARCHAR(150) NOT NULL,
                sensor_type VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'disconnected',
                last_reading_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_sensors_user (user_id),
                INDEX idx_sensors_farm (farm_id),
                INDEX idx_sensors_crop (crop_id),
                INDEX idx_sensors_device (device_id),
                INDEX idx_sensors_type (sensor_type),
                INDEX idx_sensors_status (status),
                CONSTRAINT fk_sensors_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                CONSTRAINT fk_sensors_farm FOREIGN KEY (farm_id) REFERENCES farms (id) ON DELETE CASCADE,
                CONSTRAINT fk_sensors_crop FOREIGN KEY (crop_id) REFERENCES crops (id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sensor_id INT NOT NULL,
                user_id INT NOT NULL,
                sensor_type VARCHAR(50) NOT NULL,
                value DECIMAL(8, 2) NOT NULL,
                unit VARCHAR(20) NOT NULL,
                is_demo TINYINT(1) NOT NULL DEFAULT 0,
                recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_readings_sensor_time (sensor_id, recorded_at),
                INDEX idx_readings_user_time (user_id, recorded_at),
                INDEX idx_readings_demo (sensor_id, is_demo),
                CONSTRAINT fk_readings_sensor FOREIGN KEY (sensor_id) REFERENCES sensors (id) ON DELETE CASCADE,
                CONSTRAINT fk_readings_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sensor_thresholds (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sensor_id INT NOT NULL UNIQUE,
                user_id INT NOT NULL,
                min_value DECIMAL(8, 2) NULL,
                max_value DECIMAL(8, 2) NULL,
                is_enabled TINYINT(1) NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_thresholds_user (user_id),
                CONSTRAINT fk_thresholds_sensor FOREIGN KEY (sensor_id) REFERENCES sensors (id) ON DELETE CASCADE,
                CONSTRAINT fk_thresholds_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """)

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
