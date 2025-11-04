-- ==============================
-- Secure and Reliable Healthcare Appointment System
-- Database Initialization Script
-- PostgreSQL Version: 18
-- ==============================

-- 如果数据库还没创建，请先执行：
-- CREATE DATABASE healthcare_system;

-- 切换到数据库
-- \c healthcare_system;

-- ==============================
-- 1. USERS TABLE
-- ==============================
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('patient', 'doctor', 'admin')),
    email VARCHAR(150) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================
-- 2. DOCTOR_AVAILABILITY TABLE
-- ==============================
CREATE TABLE doctor_availability (
    availability_id SERIAL PRIMARY KEY,
    doctor_id INT NOT NULL,
    available_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_doctor
        FOREIGN KEY (doctor_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

-- ==============================
-- 3. APPOINTMENTS TABLE
-- ==============================
CREATE TABLE appointments (
    appointment_id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_patient
        FOREIGN KEY (patient_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_doctor_appointment
        FOREIGN KEY (doctor_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

-- ==============================
-- 4. AUDIT_LOG TABLE
-- ==============================
CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    target_table VARCHAR(50),
    target_id INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

-- ==============================
-- Indexing & Optimization
-- ==============================
CREATE INDEX idx_user_role ON users(role);
CREATE INDEX idx_doctor_date ON doctor_availability(doctor_id, available_date);
CREATE INDEX idx_appointment_date ON appointments(appointment_date);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);

-- ==============================
-- Verification
-- ==============================
-- 查看所有表
-- \dt
