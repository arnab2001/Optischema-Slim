-- Seeding Golden Dataset Scenarios
CREATE SCHEMA IF NOT EXISTS golden;

-- Scenario A: The "Slam Dunk" (1M row table)
CREATE TABLE IF NOT EXISTS golden.orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    amount DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Fast seeding with generate_series
INSERT INTO golden.orders (user_id, amount, created_at)
SELECT 
    floor(random() * 100000) + 1,
    (random() * 500)::decimal(10,2),
    now() - (random() * interval '1 year')
FROM generate_series(1, 1000000)
ON CONFLICT DO NOTHING;

-- Scenario C: The "Tiny Table" (15 rows)
CREATE TABLE IF NOT EXISTS golden.user_roles (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    description TEXT
);

INSERT INTO golden.user_roles (code, description) VALUES
('ADMIN', 'Administrator'),
('USER', 'Regular User'),
('GUEST', 'Guest User'),
('EDITOR', 'Content Editor'),
('MODERATOR', 'Community Moderator'),
('SUPPORT', 'Customer Support'),
('BILLING', 'Billing Manager'),
('MANAGER', 'General Manager'),
('VIEWER', 'Read-only Viewer'),
('ANALYST', 'Data Analyst'),
('DEVELOPER', 'System Developer'),
('MARKETER', 'Marketing Specialist'),
('SALES', 'Sales Representative'),
('HR', 'Human Resources'),
('SECURITY', 'Security Auditor')
ON CONFLICT DO NOTHING;

-- Scenario D: Function Scan Test
CREATE TABLE IF NOT EXISTS golden.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO golden.users (username, created_at)
SELECT 
    'user_' || i,
    now() - (random() * interval '5 years')
FROM generate_series(1, 10000) s(i)
ON CONFLICT DO NOTHING;

-- Scenario E: Join Bottleneck (Missing Join Key Index)
CREATE TABLE IF NOT EXISTS golden.products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    price DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS golden.product_reviews (
    id SERIAL PRIMARY KEY,
    product_id INTEGER, -- Missing index
    rating INTEGER,
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO golden.products (name, category, price)
SELECT 
    'Product ' || i,
    (ARRAY['Electronics', 'Books', 'Clothing', 'Home'])[floor(random()*4)+1],
    (random()*1000)::decimal(10,2)
FROM generate_series(1, 1000) s(i)
ON CONFLICT DO NOTHING;

INSERT INTO golden.product_reviews (product_id, rating, comment, created_at)
SELECT 
    floor(random()*1000)+1,
    floor(random()*5)+1,
    'Review for product ' || i,
    now() - (random() * interval '6 months')
FROM generate_series(1, 100000) s(i)
ON CONFLICT DO NOTHING;

-- Scenario F: Aggregate Slowness (Sort/Group By on Large Table)
CREATE TABLE IF NOT EXISTS golden.events (
    id SERIAL PRIMARY KEY,
    event_type TEXT,
    user_id INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO golden.events (event_type, user_id, metadata, created_at)
SELECT 
    (ARRAY['click', 'view', 'purchase', 'login', 'logout'])[floor(random()*5)+1],
    floor(random()*10000)+1,
    '{"source": "mobile", "version": "1.2.3"}'::jsonb,
    now() - (random() * interval '30 days')
FROM generate_series(1, 500000) s(i)
ON CONFLICT DO NOTHING;

-- Benchmarking Metadata Storage
CREATE TABLE IF NOT EXISTS golden.benchmark_results (
    id SERIAL PRIMARY KEY,
    scenario_id TEXT,
    query_text TEXT,
    prompt TEXT,
    raw_response TEXT,
    actual_category TEXT,
    expected_category TEXT,
    actual_sql TEXT,
    alignment_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analyze all to ensure stats are fresh for the planner
ANALYZE golden.orders;
ANALYZE golden.user_roles;
ANALYZE golden.users;
ANALYZE golden.products;
ANALYZE golden.product_reviews;
ANALYZE golden.events;
ANALYZE golden.benchmark_results;
