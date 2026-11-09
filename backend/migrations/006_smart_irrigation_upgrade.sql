-- AgriSmart Feature Upgrade 3: Smart Irrigation Recommendation Schema
-- Enhances irrigation_history to record soil type, growth stage, timing recommendation, forecast rain, and water saved.

ALTER TABLE irrigation_history
    MODIFY COLUMN soil_moisture DECIMAL(5,2) NULL,
    ADD COLUMN IF NOT EXISTS soil_type VARCHAR(50) NULL AFTER location,
    ADD COLUMN IF NOT EXISTS growth_stage VARCHAR(50) NULL AFTER soil_type,
    ADD COLUMN IF NOT EXISTS timing_recommendation VARCHAR(100) NULL AFTER recommendation_status,
    ADD COLUMN IF NOT EXISTS forecast_rain_mm DECIMAL(5,2) NULL DEFAULT 0.00 AFTER rainfall,
    ADD COLUMN IF NOT EXISTS water_saved_mm DECIMAL(5,2) NULL DEFAULT 0.00 AFTER water_quantity_mm;
