-- =====================================================
-- AGRISMART PHASE 10: IoT-READY SMART FARM MONITORING SCHEMA
-- =====================================================

CREATE TABLE IF NOT EXISTS `sensors` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `farm_id` INT NOT NULL,
    `crop_id` INT NULL,
    `device_id` VARCHAR(100) NOT NULL UNIQUE,
    `device_key_hash` VARCHAR(255) NOT NULL,
    `sensor_name` VARCHAR(150) NOT NULL,
    `sensor_type` VARCHAR(50) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'disconnected',
    `last_reading_at` TIMESTAMP NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_sensors_user` (`user_id`),
    INDEX `idx_sensors_farm` (`farm_id`),
    INDEX `idx_sensors_crop` (`crop_id`),
    INDEX `idx_sensors_device` (`device_id`),
    INDEX `idx_sensors_type` (`sensor_type`),
    INDEX `idx_sensors_status` (`status`),
    CONSTRAINT `fk_sensors_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_sensors_farm` FOREIGN KEY (`farm_id`) REFERENCES `farms` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_sensors_crop` FOREIGN KEY (`crop_id`) REFERENCES `crops` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `sensor_readings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `sensor_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `sensor_type` VARCHAR(50) NOT NULL,
    `value` DECIMAL(8, 2) NOT NULL,
    `unit` VARCHAR(20) NOT NULL,
    `is_demo` TINYINT(1) NOT NULL DEFAULT 0,
    `recorded_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_readings_sensor_time` (`sensor_id`, `recorded_at`),
    INDEX `idx_readings_user_time` (`user_id`, `recorded_at`),
    INDEX `idx_readings_demo` (`sensor_id`, `is_demo`),
    CONSTRAINT `fk_readings_sensor` FOREIGN KEY (`sensor_id`) REFERENCES `sensors` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_readings_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `sensor_thresholds` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `sensor_id` INT NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `min_value` DECIMAL(8, 2) NULL,
    `max_value` DECIMAL(8, 2) NULL,
    `is_enabled` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_thresholds_user` (`user_id`),
    CONSTRAINT `fk_thresholds_sensor` FOREIGN KEY (`sensor_id`) REFERENCES `sensors` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_thresholds_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
