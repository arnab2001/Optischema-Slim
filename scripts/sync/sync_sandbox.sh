#!/bin/bash

echo "🔄 Syncing sandbox with connected database..."

# Start the sandbox
echo "📦 Starting sandbox container..."
docker compose --profile sandbox up postgres_sandbox -d

# Wait for sandbox to be ready
echo "⏳ Waiting for sandbox to be ready..."
sleep 10

# Check if sandbox is ready
until docker exec optischema-sandbox pg_isready -U sandbox -d sandbox; do
  echo "Waiting for sandbox database..."
  sleep 2
done

echo "✅ Sandbox is ready!"

# Create a dump of the current database
echo "📤 Creating dump of current database..."
docker exec optischema-postgres pg_dump -U optischema -d optischema --schema-only > /tmp/schema_dump.sql

# Copy the dump to sandbox container
echo "📋 Copying schema to sandbox..."
docker cp /tmp/schema_dump.sql optischema-sandbox:/tmp/schema_dump.sql

# Apply the schema to sandbox
echo "🔧 Applying schema to sandbox..."
docker exec optischema-sandbox psql -U sandbox -d sandbox -f /tmp/schema_dump.sql

# Create a data dump (sample data)
echo "📊 Creating sample data dump..."
docker exec optischema-postgres pg_dump -U optischema -d optischema --data-only --table=demo_* > /tmp/data_dump.sql

# Copy and apply data
echo "📋 Copying sample data to sandbox..."
docker cp /tmp/data_dump.sql optischema-sandbox:/tmp/data_dump.sql
docker exec optischema-sandbox psql -U sandbox -d sandbox -f /tmp/data_dump.sql

# Clean up
rm -f /tmp/schema_dump.sql /tmp/data_dump.sql

echo "✅ Sandbox synced successfully!"
echo "🔗 Sandbox connection: postgresql://sandbox:***@localhost:5433/sandbox"
