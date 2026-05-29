# Database Migrations

This directory contains database migration files for the i3d-agent-system.

## Prerequisites

- PostgreSQL 15 or higher
- pgvector extension installed and enabled
- Database user with sufficient privileges (CREATE, ALTER, DROP)

## Migration Files

| File | Description |
|------|-------------|
| `001_initial.sql` | Initial database schema with all core tables, indexes, RLS policies, and views |

## Running Migrations

### Using psql (Recommended)

```bash
# Set environment variables
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="i3d_agent_system"
export DB_USER="postgres"
export DB_PASSWORD="your_password"

# Run the initial migration
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f 001_initial.sql
```

### Using Python (with asyncpg or psycopg3)

```python
import asyncio
import asyncpg

async def run_migration():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='i3d_agent_system',
        user='postgres',
        password='your_password'
    )

    try:
        with open('001_initial.sql', 'r') as f:
            sql = f.read()
        await conn.execute(sql)
        print("Migration completed successfully!")
    finally:
        await conn.close()

asyncio.run(run_migration())
```

### Using Diesel (if using with Rust)

```bash
# Run the migration file
diesel migration run --migration-dir ./migrations
```

## Verification

After running migrations, verify the schema with these queries:

### Check Tables

```sql
-- List all tables created
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN (
    'agent_semantic_memory',
    'agent_conversation_history',
    'agent_tasks',
    'rag_documents',
    'agent_feedback'
)
ORDER BY tablename;
```

### Check Indexes

```sql
-- List all indexes created
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

### Check RLS Policies

```sql
-- List all RLS policies
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

### Check Vector Indexes

```sql
-- Verify HNSW indexes were created for vector columns
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND indexdef LIKE '%hnsw%'
ORDER BY tablename;
```

### Check Functions and Triggers

```sql
-- List custom functions
SELECT 
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name = 'update_updated_at_column';

-- List triggers
SELECT 
    trigger_name,
    event_object_table,
    action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table;
```

### Check Views

```sql
-- List views
SELECT 
    table_name,
    view_definition
FROM information_schema.views
WHERE table_schema = 'public'
ORDER BY table_name;
```

## Rollback

To rollback the initial migration:

```bash
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f rollback_001_initial.sql
```

Or manually drop all objects:

```sql
-- Drop views
DROP VIEW IF EXISTS v_user_recent_sessions CASCADE;

-- Drop tables (in correct order due to foreign key references)
DROP TABLE IF EXISTS agent_feedback CASCADE;
DROP TABLE IF EXISTS rag_documents CASCADE;
DROP TABLE IF EXISTS agent_tasks CASCADE;
DROP TABLE IF EXISTS agent_conversation_history CASCADE;
DROP TABLE IF EXISTS agent_semantic_memory CASCADE;

-- Drop function
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
```

## Tenant Context

All tables use Row-Level Security (RLS) with tenant isolation. Before querying:

```sql
-- Set the tenant context for the session
SET app.current_tenant = 'your_tenant_id';

-- Or use the configured value
SELECT set_config('app.current_tenant', 'your_tenant_id', false);
```

## Vector Operations

### Inserting with embeddings

```sql
INSERT INTO agent_semantic_memory (
    tenant_id,
    agent_id,
    memory_key,
    content,
    content_vector,
    memory_type,
    importance_score
) VALUES (
    'tenant_001',
    'agent_001',
    'user_preference',
    'User prefers concise responses',
    '[0.1, 0.2, ...]', -- Your 512-dimensional vector here
    'preference',
    0.8
);
```

### Vector similarity search

```sql
-- Find similar memories using cosine similarity
SELECT 
    id,
    memory_key,
    content,
    1 - (content_vector <=> '[0.1, 0.2, ...]') AS similarity
FROM agent_semantic_memory
WHERE tenant_id = 'tenant_001'
AND content_vector <=> '[0.1, 0.2, ...]' < 0.3  -- Similarity threshold
ORDER BY content_vector <=> '[0.1, 0.2, ...]'
LIMIT 10;
```

## Troubleshooting

### pgvector extension not found

```sql
-- Ensure pgvector is installed on the server
CREATE EXTENSION IF NOT EXISTS vector;
```

### RLS policy errors

If you get "no RLS policies" or permission errors, ensure:
1. RLS is enabled on the table
2. The tenant context is set before queries
3. The database user has permission to use `current_setting`

### Permission denied errors

Ensure your database user has:
- `CREATE` privilege on the database
- `USAGE` privilege on schema `public`
- `ALL PRIVILEGES` on created tables

## Next Steps

After running migrations:

1. Configure your application connection string
2. Set up proper tenant management in your application
3. Initialize any seed data if needed
4. Test vector operations with your embedding model
5. Configure backup and maintenance procedures
