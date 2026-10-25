-- =========================================================
-- AgriSmart Migration 001: Phase 2 Disease Schema & History
-- Safe and idempotent migration script
-- =========================================================

-- 1. Ensure diagnosis_history columns exist for direct predicted class and notes
-- (Handled programmatically in run_migrations.py for broad MySQL version compatibility)
ALTER TABLE `diagnosis_history`
    ADD COLUMN IF NOT EXISTS `predicted_class` VARCHAR(150) NULL AFTER `disease_id`;

ALTER TABLE `diagnosis_history`
    ADD COLUMN IF NOT EXISTS `notes` TEXT NULL AFTER `confidence`;

-- 2. Index on diagnosis_date and user_id for fast history lookup
-- CREATE INDEX idx_diagnosis_user_date ON diagnosis_history (user_id, diagnosis_date DESC);
