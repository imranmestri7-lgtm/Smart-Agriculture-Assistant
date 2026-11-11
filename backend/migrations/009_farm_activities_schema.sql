-- =========================================================
-- AgriSmart Migration 009: Smart Farm Activity Calendar & Task Planner Schema
-- Safe and idempotent migration script for Feature Upgrade 6
-- =========================================================

-- 1. Create farm_activities table
CREATE TABLE IF NOT EXISTS `farm_activities` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `farm_id` INT NULL,
    `crop_id` INT NULL,
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT NULL,
    `category` VARCHAR(60) NOT NULL,
    `priority` VARCHAR(20) NOT NULL DEFAULT 'Medium',
    `status` VARCHAR(30) NOT NULL DEFAULT 'Pending',
    `scheduled_date` DATE NOT NULL,
    `scheduled_time` TIME NULL,
    `reminder_enabled` TINYINT(1) NOT NULL DEFAULT 1,
    `completion_date` DATE NULL,
    `notes` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_activity_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_activity_farm` FOREIGN KEY (`farm_id`) REFERENCES `farms` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_activity_crop` FOREIGN KEY (`crop_id`) REFERENCES `crops` (`id`) ON DELETE SET NULL,
    INDEX `idx_activity_user_date` (`user_id`, `scheduled_date`),
    INDEX `idx_activity_user_status` (`user_id`, `status`),
    INDEX `idx_activity_user_category` (`user_id`, `category`),
    INDEX `idx_activity_crop` (`crop_id`),
    INDEX `idx_activity_farm` (`farm_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
