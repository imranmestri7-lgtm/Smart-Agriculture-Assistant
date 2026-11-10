-- AgriSmart Feature Upgrade 5: Smart Farm Expense & Profit Management System Schema

CREATE TABLE IF NOT EXISTS farm_expenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    farm_id INT NULL,
    crop_id INT NULL,
    crop_name VARCHAR(100) NULL,
    category VARCHAR(60) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    expense_date DATE NOT NULL,
    quantity DECIMAL(10, 2) NULL DEFAULT NULL,
    unit VARCHAR(30) NULL DEFAULT NULL,
    description VARCHAR(255) NULL DEFAULT NULL,
    notes TEXT NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_expenses_user_date (user_id, expense_date),
    INDEX idx_expenses_crop (crop_id),
    INDEX idx_expenses_category (category),
    CONSTRAINT fk_expense_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_expense_farm FOREIGN KEY (farm_id) REFERENCES farms (id) ON DELETE SET NULL,
    CONSTRAINT fk_expense_crop FOREIGN KEY (crop_id) REFERENCES crops (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS farm_harvests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    farm_id INT NULL,
    crop_id INT NULL,
    crop_name VARCHAR(100) NOT NULL,
    harvest_date DATE NOT NULL,
    quantity DECIMAL(10, 2) NOT NULL,
    unit VARCHAR(30) NOT NULL,
    price_per_unit DECIMAL(10, 2) NOT NULL,
    total_revenue DECIMAL(12, 2) NOT NULL,
    buyer_name VARCHAR(150) NULL DEFAULT NULL,
    notes TEXT NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_harvests_user_date (user_id, harvest_date),
    INDEX idx_harvests_crop (crop_id),
    CONSTRAINT fk_harvest_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_harvest_farm FOREIGN KEY (farm_id) REFERENCES farms (id) ON DELETE SET NULL,
    CONSTRAINT fk_harvest_crop FOREIGN KEY (crop_id) REFERENCES crops (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
