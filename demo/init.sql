-- Enable pg_stat_statements for monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
-- Enable HypoPG for hypothetical indexing
CREATE EXTENSION IF NOT EXISTS hypopg;

-- 1. Create a "Users" table with a TEXT id (inefficient) and no index on email
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Create an "Orders" table with NO foreign key index on user_id
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id TEXT, -- References users(id) but no index!
    amount DECIMAL(10, 2),
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata TEXT -- Large text field
);

-- 3. Populate Users (Generate 10,000 users)
INSERT INTO users (id, name, email, created_at)
SELECT 
    'user_' || i, 
    'User ' || i, 
    'user' || i || '@example.com',
    NOW() - (random() * interval '365 days')
FROM generate_series(1, 10000) AS i;

-- 4. Populate Orders (Generate 50,000 orders)
INSERT INTO orders (user_id, amount, status, created_at, metadata)
SELECT 
    'user_' || (floor(random() * 10000) + 1),
    (random() * 1000)::decimal(10, 2),
    CASE WHEN random() < 0.9 THEN 'completed' ELSE 'pending' END,
    NOW() - (random() * interval '365 days'),
    repeat('some metadata ', 5)
FROM generate_series(1, 50000) AS i;

-- Reset stats so we don't see the massive INSERTs in the dashboard
SELECT pg_stat_statements_reset();

-- 5. RUN SOME BAD QUERIES TO POPULATE pg_stat_statements

-- A. Slow Join (Missing index on orders.user_id)
-- Run it 5 times
DO $$ 
BEGIN 
    PERFORM count(*) 
    FROM orders o 
    JOIN users u ON o.user_id = u.id 
    WHERE u.email LIKE '%@example.com'; 
    
    PERFORM count(*) 
    FROM orders o 
    JOIN users u ON o.user_id = u.id 
    WHERE u.email LIKE '%@example.com';

    PERFORM count(*) 
    FROM orders o 
    JOIN users u ON o.user_id = u.id 
    WHERE u.email LIKE '%@example.com';
END $$;

-- B. Full Table Scan on Date (No index on created_at)
SELECT count(*) FROM orders WHERE created_at < NOW() - interval '30 days';
SELECT count(*) FROM orders WHERE created_at < NOW() - interval '60 days';

-- C. Like Query with Leading Wildcard (Cannot use B-Tree even if it existed)
SELECT * FROM users WHERE email LIKE '%99@example.com';

-- D. Aggregation without Index
SELECT user_id, sum(amount) FROM orders GROUP BY user_id ORDER BY sum(amount) DESC LIMIT 10;

-- Reset stats so we see fresh data? No, keep them.
