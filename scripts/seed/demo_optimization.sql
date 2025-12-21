-- OptiSchema Index Optimization Demonstration
-- This script shows the before/after performance impact of indexing

-- ===========================================
-- DEMONSTRATION 1: Orders by User ID
-- ===========================================

-- Show current indexes on demo_orders
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'demo_orders'
ORDER BY indexname;

-- Test query performance (should use index)
EXPLAIN (ANALYZE, BUFFERS) 
SELECT COUNT(*) 
FROM demo_orders 
WHERE user_id = 42;

-- ===========================================
-- DEMONSTRATION 2: Products by Category
-- ===========================================

-- Show the dramatic difference with our test table
SELECT 'BEFORE INDEX - Sequential Scan' as test_phase;
EXPLAIN (ANALYZE, BUFFERS) 
SELECT COUNT(*) 
FROM demo_products_no_index 
WHERE category = 'Electronics';

-- Show indexes on our test table
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'demo_products_no_index'
ORDER BY indexname;

SELECT 'AFTER INDEX - Index Scan' as test_phase;
EXPLAIN (ANALYZE, BUFFERS) 
SELECT COUNT(*) 
FROM demo_products_no_index 
WHERE category = 'Electronics';

-- ===========================================
-- DEMONSTRATION 3: Show All Indexes Created
-- ===========================================

SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes 
WHERE schemaname = 'optischema'
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;

-- ===========================================
-- DEMONSTRATION 4: Performance Metrics
-- ===========================================

-- Show query performance from pg_stat_statements
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows,
    shared_blks_hit,
    shared_blks_read,
    (shared_blks_hit::float / (shared_blks_hit + shared_blks_read) * 100) as cache_hit_ratio
FROM pg_stat_statements 
WHERE query LIKE '%demo_%'
ORDER BY total_exec_time DESC
LIMIT 10;

-- ===========================================
-- DEMONSTRATION 5: Create More Indexes
-- ===========================================

-- Create additional indexes for demonstration
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_demo_orders_status ON demo_orders(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_demo_orders_order_date ON demo_orders(order_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_demo_users_created_at ON demo_users(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_demo_logs_user_id ON demo_logs(user_id);

-- Show the new indexes
SELECT 
    'NEW INDEXES CREATED' as status,
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes 
WHERE schemaname = 'optischema'
  AND indexname IN (
    'idx_demo_orders_status',
    'idx_demo_orders_order_date', 
    'idx_demo_users_created_at',
    'idx_demo_logs_user_id'
  );

-- ===========================================
-- DEMONSTRATION 6: Test New Indexes
-- ===========================================

-- Test status index
EXPLAIN (ANALYZE, BUFFERS) 
SELECT COUNT(*) 
FROM demo_orders 
WHERE status = 'completed';

-- Test date range index
EXPLAIN (ANALYZE, BUFFERS) 
SELECT COUNT(*) 
FROM demo_orders 
WHERE order_date > '2024-01-01';

-- Test user activity index
EXPLAIN (ANALYZE, BUFFERS) 
SELECT COUNT(*) 
FROM demo_logs 
WHERE user_id = 100;
