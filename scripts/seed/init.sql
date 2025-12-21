-- OptiSchema PostgreSQL Initialization Script
-- This script sets up the database with required extensions and basic structure

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema for OptiSchema
CREATE SCHEMA IF NOT EXISTS optischema;

-- Core multi-tenant tables
CREATE TABLE IF NOT EXISTS optischema.tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'active' CHECK (status IN ('active','inactive','suspended')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS optischema.tenant_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    database_name TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);

-- Create tables for storing analysis results and recommendations
CREATE TABLE IF NOT EXISTS optischema.query_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id),
    query_hash TEXT NOT NULL,
    query_text TEXT NOT NULL,
    total_time BIGINT NOT NULL,
    calls BIGINT NOT NULL,
    mean_time DOUBLE PRECISION NOT NULL,
    stddev_time DOUBLE PRECISION,
    min_time BIGINT,
    max_time BIGINT,
    rows BIGINT,
    shared_blks_hit BIGINT,
    shared_blks_read BIGINT,
    shared_blks_written BIGINT,
    shared_blks_dirtied BIGINT,
    temp_blks_read BIGINT,
    temp_blks_written BIGINT,
    blk_read_time DOUBLE PRECISION,
    blk_write_time DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS optischema.analysis_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id),
    query_hash TEXT NOT NULL,
    query_text TEXT NOT NULL,
    execution_plan JSONB,
    analysis_summary TEXT,
    performance_score INTEGER,
    bottleneck_type TEXT,
    bottleneck_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS optischema.recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id),
    query_hash TEXT NOT NULL,
    recommendation_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    sql_fix TEXT,
    original_sql TEXT,
    patch_sql TEXT,
    execution_plan_json JSONB,
    estimated_improvement_percent INTEGER,
    confidence_score INTEGER,
    risk_level TEXT,
    status TEXT DEFAULT 'pending',
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS optischema.sandbox_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id),
    recommendation_id UUID REFERENCES optischema.recommendations(id),
    original_performance JSONB,
    optimized_performance JSONB,
    improvement_percent INTEGER,
    test_status TEXT,
    test_results JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS optischema.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id),
    action_type TEXT NOT NULL,
    user_id TEXT,
    recommendation_id UUID REFERENCES optischema.recommendations(id),
    query_hash TEXT,
    before_metrics JSONB,
    after_metrics JSONB,
    improvement_percent DOUBLE PRECISION,
    details JSONB DEFAULT '{}',
    risk_level TEXT,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS optischema.connection_baselines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id),
    connection_id TEXT NOT NULL,
    connection_name TEXT NOT NULL,
    baseline_latency_ms DOUBLE PRECISION NOT NULL,
    measured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    connection_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS optischema.index_recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id),
    index_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    schema_name TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    size_pretty TEXT NOT NULL,
    idx_scan BIGINT NOT NULL,
    idx_tup_read BIGINT NOT NULL,
    idx_tup_fetch BIGINT NOT NULL,
    last_used TIMESTAMP WITH TIME ZONE,
    days_unused INTEGER NOT NULL,
    estimated_savings_mb DOUBLE PRECISION NOT NULL,
    risk_level TEXT NOT NULL,
    recommendation_type TEXT NOT NULL,
    sql_fix TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Benchmark jobs table for async operations
CREATE TABLE IF NOT EXISTS optischema.benchmark_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id),
    recommendation_id UUID NOT NULL,
    status TEXT DEFAULT 'pending',
    job_type TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    result_json JSONB,
    error_message TEXT
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_query_metrics_tenant_hash ON optischema.query_metrics(tenant_id, query_hash);
CREATE INDEX IF NOT EXISTS idx_query_metrics_tenant_created_at ON optischema.query_metrics(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_analysis_results_tenant_hash ON optischema.analysis_results(tenant_id, query_hash);
CREATE INDEX IF NOT EXISTS idx_recommendations_tenant_hash ON optischema.recommendations(tenant_id, query_hash);
CREATE INDEX IF NOT EXISTS idx_recommendations_tenant_type ON optischema.recommendations(tenant_id, recommendation_type);
CREATE INDEX IF NOT EXISTS idx_recommendations_tenant_applied ON optischema.recommendations(tenant_id, applied);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_action_type ON optischema.audit_logs(tenant_id, action_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_created_at ON optischema.audit_logs(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_user_id ON optischema.audit_logs(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_recommendation_id ON optischema.audit_logs(tenant_id, recommendation_id);
CREATE INDEX IF NOT EXISTS idx_connection_baselines_tenant_connection_id ON optischema.connection_baselines(tenant_id, connection_id);
CREATE INDEX IF NOT EXISTS idx_connection_baselines_tenant_is_active ON optischema.connection_baselines(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_index_recommendations_tenant_schema_table ON optischema.index_recommendations(tenant_id, schema_name, table_name);
CREATE INDEX IF NOT EXISTS idx_index_recommendations_tenant_risk_level ON optischema.index_recommendations(tenant_id, risk_level);
CREATE INDEX IF NOT EXISTS idx_index_recommendations_tenant_days_unused ON optischema.index_recommendations(tenant_id, days_unused);
CREATE INDEX IF NOT EXISTS idx_benchmark_jobs_tenant_status ON optischema.benchmark_jobs(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_benchmark_jobs_tenant_created_at ON optischema.benchmark_jobs(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_benchmark_jobs_tenant_recommendation_id ON optischema.benchmark_jobs(tenant_id, recommendation_id);

-- Create functions for updating timestamps
CREATE OR REPLACE FUNCTION optischema.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_query_metrics_updated_at 
    BEFORE UPDATE ON optischema.query_metrics 
    FOR EACH ROW EXECUTE FUNCTION optischema.update_updated_at_column();

-- Create views for easier querying
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
    r.*,
    qm.query_text,
    qm.mean_time as current_mean_time
FROM optischema.recommendations r
JOIN optischema.query_metrics qm ON r.tenant_id = qm.tenant_id AND r.query_hash = qm.query_hash
WHERE r.created_at >= NOW() - INTERVAL '24 hours'
ORDER BY r.tenant_id, r.created_at DESC;

-- Grant permissions
GRANT USAGE ON SCHEMA optischema TO optischema;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA optischema TO optischema;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA optischema TO optischema;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA optischema TO optischema;

-- Insert default tenant
INSERT INTO optischema.tenants (id, name, status)
VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'active')
ON CONFLICT (name) DO NOTHING;

-- Insert some sample data for testing (optional)
INSERT INTO optischema.query_metrics (
    tenant_id,
    query_hash, 
    query_text, 
    total_time, 
    calls, 
    mean_time
) VALUES 
(
    '00000000-0000-0000-0000-000000000001',
    'sample_query_1',
    'SELECT * FROM information_schema.tables WHERE table_schema = $1',
    1000000,
    100,
    10000
),
(
    '00000000-0000-0000-0000-000000000001',
    'sample_query_2', 
    'SELECT COUNT(*) FROM pg_stat_statements',
    500000,
    50,
    10000
) ON CONFLICT DO NOTHING;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'OptiSchema database initialized successfully!';
    RAISE NOTICE 'Extensions enabled: pg_stat_statements, uuid-ossp';
    RAISE NOTICE 'Schema created: optischema';
    RAISE NOTICE 'Tables created incl. tenants, tenant_connections, query_metrics, analysis_results, recommendations, sandbox_tests, audit_logs, connection_baselines, index_recommendations, benchmark_jobs';
    RAISE NOTICE 'Views created: hot_queries, recent_recommendations';
END $$; 
