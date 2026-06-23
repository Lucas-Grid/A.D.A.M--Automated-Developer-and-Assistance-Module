"""Initial baseline migration - raw SQLite schema snapshot for ADAM OS v0.1.0."""
# This is a placeholder migration. ADAM OS uses raw SQLite DDL via _ensure_table() in each registry.
# This file represents the schema state at v0.1.0 for migration tracking purposes.

# Tables created by _ensure_table()/ensure_tables() methods:
# - projects (core/registry.py)
# - agents (agents/registry.py)
# - automations (automations/registry.py)
# - workflow_steps (automations/workflow.py)
# - job_history (automations/history.py)
# - knowledge_entities, knowledge_relationships (knowledge/graph.py)
# - memory, memory_index (memory/store.py)
# - workspaces (workspace/manager.py)
# - models (connections/model_registry.py)

# The actual tables are created via raw SQL in the respective registry modules.
# Migration via Alembic is supported for future ORM model additions.

# SCHEMA SNAPSHOT (for documentation):
# ----------------------------------
# CREATE TABLE projects (id, name, path, description, model_tag, metadata, created_at, updated_at)
# CREATE TABLE agents (id, name, role, goal, created_at, updated_at)
# CREATE TABLE automations (id, name, schedule, enabled, steps, metadata, created_at, updated_at)
# CREATE TABLE workflow_steps (workflow_id, step_index, skill_name, params, conditions)
# CREATE TABLE job_history (id, workflow_id, run_at, status, result, error)
# CREATE TABLE knowledge_entities (id, type, name, data, created_at, updated_at)
# CREATE TABLE knowledge_relationships (id, source_id, target_id, type, strength, created_at)
# CREATE TABLE memory (id, key, value, kind, tags, created_at, updated_at)
# CREATE TABLE memory_index (id, memory_id, embedding) -- FK: memory(id) ON DELETE CASCADE
# CREATE TABLE workspaces (id, path, name, type, created_at, updated_at)
# CREATE TABLE models (id, name, provider, tags, metadata, created_at, updated_at)

# Placeholder revision identifiers
revision = "20260623_initial_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """No-op: Tables are created by registry singletons."""
    pass


def downgrade():
    """No-op: Tables are managed by registry singletons."""
    pass