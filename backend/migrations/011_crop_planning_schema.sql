-- =========================================================
-- AgriSmart Migration 011: Smart Crop Planning Foundation Schema
-- Safe and idempotent migration script for Feature Upgrade 9 - Prompt 1
-- =========================================================

CREATE TABLE IF NOT EXISTS `crop_plans` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `farm_id` INT NULL,
    `crop_name` VARCHAR(100) NOT NULL,
    `variety` VARCHAR(100) NULL,
    `season` VARCHAR(30) NOT NULL,
    `planning_year` INT NOT NULL,
    `planned_sowing_date` DATE NOT NULL,
    `expected_harvest_date` DATE NOT NULL,
    `land_area` DECIMAL(10,2) NOT NULL,
    `area_unit` VARCHAR(20) NOT NULL DEFAULT 'acre',
    `field_location` VARCHAR(150) NULL,
    `target_yield` DECIMAL(10,2) NULL,
    `yield_unit` VARCHAR(30) NULL DEFAULT 'quintal',
    `estimated_budget` DECIMAL(12,2) NULL,
    `estimated_revenue` DECIMAL(12,2) NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'Planned',
    `notes` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_crop_plan_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_crop_plan_farm` FOREIGN KEY (`farm_id`) REFERENCES `farms` (`id`) ON DELETE SET NULL,
    INDEX `idx_crop_plan_user_sowing` (`user_id`, `planned_sowing_date`),
    INDEX `idx_crop_plan_user_season` (`user_id`, `season`, `planning_year`),
    INDEX `idx_crop_plan_user_status` (`user_id`, `status`),
    INDEX `idx_crop_plan_farm` (`farm_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
