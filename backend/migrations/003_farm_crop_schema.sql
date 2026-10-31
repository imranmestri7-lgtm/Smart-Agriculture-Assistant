-- =========================================================
-- AgriSmart Migration 003: Farm & Crop Management Schema
-- Safe and idempotent migration script for Phase 6
-- =========================================================

-- 1. Create farms table
CREATE TABLE IF NOT EXISTS `farms` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `farm_name` VARCHAR(150) NOT NULL,
    `location` VARCHAR(200) NOT NULL,
    `total_area` DECIMAL(10, 2) NOT NULL,
    `area_unit` VARCHAR(20) NOT NULL DEFAULT 'acre',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_farms_user` (`user_id`),
    CONSTRAINT `fk_farms_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 2. Extend existing crops table with farm association, cultivated area and growth status
-- (Handled safely with IF NOT EXISTS / information_schema in python runner)
ALTER TABLE `crops`
    ADD COLUMN IF NOT EXISTS `farm_id` INT NULL AFTER `user_id`,
    ADD COLUMN IF NOT EXISTS `cultivated_area` DECIMAL(10, 2) NULL AFTER `planting_date`,
    ADD COLUMN IF NOT EXISTS `area_unit` VARCHAR(20) NOT NULL DEFAULT 'acre' AFTER `cultivated_area`,
    ADD COLUMN IF NOT EXISTS `growth_status` VARCHAR(50) NOT NULL DEFAULT 'Newly Planted' AFTER `area_unit`,
    ADD COLUMN IF NOT EXISTS `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER `created_at`;
