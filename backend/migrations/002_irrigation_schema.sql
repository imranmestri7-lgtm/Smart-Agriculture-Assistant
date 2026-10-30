-- =========================================================
-- AgriSmart Migration 002: Smart Irrigation History Schema
-- Safe and idempotent migration script
-- =========================================================

CREATE TABLE IF NOT EXISTS `irrigation_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `crop` VARCHAR(100) NOT NULL,
    `soil_moisture` DECIMAL(5,2) NOT NULL,
    `temperature` DECIMAL(5,2) NOT NULL,
    `humidity` DECIMAL(5,2) NOT NULL,
    `rainfall` DECIMAL(5,2) NOT NULL,
    `location` VARCHAR(150) NULL,
    `recommendation_status` VARCHAR(50) NOT NULL,
    `is_irrigation_needed` TINYINT(1) NOT NULL,
    `water_quantity_mm` DECIMAL(5,2) NULL,
    `notes` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_irrigation_user_date` (`user_id`, `created_at` DESC),
    CONSTRAINT `fk_irrigation_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
