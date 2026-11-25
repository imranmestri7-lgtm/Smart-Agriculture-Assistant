-- =========================================================
-- AgriSmart Migration 012: Smart Crop Reminders Schema
-- Feature Upgrade 9, Phase 3 (Part 2)
-- =========================================================

CREATE TABLE IF NOT EXISTS `crop_plan_reminders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `crop_plan_id` INT NOT NULL,
    `farm_id` INT NULL,
    `reminder_type` VARCHAR(50) NOT NULL, -- 'milestone' or 'growth_stage'
    `milestone_type` VARCHAR(50) NOT NULL, -- 'sowing', 'harvest', 'vegetative', 'flowering', 'fruit_development'
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT NULL,
    `guidance` TEXT NULL,
    `due_date` DATE NOT NULL,
    `days_offset` INT NOT NULL DEFAULT 0,
    `status` VARCHAR(30) NOT NULL DEFAULT 'pending', -- 'pending', 'completed', 'dismissed'
    `is_estimated` TINYINT(1) NOT NULL DEFAULT 0,
    `completed_at` TIMESTAMP NULL,
    `dismissed_at` TIMESTAMP NULL,
    `unique_key` VARCHAR(150) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_cprem_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cprem_plan` FOREIGN KEY (`crop_plan_id`) REFERENCES `crop_plans` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cprem_farm` FOREIGN KEY (`farm_id`) REFERENCES `farms` (`id`) ON DELETE SET NULL,
    INDEX `idx_cprem_user_due` (`user_id`, `due_date`),
    INDEX `idx_cprem_user_status` (`user_id`, `status`),
    INDEX `idx_cprem_plan` (`crop_plan_id`),
    UNIQUE KEY `uk_cprem_user_key` (`user_id`, `unique_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `crop_plan_reminder_settings` (
    `user_id` INT PRIMARY KEY,
    `sowing_lead_days` VARCHAR(50) NOT NULL DEFAULT '7,1,0',
    `harvest_lead_days` VARCHAR(50) NOT NULL DEFAULT '14,7,0',
    `enable_growth_stages` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_cprem_settings_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
