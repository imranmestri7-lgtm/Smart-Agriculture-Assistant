-- AgriSmart Feature Upgrade 4: Smart Farm Alert & Notification System Schema
-- Adds related_id to notifications, push_enabled to notification_preferences, and push_subscriptions table.

ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS related_id INT NULL AFTER link;

ALTER TABLE notification_preferences
    ADD COLUMN IF NOT EXISTS push_enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER disease_reminders;

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    endpoint TEXT NOT NULL,
    p256dh VARCHAR(255) NOT NULL,
    auth VARCHAR(255) NOT NULL,
    user_agent VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_push_user (user_id),
    CONSTRAINT fk_push_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
