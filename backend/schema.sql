-- Link Shortener Database Schema
-- Run this on your MySQL server

-- Create database
CREATE DATABASE IF NOT EXISTS link_shortener
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE link_shortener;
-- Create user (change password!)
--- CREATE USER IF NOT EXISTS 'linkshortener'@'localhost' IDENTIFIED BY 'your_secure_password_here';
--- GRANT ALL PRIVILEGES ON linkshortener.* TO 'linkshortener'@'localhost';
--- FLUSH PRIVILEGES;

-- Links table
CREATE TABLE IF NOT EXISTS links (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    short_code VARCHAR(20) NOT NULL UNIQUE,
    original_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    click_count BIGINT DEFAULT 0 NOT NULL,
    creator_ip_hash VARCHAR(64) NULL,
    
    INDEX idx_short_code_active (short_code, is_active),
    INDEX idx_expires_at (expires_at),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Clicks table (analytics)
CREATE TABLE IF NOT EXISTS clicks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    link_id BIGINT NOT NULL,
    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_hash VARCHAR(64) NULL,
    country VARCHAR(2) NULL,
    referer VARCHAR(500) NULL,
    user_agent_type VARCHAR(20) NULL,
    
    INDEX idx_link_clicked (link_id, clicked_at),
    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Blocked domains table
CREATE TABLE IF NOT EXISTS blocked_domains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain VARCHAR(255) NOT NULL UNIQUE,
    reason VARCHAR(255) NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_domain (domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert some common spam domains
INSERT IGNORE INTO blocked_domains (domain, reason) VALUES
    ('bit.ly', 'prevent double-shortening'),
    ('tinyurl.com', 'prevent double-shortening'),
    ('t.co', 'prevent double-shortening'),
    ('goo.gl', 'prevent double-shortening');
