-- Основные таблицы 
CREATE TABLE clients (
    id UUID PRIMARY KEY,
    passport_hash VARCHAR(64) UNIQUE, -- Хеш паспорта для поиска
    full_name_encrypted BYTEA, -- Шифрованное ФИО
    phone_hash VARCHAR(64),
    email_hash VARCHAR(64),
    monthly_income DECIMAL(12,2),
    employment_type VARCHAR(20),
    experience_months INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE vehicles (
    id UUID PRIMARY KEY,
    brand VARCHAR(50),
    model VARCHAR(50),
    year INT,
    price DECIMAL(12,2),
    vin_hash VARCHAR(64) UNIQUE,
    category VARCHAR(10),
    stock_id VARCHAR(50) -- ID из системы учета автосалона
);

CREATE TABLE calculations (
    id UUID PRIMARY KEY,
    client_id UUID REFERENCES clients(id),
    vehicle_id UUID REFERENCES vehicles(id),
    financing_type VARCHAR(10),
    amount DECIMAL(12,2),
    initial_payment DECIMAL(12,2),
    months INT,
    monthly_payment DECIMAL(12,2),
    total_payment DECIMAL(12,2),
    effective_rate DECIMAL(5,2),
    approval_status VARCHAR(20),
    approval_score DECIMAL(5,2),
    session_data JSONB, -- Все параметры расчета
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_configs (
    id UUID PRIMARY KEY,
    product_type VARCHAR(20),
    name VARCHAR(100),
    min_amount DECIMAL(12,2),
    max_amount DECIMAL(12,2),
    min_months INT,
    max_months INT,
    base_rate DECIMAL(5,2),
    conditions JSONB,
    is_active BOOLEAN DEFAULT true,
    valid_from DATE,
    valid_to DATE
);

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(50), -- ID менеджера
    client_id UUID REFERENCES clients(id),
    calculation_id UUID REFERENCES calculations(id),
    ip_address INET,
    user_agent TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);


-- Проверка расчетов по дням
SELECT 
    DATE(created_at) as день,
    COUNT(*) as "количество расчетов",
    AVG(monthly_payment) as "средний платеж",
    AVG(approval_score) as "средний балл"
FROM calculations 
WHERE created_at BETWEEN '2025-12-28' AND '2025-12-30'
GROUP BY DATE(created_at)
ORDER BY день;



-- 1. Очистка таблиц (при необходимости)
TRUNCATE TABLE calculations CASCADE;
TRUNCATE TABLE clients CASCADE;
TRUNCATE TABLE vehicles CASCADE;
TRUNCATE TABLE user_sessions CASCADE;

-- 2. Заполнение таблицы клиентов (clients)
INSERT INTO clients (id, passport_hash, full_name_encrypted, monthly_income, employment_type, experience_months, created_at, updated_at) VALUES
-- Данные зашифрованы для примера (в реальности используйте pgcrypto)
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '8d969eef6ecad3c29a3a629280e686cf', '\x536572676579204976616e6f76', 85000.00, 'employed', 24, '2025-12-28 09:15:00', '2025-12-28 09:15:00'),
('b1ffc11e-9c0b-4ef8-bb6d-6bb9bd380a12', '5e8dd316726c643bd2e3d3b2b764a2f1', '\x416e6e6120506574726f7661', 120000.00, 'business_owner', 60, '2025-12-28 11:30:00', '2025-12-28 11:30:00'),
('c2aaee22-9c0b-4ef8-bb6d-6bb9bd380a13', 'd6a6bc0db10694a2d90e3a69648f3a03', '\x446d69747279205369646f726f76', 65000.00, 'employed', 18, '2025-12-29 14:45:00', '2025-12-29 14:45:00'),
('d3bbff33-9c0b-4ef8-bb6d-6bb9bd380a14', '3c5d5c8c9c5d5c8c9c5d5c8c9c5d5c8c', '\x456c656e61204b6f7a6c6f7661', 95000.00, 'self_employed', 36, '2025-12-29 16:20:00', '2025-12-29 16:20:00'),
('e4cc0011-9c0b-4ef8-bb6d-6bb9bd380a15', '7f7a5c8c9c5d5c8c9c5d5c8c9c5d5c8d', '\x4d6178696d20496e6f7a656d746576', 180000.00, 'business_owner', 120, '2025-12-30 10:10:00', '2025-12-30 10:10:00');

-- 3. Заполнение таблицы автомобилей (vehicles)
INSERT INTO vehicles (id, brand, model, year, price, vin_hash, category, stock_id, created_at) VALUES
('f5dd1122-9c0b-4ef8-bb6d-6bb9bd380a21', 'Volkswagen', 'Tiguan', 2024, 3200000.00, 'WVGZZZ5NZMW123456', 'new', 'VW-TIG-001', '2025-12-01 10:00:00'),
('g6ee2233-9c0b-4ef8-bb6d-6bb9bd380a22', 'Skoda', 'Kodiaq', 2024, 2800000.00, 'TMBZZZ6TZJ0123456', 'new', 'SKO-KOD-002', '2025-12-05 11:00:00'),
('h7ff3344-9c0b-4ef8-bb6d-6bb9bd380a23', 'Audi', 'Q5', 2023, 4500000.00, 'WAUZZZFY2N1234567', 'used', 'AUD-Q5-003', '2025-12-10 12:00:00'),
('i8gg4455-9c0b-4ef8-bb6d-6bb9bd380a24', 'Volkswagen', 'Polo', 2024, 1500000.00, 'WVWZZZ6RZEY123456', 'new', 'VW-POL-004', '2025-12-15 13:00:00'),
('j9hh5566-9c0b-4ef8-bb6d-6bb9bd380a25', 'Skoda', 'Octavia', 2022, 1800000.00, 'TMBJJ7NE5J0123456', 'used', 'SKO-OCT-005', '2025-12-20 14:00:00');

-- 4. Заполнение таблицы продуктов (product_configs)
INSERT INTO product_configs (id, product_type, name, min_amount, max_amount, min_months, max_months, base_rate, conditions, is_active, valid_from, valid_to) VALUES
('k1ii6677-9c0b-4ef8-bb6d-6bb9bd380a31', 'credit', 'Стандартный кредит', 100000.00, 5000000.00, 12, 84, 15.9, '{"min_initial": 0.15, "available_for": ["new", "used"], "insurance_required": true}', true, '2025-01-01', '2026-12-31'),
('l2jj7788-9c0b-4ef8-bb6d-6bb9bd380a32', 'credit', 'Премиум кредит', 500000.00, 10000000.00, 12, 60, 14.9, '{"min_initial": 0.20, "available_for": ["new"], "insurance_required": true, "income_requirement": 80000}', true, '2025-01-01', '2026-12-31'),
('m3kk8899-9c0b-4ef8-bb6d-6bb9bd380a33', 'leasing', 'Стандартный лизинг', 300000.00, 10000000.00, 12, 60, 14.9, '{"min_initial": 0.10, "residual_percent": 0.20, "available_for": ["new", "used"], "vat_included": true}', true, '2025-01-01', '2026-12-31'),
('n4ll9900-9c0b-4ef8-bb6d-6bb9bd380a34', 'leasing', 'Бизнес-лизинг', 1000000.00, 20000000.00, 6, 36, 13.9, '{"min_initial": 0.05, "residual_percent": 0.10, "available_for": ["new"], "for_business_only": true}', true, '2025-01-01', '2026-12-31');

-- 5. Заполнение таблицы расчетов (calculations) за 28-30 декабря 2025
INSERT INTO calculations (id, client_id, vehicle_id, financing_type, amount, initial_payment, months, monthly_payment, total_payment, effective_rate, approval_status, approval_score, session_data, created_at) VALUES
-- 28 декабря 2025
('o5mm0011-9c0b-4ef8-bb6d-6bb9bd380a41', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'f5dd1122-9c0b-4ef8-bb6d-6bb9bd380a21', 'credit', 3200000.00, 800000.00, 60, 52045.50, 3122730.00, 16.2, 'pre_approved', 78.5, '{"insurance_included": true, "life_insurance": false, "product_id": "k1ii6677-9c0b-4ef8-bb6d-6bb9bd380a31"}', '2025-12-28 09:30:00'),
('p6nn0022-9c0b-4ef8-bb6d-6bb9bd380a42', 'b1ffc11e-9c0b-4ef8-bb6d-6bb9bd380a12', 'h7ff3344-9c0b-4ef8-bb6d-6bb9bd380a23', 'leasing', 4500000.00, 900000.00, 36, 128450.25, 4624209.00, 15.5, 'pre_approved', 92.3, '{"insurance_included": true, "life_insurance": true, "product_id": "m3kk8899-9c0b-4ef8-bb6d-6bb9bd380a33"}', '2025-12-28 11:45:00'),

-- 29 декабря 2025
('q7oo0033-9c0b-4ef8-bb6d-6bb9bd380a43', 'c2aaee22-9c0b-4ef8-bb6d-6bb9bd380a13', 'i8gg4455-9c0b-4ef8-bb6d-6bb9bd380a24', 'credit', 1500000.00, 300000.00, 48, 32567.80, 1563254.40, 17.8, 'conditional_approval', 62.1, '{"insurance_included": true, "life_insurance": false, "product_id": "k1ii6677-9c0b-4ef8-bb6d-6bb9bd380a31"}', '2025-12-29 15:00:00'),
('r8pp0044-9c0b-4ef8-bb6d-6bb9bd380a44', 'd3bbff33-9c0b-4ef8-bb6d-6bb9bd380a14', 'g6ee2233-9c0b-4ef8-bb6d-6bb9bd380a22', 'credit', 2800000.00, 700000.00, 72, 39678.90, 2856480.80, 16.5, 'pre_approved', 85.7, '{"insurance_included": false, "life_insurance": false, "product_id": "k1ii6677-9c0b-4ef8-bb6d-6bb9bd380a31"}', '2025-12-29 16:35:00'),

-- 30 декабря 2025
('s9qq0055-9c0b-4ef8-bb6d-6bb9bd380a45', 'e4cc0011-9c0b-4ef8-bb6d-6bb9bd380a15', 'f5dd1122-9c0b-4ef8-bb6d-6bb9bd380a21', 'leasing', 3200000.00, 160000.00, 24, 162345.60, 3896294.40, 14.9, 'pre_approved', 96.5, '{"insurance_included": true, "life_insurance": true, "product_id": "n4ll9900-9c0b-4ef8-bb6d-6bb9bd380a34"}', '2025-12-30 10:30:00'),
('t0rr0066-9c0b-4ef8-bb6d-6bb9bd380a46', 'b1ffc11e-9c0b-4ef8-bb6d-6bb9bd380a12', 'j9hh5566-9c0b-4ef8-bb6d-6bb9bd380a25', 'credit', 1800000.00, 450000.00, 36, 47890.25, 1724049.00, 16.9, 'rejected', 45.2, '{"insurance_included": true, "life_insurance": false, "product_id": "l2jj7788-9c0b-4ef8-bb6d-6bb9bd380a32", "rejection_reason": "Высокое соотношение платеж/доход"}', '2025-12-30 14:15:00');

-- 6. Заполнение таблицы пользовательских сессий (user_sessions)
INSERT INTO user_sessions (id, user_id, client_id, calculation_id, ip_address, user_agent, started_at, ended_at) VALUES
('u1ss0077-9c0b-4ef8-bb6d-6bb9bd380a51', 'manager_ivanov', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'o5mm0011-9c0b-4ef8-bb6d-6bb9bd380a41', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', '2025-12-28 09:15:00', '2025-12-28 09:45:00'),
('v2tt0088-9c0b-4ef8-bb6d-6bb9bd380a52', 'manager_petrova', 'b1ffc11e-9c0b-4ef8-bb6d-6bb9bd380a12', 'p6nn0022-9c0b-4ef8-bb6d-6bb9bd380a42', '192.168.1.101', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36', '2025-12-28 11:30:00', '2025-12-28 12:15:00'),
('w3uu0099-9c0b-4ef8-bb6d-6bb9bd380a53', 'manager_sidorov', 'c2aaee22-9c0b-4ef8-bb6d-6bb9bd380a13', 'q7oo0033-9c0b-4ef8-bb6d-6bb9bd380a43', '192.168.1.102', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0', '2025-12-29 14:45:00', '2025-12-29 15:20:00'),
('x4vv0100-9c0b-4ef8-bb6d-6bb9bd380a54', 'manager_ivanov', 'd3bbff33-9c0b-4ef8-bb6d-6bb9bd380a14', 'r8pp0044-9c0b-4ef8-bb6d-6bb9bd380a44', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', '2025-12-29 16:20:00', '2025-12-29 16:50:00'),
('y5ww0111-9c0b-4ef8-bb6d-6bb9bd380a55', 'manager_kozlov', 'e4cc0011-9c0b-4ef8-bb6d-6bb9bd380a15', 's9qq0055-9c0b-4ef8-bb6d-6bb9bd380a45', '192.168.1.103', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36', '2025-12-30 10:10:00', '2025-12-30 10:50:00'),
('z6xx0122-9c0b-4ef8-bb6d-6bb9bd380a56', 'manager_petrova', 'b1ffc11e-9c0b-4ef8-bb6d-6bb9bd380a12', 't0rr0066-9c0b-4ef8-bb6d-6bb9bd380a46', '192.168.1.101', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0', '2025-12-30 14:00:00', '2025-12-30 14:30:00');

-- 7. Статистика после заполнения
SELECT 'База данных заполнена тестовыми данными за период 28-30 декабря 2025 года' as message;

SELECT 
    'Клиенты' as table_name,
    COUNT(*) as record_count
FROM clients
UNION ALL
SELECT 
    'Автомобили',
    COUNT(*)
FROM vehicles
UNION ALL
SELECT 
    'Продукты',
    COUNT(*)
FROM product_configs
UNION ALL
SELECT 
    'Расчеты',
    COUNT(*)
FROM calculations
UNION ALL
SELECT 
    'Сессии',
    COUNT(*)
FROM user_sessions;

-- 8. Аналитика по датам расчетов
SELECT 
    DATE(created_at) as calculation_date,
    COUNT(*) as calculations_count,
    SUM(CASE WHEN approval_status = 'pre_approved' THEN 1 ELSE 0 END) as approved,
    SUM(CASE WHEN approval_status = 'rejected' THEN 1 ELSE 0 END) as rejected,
    ROUND(AVG(approval_score), 1) as avg_score
FROM calculations
WHERE created_at BETWEEN '2025-12-28' AND '2025-12-30 23:59:59'
GROUP BY DATE(created_at)
ORDER BY calculation_date;