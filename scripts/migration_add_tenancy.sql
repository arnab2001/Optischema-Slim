-- OptiSchema Multi-Tenant Migration Script
-- This script adds tenant support to all existing tables
-- Run this after the initial schema is created

-- Step 1: Create tenants table
CREATE TABLE IF NOT EXISTS optischema.tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 2: Create tenant_connections table (simplified, no encryption for now)
CREATE TABLE IF NOT EXISTS optischema.tenant_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    database_name TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL, -- plaintext for now
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

-- Step 3: Add tenant_id columns to all existing tables
-- (We'll add them as nullable first, then backfill, then make NOT NULL)

-- Add tenant_id to query_metrics
ALTER TABLE optischema.query_metrics 
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES optischema.tenants(id);

-- Add tenant_id to analysis_results  
ALTER TABLE optischema.analysis_results 
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES optischema.tenants(id);

-- Add tenant_id to recommendations
ALTER TABLE optischema.recommendations 
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES optischema.tenants(id);

-- Add tenant_id to sandbox_tests
ALTER TABLE optischema.sandbox_tests 
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES optischema.tenants(id);

-- Add tenant_id to audit_logs
ALTER TABLE optischema.audit_logs 
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES optischema.tenants(id);

-- Add tenant_id to connection_baselines
ALTER TABLE optischema.connection_baselines 
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES optischema.tenants(id);

-- Add tenant_id to index_recommendations
ALTER TABLE optischema.index_recommendations 
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES optischema.tenants(id);

-- Add tenant_id to benchmark_jobs
ALTER TABLE IF NOT EXISTS optischema.benchmark_jobs
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES optischema.tenants(id);

-- Create llm_cache table for tenant-aware caching
CREATE TABLE IF NOT EXISTS optischema.llm_cache (
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (tenant_id, key)
);

-- Step 4: Create a default tenant for existing data
INSERT INTO optischema.tenants (id, name, status) 
VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'active')
ON CONFLICT (name) DO NOTHING;

-- Step 5: Backfill existing data with default tenant
UPDATE optischema.query_metrics 
SET tenant_id = '00000000-0000-0000-0000-000000000001' 
WHERE tenant_id IS NULL;

UPDATE optischema.analysis_results 
SET tenant_id = '00000000-0000-0000-0000-000000000001' 
WHERE tenant_id IS NULL;

UPDATE optischema.recommendations 
SET tenant_id = '00000000-0000-0000-0000-000000000001' 
WHERE tenant_id IS NULL;

UPDATE optischema.sandbox_tests 
SET tenant_id = '00000000-0000-0000-0000-000000000001' 
WHERE tenant_id IS NULL;

UPDATE optischema.audit_logs 
SET tenant_id = '00000000-0000-0000-0000-000000000001' 
WHERE tenant_id IS NULL;

UPDATE optischema.connection_baselines 
SET tenant_id = '00000000-0000-0000-0000-000000000001' 
WHERE tenant_id IS NULL;

UPDATE optischema.index_recommendations 
SET tenant_id = '00000000-0000-0000-0000-000000000001' 
WHERE tenant_id IS NULL;

UPDATE optischema.benchmark_jobs
SET tenant_id = '00000000-0000-0000-0000-000000000001'
WHERE tenant_id IS NULL;

-- Step 6: Make tenant_id columns NOT NULL
ALTER TABLE optischema.query_metrics 
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE optischema.analysis_results 
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE optischema.recommendations 
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE optischema.sandbox_tests 
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE optischema.audit_logs 
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE optischema.connection_baselines 
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE optischema.index_recommendations 
ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE IF EXISTS optischema.benchmark_jobs
ALTER COLUMN tenant_id SET NOT NULL;

-- Step 7: Update foreign key constraints to include tenant_id
-- Drop existing foreign keys that don't include tenant_id
ALTER TABLE optischema.sandbox_tests 
DROP CONSTRAINT IF EXISTS sandbox_tests_recommendation_id_fkey;

ALTER TABLE optischema.audit_logs 
DROP CONSTRAINT IF EXISTS audit_logs_recommendation_id_fkey;

-- Recreate foreign keys with tenant_id
ALTER TABLE optischema.sandbox_tests 
ADD CONSTRAINT sandbox_tests_recommendation_id_fkey 
FOREIGN KEY (tenant_id, recommendation_id) 
REFERENCES optischema.recommendations(tenant_id, id);

ALTER TABLE optischema.audit_logs 
ADD CONSTRAINT audit_logs_recommendation_id_fkey 
FOREIGN KEY (tenant_id, recommendation_id) 
REFERENCES optischema.recommendations(tenant_id, id);

-- Step 8: Update unique constraints to include tenant_id
-- Drop existing unique constraints
ALTER TABLE optischema.connection_baselines 
DROP CONSTRAINT IF EXISTS connection_baselines_connection_id_key;

-- Add new unique constraints with tenant_id
ALTER TABLE optischema.connection_baselines 
ADD CONSTRAINT connection_baselines_tenant_connection_id_key 
UNIQUE (tenant_id, connection_id);

-- Step 9: Create new indexes with tenant_id
-- Drop old indexes that don't include tenant_id
DROP INDEX IF EXISTS optischema.idx_query_metrics_hash;
DROP INDEX IF EXISTS optischema.idx_analysis_results_hash;
DROP INDEX IF EXISTS optischema.idx_recommendations_hash;
DROP INDEX IF EXISTS optischema.idx_audit_logs_recommendation_id;
DROP INDEX IF EXISTS optischema.idx_connection_baselines_connection_id;
DROP INDEX IF EXISTS optischema.idx_benchmark_jobs_status;
DROP INDEX IF EXISTS optischema.idx_benchmark_jobs_recommendation_id;
DROP INDEX IF EXISTS optischema.idx_benchmark_jobs_created_at;

-- Create new indexes with tenant_id
CREATE INDEX idx_query_metrics_tenant_hash ON optischema.query_metrics(tenant_id, query_hash);
CREATE INDEX idx_query_metrics_tenant_created_at ON optischema.query_metrics(tenant_id, created_at);
CREATE INDEX idx_analysis_results_tenant_hash ON optischema.analysis_results(tenant_id, query_hash);
CREATE INDEX idx_recommendations_tenant_hash ON optischema.recommendations(tenant_id, query_hash);
CREATE INDEX idx_recommendations_tenant_type ON optischema.recommendations(tenant_id, recommendation_type);
CREATE INDEX idx_recommendations_tenant_applied ON optischema.recommendations(tenant_id, applied);
CREATE INDEX idx_audit_logs_tenant_action_type ON optischema.audit_logs(tenant_id, action_type);
CREATE INDEX idx_audit_logs_tenant_created_at ON optischema.audit_logs(tenant_id, created_at);
CREATE INDEX idx_audit_logs_tenant_user_id ON optischema.audit_logs(tenant_id, user_id);
CREATE INDEX idx_audit_logs_tenant_recommendation_id ON optischema.audit_logs(tenant_id, recommendation_id);
CREATE INDEX idx_connection_baselines_tenant_connection_id ON optischema.connection_baselines(tenant_id, connection_id);
CREATE INDEX idx_connection_baselines_tenant_is_active ON optischema.connection_baselines(tenant_id, is_active);
CREATE INDEX idx_index_recommendations_tenant_schema_table ON optischema.index_recommendations(tenant_id, schema_name, table_name);
CREATE INDEX idx_index_recommendations_tenant_risk_level ON optischema.index_recommendations(tenant_id, risk_level);
CREATE INDEX idx_index_recommendations_tenant_days_unused ON optischema.index_recommendations(tenant_id, days_unused);
CREATE INDEX idx_benchmark_jobs_tenant_status ON optischema.benchmark_jobs(tenant_id, status);
CREATE INDEX idx_benchmark_jobs_tenant_created_at ON optischema.benchmark_jobs(tenant_id, created_at);
CREATE INDEX idx_benchmark_jobs_tenant_recommendation_id ON optischema.benchmark_jobs(tenant_id, recommendation_id);

-- Step 10: Update views to include tenant filtering
DROP VIEW IF EXISTS optischema.hot_queries;
DROP VIEW IF EXISTS optischema.recent_recommendations;

CREATE OR REPLACE VIEW optischema.hot_queries AS
SELECT 
    tenant_id,
    query_hash,
    query_text,
    total_time,
    calls,
    mean_time,
    ROUND((total_time / NULLIF(SUM(total_time) OVER (PARTITION BY tenant_id), 0)) * 100, 2) as percentage_of_total_time
FROM optischema.query_metrics
WHERE created_at >= NOW() - INTERVAL '1 hour'
ORDER BY tenant_id, total_time DESC;

CREATE OR REPLACE VIEW optischema.recent_recommendations AS
SELECT 
    r.tenant_id,
    r.*,
    qm.query_text,
    qm.mean_time as current_mean_time
FROM optischema.recommendations r
JOIN optischema.query_metrics qm ON r.tenant_id = qm.tenant_id AND r.query_hash = qm.query_hash
WHERE r.created_at >= NOW() - INTERVAL '24 hours'
ORDER BY r.tenant_id, r.created_at DESC;

-- Step 11: Add triggers for tenant tables
CREATE TRIGGER update_tenants_updated_at 
    BEFORE UPDATE ON optischema.tenants 
    FOR EACH ROW EXECUTE FUNCTION optischema.update_updated_at_column();

CREATE TRIGGER update_tenant_connections_updated_at 
    BEFORE UPDATE ON optischema.tenant_connections 
    FOR EACH ROW EXECUTE FUNCTION optischema.update_updated_at_column();

-- Step 12: Grant permissions for new tables
GRANT ALL PRIVILEGES ON optischema.tenants TO optischema;
GRANT ALL PRIVILEGES ON optischema.tenant_connections TO optischema;

-- Step 13: Log successful migration
DO $$
BEGIN
    RAISE NOTICE 'Multi-tenant migration completed successfully!';
    RAISE NOTICE 'Created tables: tenants, tenant_connections';
    RAISE NOTICE 'Added tenant_id to all existing tables';
    RAISE NOTICE 'Backfilled existing data with default tenant';
    RAISE NOTICE 'Updated constraints and indexes for multi-tenancy';
    RAISE NOTICE 'Updated views to be tenant-aware';
END $$;
