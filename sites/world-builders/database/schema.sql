-- World Builders Construction: lead database (MySQL 5.7+ / MariaDB 10.3+, as provided by Hostinger).
-- Import once in hPanel > Databases > phpMyAdmin > Import, after creating an empty database and user.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS leads (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  created_at   DATETIME        NOT NULL,
  updated_at   DATETIME        NULL,
  name         VARCHAR(120)    NOT NULL,
  phone        VARCHAR(32)     NOT NULL,
  email        VARCHAR(190)    NULL,
  location     VARCHAR(120)    NOT NULL,
  project      VARCHAR(60)     NOT NULL,
  size         VARCHAR(20)     NOT NULL,
  plans        VARCHAR(30)     NOT NULL,
  budget_jmd   VARCHAR(20)     NOT NULL,
  timeframe    VARCHAR(20)     NOT NULL,
  message      TEXT            NULL,
  intent       VARCHAR(20)     NOT NULL DEFAULT 'quote',
  variant      VARCHAR(40)     NULL,
  page         VARCHAR(255)    NULL,
  ip_hash      CHAR(64)        NOT NULL,
  user_agent   VARCHAR(255)    NULL,
  status       VARCHAR(20)     NOT NULL DEFAULT 'new',
  notified     TINYINT(1)      NOT NULL DEFAULT 0,
  notes        TEXT            NULL,
  PRIMARY KEY (id),
  KEY idx_status_created (status, created_at),
  KEY idx_ip_created (ip_hash, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS login_attempts (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ip_hash    CHAR(64)        NOT NULL,
  created_at DATETIME        NOT NULL,
  PRIMARY KEY (id),
  KEY idx_ip_created (ip_hash, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
