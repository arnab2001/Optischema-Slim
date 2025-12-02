-- Migration: Add authentication and encryption support
-- Creates users and api_keys tables, adds password encryption column

BEGIN;

-- Create users table for authentication
CREATE TABLE IF NOT EXISTS optischema.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON optischema.users(email);
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON optischema.users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON optischema.users(is_active);

-- Create API keys table
CREATE TABLE IF NOT EXISTS optischema.api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES optischema.users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES optischema.tenants(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON optischema.api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant_id ON optischema.api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON optischema.api_keys(key_hash);

-- Add password encryption column to tenant_connections
ALTER TABLE optischema.tenant_connections 
ADD COLUMN IF NOT EXISTS password_encrypted TEXT;

-- Add flag to track migration status
ALTER TABLE optischema.tenant_connections 
ADD COLUMN IF NOT EXISTS encryption_migrated BOOLEAN DEFAULT FALSE;

-- Add comment explaining the migration
COMMENT ON COLUMN optischema.tenant_connections.password_encrypted IS 'Encrypted password using Fernet encryption';
COMMENT ON COLUMN optischema.tenant_connections.encryption_migrated IS 'Flag indicating if password has been migrated to encrypted format';

COMMIT;
