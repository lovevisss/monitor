CREATE DATABASE IF NOT EXISTS `jiankong`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE `jiankong`;

CREATE TABLE IF NOT EXISTS `service` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(128) NOT NULL,
  `target` VARCHAR(512) NOT NULL,
  `check_type` VARCHAR(16) NOT NULL,
  `keyword` VARCHAR(255) NULL,
  `tags` VARCHAR(512) NULL,
  `interval_sec` INT NOT NULL DEFAULT 60,
  `timeout_sec` INT NOT NULL DEFAULT 10,
  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_service_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `monitor_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `service_id` INT NOT NULL,
  `latency_ms` DOUBLE NULL,
  `http_code` INT NULL,
  `result_status` VARCHAR(16) NOT NULL,
  `is_success` TINYINT(1) NOT NULL,
  `error_msg` TEXT NULL,
  `checked_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_monitor_log_service_time` (`service_id`, `checked_at`),
  CONSTRAINT `fk_monitor_log_service`
    FOREIGN KEY (`service_id`) REFERENCES `service`(`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `alert_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `service_id` INT NOT NULL,
  `alert_type` VARCHAR(16) NOT NULL,
  `reason` TEXT NOT NULL,
  `first_occur_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_occur_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `recovered_at` DATETIME NULL,
  `alert_status` VARCHAR(16) NOT NULL DEFAULT 'active',
  PRIMARY KEY (`id`),
  KEY `idx_alert_log_service_state_time` (`service_id`, `alert_status`, `first_occur_at`),
  CONSTRAINT `fk_alert_log_service`
    FOREIGN KEY (`service_id`) REFERENCES `service`(`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `admin_user` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(64) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_admin_user_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `audit_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `admin_username` VARCHAR(64) NOT NULL,
  `action` VARCHAR(64) NOT NULL,
  `target_type` VARCHAR(64) NOT NULL,
  `target_id` VARCHAR(64) NULL,
  `detail` TEXT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audit_log_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `maintenance_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `service_id` INT NOT NULL,
  `admin_username` VARCHAR(64) NOT NULL,
  `content` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_maintenance_log_service_time` (`service_id`, `created_at`),
  CONSTRAINT `fk_maintenance_log_service`
    FOREIGN KEY (`service_id`) REFERENCES `service`(`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

