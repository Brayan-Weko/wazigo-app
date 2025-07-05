-- database/schema.sql

CREATE DATABASE smart_route_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_route_db;

-- Table des utilisateurs
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    google_id VARCHAR(250) UNIQUE NULL,
    email VARCHAR(250) UNIQUE NOT NULL,
    name VARCHAR(250) NOT NULL,
    avatar_url TEXT NULL,
    preferences JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Table des itinéraires sauvegardés
CREATE TABLE saved_routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    name VARCHAR(250) NOT NULL,
    origin_address TEXT NOT NULL,
    origin_lat DECIMAL(10, 8) NOT NULL,
    origin_lng DECIMAL(11, 8) NOT NULL,
    destination_address TEXT NOT NULL,
    destination_lat DECIMAL(10, 8) NOT NULL,
    destination_lng DECIMAL(11, 8) NOT NULL,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Table de l'historique des trajets
CREATE TABLE route_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    session_id VARCHAR(250) NOT NULL,
    origin_address TEXT NOT NULL,
    origin_lat DECIMAL(10, 8) NOT NULL,
    origin_lng DECIMAL(11, 8) NOT NULL,
    destination_address TEXT NOT NULL,
    destination_lat DECIMAL(10, 8) NOT NULL,
    destination_lng DECIMAL(11, 8) NOT NULL,
    selected_route_data JSON NOT NULL,
    alternative_routes JSON NULL,
    traffic_conditions JSON NULL,
    travel_time_seconds INT NOT NULL,
    distance_meters INT NOT NULL,
    optimization_score DECIMAL(5, 2) NOT NULL,
    weather_conditions JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_date (user_id, created_at),
    INDEX idx_session (session_id)
);

-- Table des analytics utilisateur
CREATE TABLE user_analytics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    total_routes_searched INT DEFAULT 0,
    total_time_saved_minutes INT DEFAULT 0,
    total_distance_km DECIMAL(10, 2) DEFAULT 0,
    most_used_origin TEXT NULL,
    most_used_destination TEXT NULL,
    average_optimization_score DECIMAL(5, 2) DEFAULT 0,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Table des sessions (pour utilisateurs non connectés)
CREATE TABLE guest_sessions (
    id VARCHAR(250) PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT NULL,
    preferences JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    INDEX idx_expires (expires_at)
);

-- Table des retours utilisateur
CREATE TABLE feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    session_id VARCHAR(250) NULL,
    route_id INT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT NULL,
    feedback_type ENUM('route_quality', 'app_performance', 'feature_request', 'bug_report') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (route_id) REFERENCES route_history(id) ON DELETE SET NULL
);