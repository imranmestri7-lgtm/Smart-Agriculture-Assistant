-- =========================================================
-- AgriSmart Migration 010: Smart Farm Inventory & Stock Management Schema
-- Safe and idempotent migration script for Feature Upgrade 7
-- =========================================================

-- 1. Create farm_inventory table
CREATE TABLE IF NOT EXISTS `farm_inventory` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `farm_id` INT NULL,
    `item_name` VARCHAR(150) NOT NULL,
    `category` VARCHAR(60) NOT NULL,
    `quantity` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `unit` VARCHAR(30) NOT NULL DEFAULT 'kg',
    `purchase_price` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `purchase_date` DATE NOT NULL,
    `supplier_name` VARCHAR(150) NULL,
    `min_threshold` DECIMAL(12, 2) NOT NULL DEFAULT 5.00,
    `expiry_date` DATE NULL,
    `storage_location` VARCHAR(150) NULL,
    `notes` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_inventory_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_inventory_farm` FOREIGN KEY (`farm_id`) REFERENCES `farms` (`id`) ON DELETE SET NULL,
    INDEX `idx_inventory_user` (`user_id`),
    INDEX `idx_inventory_user_cat` (`user_id`, `category`),
    INDEX `idx_inventory_farm` (`farm_id`),
    INDEX `idx_inventory_expiry` (`expiry_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Create farm_inventory_movements table (Audit Trail)
CREATE TABLE IF NOT EXISTS `farm_inventory_movements` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `inventory_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `crop_id` INT NULL,
    `farm_id` INT NULL,
    `movement_type` VARCHAR(40) NOT NULL,
    `quantity` DECIMAL(12, 2) NOT NULL,
    `unit` VARCHAR(30) NOT NULL,
    `movement_date` DATE NOT NULL,
    `movement_time` TIME NULL,
    `reason` VARCHAR(255) NULL,
    `notes` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_movement_inventory` FOREIGN KEY (`inventory_id`) REFERENCES `farm_inventory` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_movement_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_movement_crop` FOREIGN KEY (`crop_id`) REFERENCES `crops` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_movement_farm` FOREIGN KEY (`farm_id`) REFERENCES `farms` (`id`) ON DELETE SET NULL,
    INDEX `idx_movement_inventory` (`inventory_id`),
    INDEX `idx_movement_user_date` (`user_id`, `movement_date`),
    INDEX `idx_movement_type` (`movement_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
