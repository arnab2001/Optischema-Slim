-- OptiSchema Sandbox PostgreSQL Initialization Script
-- This script sets up a sandbox database for testing optimization patches

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema for sandbox
CREATE SCHEMA IF NOT EXISTS sandbox;

-- Create a simple test table for optimization demonstrations
CREATE TABLE IF NOT EXISTS sandbox.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sandbox.orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES sandbox.users(id),
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sandbox.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sandbox.order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES sandbox.orders(id),
    product_id INTEGER REFERENCES sandbox.products(id),
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert sample data for testing
INSERT INTO sandbox.users (username, email) VALUES
('john_doe', 'john@example.com'),
('jane_smith', 'jane@example.com'),
('bob_wilson', 'bob@example.com'),
('alice_brown', 'alice@example.com'),
('charlie_davis', 'charlie@example.com');

INSERT INTO sandbox.products (name, price, category) VALUES
('Laptop', 999.99, 'Electronics'),
('Mouse', 29.99, 'Electronics'),
('Keyboard', 79.99, 'Electronics'),
('Monitor', 299.99, 'Electronics'),
('Headphones', 149.99, 'Electronics'),
('Book', 19.99, 'Books'),
('Pen', 2.99, 'Office'),
('Paper', 9.99, 'Office');

INSERT INTO sandbox.orders (user_id, amount, status) VALUES
(1, 1029.98, 'completed'),
(2, 449.98, 'pending'),
(3, 79.99, 'completed'),
(4, 299.99, 'shipped'),
(5, 19.99, 'completed');

INSERT INTO sandbox.order_items (order_id, product_id, quantity, price) VALUES
(1, 1, 1, 999.99),
(1, 2, 1, 29.99),
(2, 4, 1, 299.99),
(2, 5, 1, 149.99),
(3, 3, 1, 79.99),
(4, 4, 1, 299.99),
(5, 6, 1, 19.99);

-- Create some intentionally problematic queries for optimization testing
-- These queries will be slow and can be optimized

-- Query 1: Missing index on email column
-- This will be slow when searching by email
SELECT * FROM sandbox.users WHERE email = 'john@example.com';

-- Query 2: Missing index on user_id in orders
-- This will be slow when joining users and orders
SELECT u.username, o.amount, o.status 
FROM sandbox.users u 
JOIN sandbox.orders o ON u.id = o.user_id 
WHERE u.username = 'john_doe';

-- Query 3: Missing index on category in products
-- This will be slow when filtering by category
SELECT * FROM sandbox.products WHERE category = 'Electronics';

-- Query 4: Complex join without proper indexes
-- This will be slow due to multiple joins
SELECT 
    u.username,
    p.name as product_name,
    oi.quantity,
    oi.price,
    o.status
FROM sandbox.users u
JOIN sandbox.orders o ON u.id = o.user_id
JOIN sandbox.order_items oi ON o.id = oi.order_id
JOIN sandbox.products p ON oi.product_id = p.id
WHERE u.username = 'john_doe';

-- Create functions for updating timestamps
CREATE OR REPLACE FUNCTION sandbox.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON sandbox.users 
    FOR EACH ROW EXECUTE FUNCTION sandbox.update_updated_at_column();

-- Grant permissions
GRANT USAGE ON SCHEMA sandbox TO sandbox;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA sandbox TO sandbox;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA sandbox TO sandbox;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA sandbox TO sandbox;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'OptiSchema sandbox database initialized successfully!';
    RAISE NOTICE 'Extensions enabled: pg_stat_statements, uuid-ossp';
    RAISE NOTICE 'Schema created: sandbox';
    RAISE NOTICE 'Tables created: users, orders, products, order_items';
    RAISE NOTICE 'Sample data inserted for testing';
    RAISE NOTICE 'Problematic queries ready for optimization testing';
END $$; 