#!/bin/bash
# Script to re-seed the golden dataset into the postgres-sandbox container

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
SQL_FILE="$DIR/seed_golden.sql"

if [ ! -f "$SQL_FILE" ]; then
    echo "Error: seed_golden.sql not found in $DIR"
    exit 1
fi

echo "Re-seeding Golden Dataset into postgres-sandbox..."
docker exec -i optischema-postgres-sandbox psql -U optischema -d optischema_sandbox < "$SQL_FILE"

if [ $? -eq 0 ]; then
    echo "Golden Dataset seeded successfully."
else
    echo "Failed to seed Golden Dataset."
    exit 1
fi
