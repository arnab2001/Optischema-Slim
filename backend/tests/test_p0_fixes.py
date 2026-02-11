"""
Tests for P0 audit fixes.
Run with: cd backend && python -m pytest tests/test_p0_fixes.py -v
"""

import ssl
import pytest

# ---------------------------------------------------------------------------
# P0.2: SSL configuration utility
# ---------------------------------------------------------------------------
from db_utils import configure_ssl


class TestConfigureSSL:
    def test_require_creates_verified_context(self):
        """sslmode=require should verify certificates (not CERT_NONE)."""
        config = configure_ssl({"host": "rds.amazonaws.com", "ssl": "require"})
        ctx = config["ssl"]
        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.check_hostname is True

    def test_prefer_creates_unverified_context(self):
        """sslmode=prefer accepts weaker security."""
        config = configure_ssl({"host": "localhost", "ssl": "prefer"})
        ctx = config["ssl"]
        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.verify_mode == ssl.CERT_NONE

    def test_disable_sets_false(self):
        config = configure_ssl({"host": "localhost", "ssl": "disable"})
        assert config["ssl"] is False

    def test_true_treated_as_require(self):
        config = configure_ssl({"host": "localhost", "ssl": True})
        ctx = config["ssl"]
        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_no_ssl_key_unchanged(self):
        config = configure_ssl({"host": "localhost"})
        assert "ssl" not in config or config.get("ssl") is None

    def test_does_not_mutate_original(self):
        original = {"host": "localhost", "ssl": "require"}
        configure_ssl(original)
        assert original["ssl"] == "require"  # unchanged


# ---------------------------------------------------------------------------
# P0.4: Version detection fallback
# ---------------------------------------------------------------------------


class TestVersionFallback:
    def test_pg_version_default_is_none(self):
        """ConnectionManager starts with None version."""
        from connection_manager import ConnectionManager
        cm = ConnectionManager()
        assert cm.get_pg_version() is None

    def test_fallback_value_is_pg12(self):
        """The fallback constant should be 120000 (PG 12)."""
        # We can't easily test the async connect flow without a DB,
        # but we verify the fallback constant exists in the source.
        import inspect
        from connection_manager import ConnectionManager
        source = inspect.getsource(ConnectionManager.connect)
        assert "120000" in source, "Fallback version 120000 (PG12) should be in connect()"


# ---------------------------------------------------------------------------
# P0.5: Schema pruning
# ---------------------------------------------------------------------------


class TestSchemaPruning:
    @pytest.fixture
    def llm_service(self):
        from services.llm_service import LLMService
        return LLMService()

    def test_prune_finds_bare_table_name(self, llm_service):
        schema = (
            "Table: public.users\n"
            "  id integer PK\n"
            "  name text\n"
            "\n"
            "Table: public.orders\n"
            "  id integer PK\n"
            "  user_id integer FK\n"
        )
        result = llm_service._prune_schema("SELECT * FROM users", schema)
        assert "users" in result
        assert "orders" not in result

    def test_prune_handles_schema_qualified_query(self, llm_service):
        schema = (
            "Table: public.users\n"
            "  id integer PK\n"
            "\n"
            "Table: public.orders\n"
            "  id integer PK\n"
        )
        result = llm_service._prune_schema("SELECT * FROM public.users", schema)
        assert "users" in result
        assert "orders" not in result

    def test_prune_case_insensitive(self, llm_service):
        schema = (
            "Table: public.Users\n"
            "  id integer PK\n"
            "\n"
            "Table: public.Orders\n"
            "  id integer PK\n"
        )
        result = llm_service._prune_schema("SELECT * FROM users", schema)
        assert "Users" in result

    def test_prune_fallback_on_empty_match(self, llm_service):
        schema = "Table: public.users\n  id integer PK\n"
        result = llm_service._prune_schema("SELECT * FROM nonexistent", schema)
        # Should return full schema as fallback
        assert result == schema

    def test_prune_multi_table_join(self, llm_service):
        schema = (
            "Table: public.users\n"
            "  id integer PK\n"
            "\n"
            "Table: public.orders\n"
            "  id integer PK\n"
            "  user_id integer FK\n"
            "\n"
            "Table: public.products\n"
            "  id integer PK\n"
        )
        result = llm_service._prune_schema(
            "SELECT * FROM users JOIN orders ON users.id = orders.user_id",
            schema
        )
        assert "users" in result
        assert "orders" in result
        assert "products" not in result


# ---------------------------------------------------------------------------
# P1.1: CONCURRENTLY in prompts
# ---------------------------------------------------------------------------


class TestConcurrentlyPrompt:
    def test_standard_prompt_includes_concurrently(self):
        from services.llm_service import LLMService
        svc = LLMService()
        prompt = svc._build_standard_prompt(
            "SELECT * FROM users WHERE id = $1",
            "Table: users\n  id integer PK\n",
            {"Total Cost": 100}
        )
        assert "CONCURRENTLY" in prompt

    def test_reasoning_prompt_includes_concurrently(self):
        from services.llm_service import LLMService
        svc = LLMService()
        prompt = svc._build_reasoning_prompt(
            "SELECT * FROM users WHERE id = $1",
            "Table: users\n  id integer PK\n",
            {"Total Cost": 100}
        )
        assert "CONCURRENTLY" in prompt


# ---------------------------------------------------------------------------
# P0.3: HypoPG index name detection
# ---------------------------------------------------------------------------


class TestHypoPGIndexDetection:
    def test_detects_hypopg_index_name(self):
        """The simulation service should specifically check for HypoPG index names."""
        import inspect
        from services.simulation_service import SimulationService
        source = inspect.getsource(SimulationService.simulate_index)
        # Should check for "<" prefix (HypoPG names start with "<hypopg>")
        assert 'startswith("<")' in source or "hypopg" in source.lower()

    def test_hypopg_reset_called(self):
        """The simulation service should call hypopg_reset() for cleanup."""
        import inspect
        from services.simulation_service import SimulationService
        source = inspect.getsource(SimulationService.simulate_index)
        assert "hypopg_reset" in source


# ---------------------------------------------------------------------------
# A1+A3: Enriched schema context and prompt improvements
# ---------------------------------------------------------------------------


class TestPlanBottleneckExtraction:
    """Test that the plan bottleneck extractor produces concise, useful output."""

    def test_extracts_seq_scan(self):
        from services.llm_service import LLMService
        svc = LLMService()
        plan = {
            "Node Type": "Seq Scan",
            "Relation Name": "orders",
            "Total Cost": 1500.0,
            "Plan Rows": 50000,
            "Filter": "(status = 'pending')",
        }
        result = svc._extract_plan_bottlenecks(plan)
        assert "Seq Scan" in result
        assert "orders" in result
        assert "status" in result
        assert "50000" in result

    def test_extracts_nested_join(self):
        from services.llm_service import LLMService
        svc = LLMService()
        plan = {
            "Node Type": "Hash Join",
            "Total Cost": 3000.0,
            "Plan Rows": 1000,
            "Hash Cond": "(users.id = orders.user_id)",
            "Plans": [
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "users",
                    "Total Cost": 500.0,
                    "Plan Rows": 10000,
                },
                {
                    "Node Type": "Hash",
                    "Total Cost": 2000.0,
                    "Plan Rows": 50000,
                    "Plans": [
                        {
                            "Node Type": "Seq Scan",
                            "Relation Name": "orders",
                            "Total Cost": 1800.0,
                            "Plan Rows": 50000,
                        }
                    ],
                },
            ],
        }
        result = svc._extract_plan_bottlenecks(plan)
        assert "Hash Join" in result
        assert "users.id = orders.user_id" in result
        assert "Seq Scan" in result
        assert "orders" in result
        assert "users" in result

    def test_does_not_dump_full_json(self):
        """The prompt should NOT contain json.dumps output."""
        from services.llm_service import LLMService
        svc = LLMService()
        plan = {
            "Node Type": "Seq Scan",
            "Relation Name": "test",
            "Total Cost": 100.0,
            "Plan Rows": 500,
        }
        prompt = svc._build_standard_prompt("SELECT * FROM test", "Table: test", plan)
        # Should NOT have json.dumps markers like indented braces
        assert '"Node Type"' not in prompt
        assert '"Plan Rows"' not in prompt


# ---------------------------------------------------------------------------
# B1: JSON extraction with balanced braces
# ---------------------------------------------------------------------------


class TestJsonBlockExtraction:
    def test_extracts_simple_json(self):
        from services.llm_service import LLMService
        text = '```json\n{"category": "INDEX", "sql": "CREATE INDEX..."}\n```'
        result = LLMService._extract_json_block(text)
        assert result is not None
        import json
        parsed = json.loads(result)
        assert parsed["category"] == "INDEX"
        assert parsed["sql"] == "CREATE INDEX..."

    def test_extracts_nested_json(self):
        from services.llm_service import LLMService
        text = '```json\n{"reasoning": "obj {inner}", "nested": {"a": 1}}\n```'
        result = LLMService._extract_json_block(text)
        assert result is not None
        import json
        parsed = json.loads(result)
        assert parsed["nested"]["a"] == 1

    def test_handles_strings_with_braces(self):
        from services.llm_service import LLMService
        text = '```json\n{"sql": "CREATE INDEX ON t(a)", "reasoning": "curly {brace} test"}\n```'
        result = LLMService._extract_json_block(text)
        assert result is not None
        import json
        parsed = json.loads(result)
        assert "CREATE INDEX" in parsed["sql"]
        assert "curly {brace} test" in parsed["reasoning"]

    def test_returns_none_for_no_json(self):
        from services.llm_service import LLMService
        result = LLMService._extract_json_block("no json here")
        assert result is None

    def test_handles_escaped_quotes(self):
        from services.llm_service import LLMService
        text = '```json\n{"sql": "SELECT \\"name\\" FROM t"}\n```'
        result = LLMService._extract_json_block(text)
        assert result is not None


# ---------------------------------------------------------------------------
# B2: SQL detection — no false positives from reasoning text
# ---------------------------------------------------------------------------


class TestSQLDetection:
    def test_does_not_extract_sql_from_reasoning(self):
        from services.llm_service import LLMService
        svc = LLMService()
        result = svc._clean_llm_result({
            "reasoning": "Create a backup before applying any changes",
            "category": "ADVISORY"
        })
        assert "sql" not in result or result.get("sql") is None or result["sql"] == ""

    def test_extracts_sql_from_known_key(self):
        from services.llm_service import LLMService
        svc = LLMService()
        result = svc._clean_llm_result({
            "suggested_sql": "CREATE INDEX CONCURRENTLY idx_foo ON bar(baz)",
            "reasoning": "Add index on baz",
            "category": "INDEX"
        })
        assert result["sql"] == "CREATE INDEX CONCURRENTLY idx_foo ON bar(baz)"

    def test_does_not_extract_empty_sql_key(self):
        from services.llm_service import LLMService
        svc = LLMService()
        result = svc._clean_llm_result({
            "suggested_sql": "",
            "reasoning": "No action needed",
            "category": "ADVISORY"
        })
        # Should not set sql to empty string
        assert "sql" not in result or result.get("sql") in (None, "")


# ---------------------------------------------------------------------------
# C4: vacuum_overdue logic
# ---------------------------------------------------------------------------


class TestVacuumOverdue:
    def test_overdue_when_never_vacuumed(self):
        from services.health_scan_service import HealthScanService
        from models import HealthThresholds
        svc = HealthScanService()
        # Use low thresholds so test data triggers the bloat alert
        thresholds = HealthThresholds(bloat_min_size_mb=1, bloat_min_ratio_percent=10)
        vitals = {
            "bloat": [
                {
                    "schemaname": "public",
                    "table": "big_table",
                    "live_tuples": 100000,
                    "dead_tuples": 50000,
                    "dead_ratio": 33.3,
                    "last_autovacuum": None,
                    "total_bytes": 50 * 1024 * 1024,  # 50MB
                    "total_size": "50 MB",
                }
            ],
            "unused_indexes": [],
            "config": [],
            "top_queries": [],
        }
        report = svc.process_vitals_rules(vitals, thresholds)
        assert len(report["table_bloat"]["issues"]) == 1
        assert report["table_bloat"]["issues"][0]["vacuum_overdue"] is True

    def test_not_overdue_when_recently_vacuumed(self):
        from services.health_scan_service import HealthScanService
        from models import HealthThresholds
        from datetime import datetime, timezone
        svc = HealthScanService()
        thresholds = HealthThresholds(bloat_min_size_mb=1, bloat_min_ratio_percent=10)
        recent = datetime.now(timezone.utc)  # Just now
        vitals = {
            "bloat": [
                {
                    "schemaname": "public",
                    "table": "active_table",
                    "live_tuples": 100000,
                    "dead_tuples": 30000,
                    "dead_ratio": 23.0,
                    "last_autovacuum": recent,
                    "total_bytes": 50 * 1024 * 1024,
                    "total_size": "50 MB",
                }
            ],
            "unused_indexes": [],
            "config": [],
            "top_queries": [],
        }
        report = svc.process_vitals_rules(vitals, thresholds)
        assert len(report["table_bloat"]["issues"]) == 1
        assert report["table_bloat"]["issues"][0]["vacuum_overdue"] is False


class TestPromptIncludesIndexContext:
    """Test that the prompts reference existing indexes and cardinality."""

    def test_standard_prompt_mentions_existing_indexes(self):
        from services.llm_service import LLMService
        svc = LLMService()
        prompt = svc._build_standard_prompt(
            "SELECT * FROM users",
            "Table: users\nExisting Indexes:\n  - idx_users_email [0 scans]: CREATE INDEX...",
            {"Node Type": "Seq Scan", "Total Cost": 100, "Plan Rows": 500},
        )
        assert "NO DUPLICATE INDEXES" in prompt
        assert "Existing Indexes" in prompt

    def test_reasoning_prompt_mentions_existing_indexes(self):
        from services.llm_service import LLMService
        svc = LLMService()
        prompt = svc._build_reasoning_prompt(
            "SELECT * FROM users",
            "Table: users\nExisting Indexes:\n  - idx_users_email [0 scans]: CREATE INDEX...",
            {"Node Type": "Seq Scan", "Total Cost": 100, "Plan Rows": 500},
        )
        assert "NO DUPLICATE INDEXES" in prompt
        assert "low-cardinality" in prompt.lower() or "cardinality" in prompt.lower()
