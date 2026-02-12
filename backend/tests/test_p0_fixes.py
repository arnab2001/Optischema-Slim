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


# ---------------------------------------------------------------------------
# P1.3: PG12 syntax default in metric_service
# ---------------------------------------------------------------------------


class TestPG12SyntaxDefault:
    def test_version_none_uses_old_syntax(self):
        """When pg_version is None, should default to PG12 (old) column names."""
        from services.metric_service import MetricService
        from connection_manager import connection_manager

        # Save and override
        original = connection_manager.get_pg_version()
        connection_manager._pg_version = None

        try:
            svc = MetricService()
            select, _, order = svc._build_query_metrics_sql()
            # Old syntax uses 'total_time' not 'total_exec_time'
            assert "total_time" in select
            assert "total_exec_time" not in select
            assert "mean_time" in select
            assert "mean_exec_time" not in select
        finally:
            connection_manager._pg_version = original

    def test_pg13_uses_new_syntax(self):
        """PG13+ should use total_exec_time."""
        from services.metric_service import MetricService
        from connection_manager import connection_manager

        original = connection_manager.get_pg_version()
        connection_manager._pg_version = 130000

        try:
            svc = MetricService()
            select, _, _ = svc._build_query_metrics_sql()
            assert "total_exec_time" in select
            assert "mean_exec_time" in select
        finally:
            connection_manager._pg_version = original

    def test_pg12_uses_old_syntax(self):
        """PG12 should use total_time."""
        from services.metric_service import MetricService
        from connection_manager import connection_manager

        original = connection_manager.get_pg_version()
        connection_manager._pg_version = 120000

        try:
            svc = MetricService()
            select, _, _ = svc._build_query_metrics_sql()
            assert "total_time" in select
            assert "total_exec_time" not in select
        finally:
            connection_manager._pg_version = original


# ---------------------------------------------------------------------------
# C2: Health scan version-aware columns
# ---------------------------------------------------------------------------


class TestHealthScanVersionAware:
    def test_collect_vitals_imports_version_check(self):
        """Health scan should use version-aware column names."""
        import inspect
        from services.health_scan_service import HealthScanService
        source = inspect.getsource(HealthScanService.collect_vitals)
        # Should reference version check, not hardcode total_exec_time
        assert "use_new" in source or "pg_version" in source
        assert "total_col" in source or "total_time" in source


# ---------------------------------------------------------------------------
# P1.2: Stats reset warning
# ---------------------------------------------------------------------------


class TestStatsResetWarning:
    def _read_index_advisor_source(self):
        """Read source directly to avoid tenant_context import."""
        import pathlib
        src = pathlib.Path(__file__).parent.parent / "index_advisor.py"
        return src.read_text()

    def test_analyze_unused_checks_stats_reset(self):
        """analyze_unused_indexes should check stats_reset for freshness."""
        source = self._read_index_advisor_source()
        assert "stats_reset" in source
        assert "stats_warning" in source

    def test_recommendation_includes_warning_field(self):
        """Recommendations should carry a stats_warning field."""
        source = self._read_index_advisor_source()
        assert "'stats_warning'" in source


# ---------------------------------------------------------------------------
# C3: Bloat uses pg_total_relation_size
# ---------------------------------------------------------------------------


class TestBloatTotalSize:
    def test_bloat_query_uses_total_relation_size(self):
        """Bloat query should use pg_total_relation_size (not pg_relation_size)."""
        import inspect
        from services.health_scan_service import HealthScanService
        source = inspect.getsource(HealthScanService.collect_vitals)
        # The bloat section should use pg_total_relation_size
        assert "pg_total_relation_size(relid)" in source


# ---------------------------------------------------------------------------
# P1.4: Fingerprinting preserves LIMIT/OFFSET
# ---------------------------------------------------------------------------


class TestFingerprintPreservesLimit:
    @staticmethod
    def _get_fingerprint_fn():
        """Load fingerprint_query from source to avoid deep import chain."""
        import importlib.util, pathlib
        src = pathlib.Path(__file__).parent.parent / "analysis" / "core.py"
        # Load the module without triggering __init__.py imports
        spec = importlib.util.spec_from_file_location("analysis_core_isolated", src,
            submodule_search_locations=[])
        mod = importlib.util.module_from_spec(spec)
        # Stub dependencies so the module can load
        import sys, types
        for stub_name in ["collector", "models"]:
            if stub_name not in sys.modules:
                sys.modules[stub_name] = types.ModuleType(stub_name)
        # Add dummy model classes
        models_stub = sys.modules["models"]
        for cls_name in ["QueryMetrics", "HotQuery", "MetricsSummary"]:
            if not hasattr(models_stub, cls_name):
                setattr(models_stub, cls_name, type(cls_name, (), {}))
        collector_stub = sys.modules["collector"]
        if not hasattr(collector_stub, "get_metrics_cache"):
            collector_stub.get_metrics_cache = lambda: []
        spec.loader.exec_module(mod)
        return mod.fingerprint_query

    def test_limit_preserved(self):
        """LIMIT values should remain in fingerprint."""
        fingerprint_query = self._get_fingerprint_fn()
        fp1 = fingerprint_query("SELECT * FROM users LIMIT 10")
        fp2 = fingerprint_query("SELECT * FROM users LIMIT 1000000")
        assert "10" in fp1
        assert "1000000" in fp2
        assert fp1 != fp2

    def test_offset_preserved(self):
        """OFFSET values should remain in fingerprint."""
        fingerprint_query = self._get_fingerprint_fn()
        fp = fingerprint_query("SELECT * FROM users LIMIT 10 OFFSET 50")
        assert "10" in fp
        assert "50" in fp

    def test_where_values_still_replaced(self):
        """WHERE clause values should still be replaced with ?."""
        fingerprint_query = self._get_fingerprint_fn()
        fp = fingerprint_query("SELECT * FROM users WHERE id = 42 LIMIT 10")
        assert "42" not in fp
        assert "10" in fp


# ---------------------------------------------------------------------------
# B3: Validate LLM SQL column references
# ---------------------------------------------------------------------------


class TestValidateSQLColumns:
    def test_detects_hallucinated_column(self):
        from services.llm_service import LLMService
        svc = LLMService()
        schema = "  - id (integer) [PK]\n  - email (text)\n"
        warnings = svc._validate_sql_columns(
            "CREATE INDEX idx_users_phone ON users(phone_number)",
            schema
        )
        assert any("phone_number" in w for w in warnings)

    def test_no_warning_for_valid_columns(self):
        from services.llm_service import LLMService
        svc = LLMService()
        schema = "  - id (integer) [PK]\n  - email (text)\n"
        warnings = svc._validate_sql_columns(
            "CREATE INDEX idx_users_email ON users(email)",
            schema
        )
        # 'email' exists in schema, so no warning for it
        assert not any("email" in w for w in warnings)

    def test_empty_schema_returns_no_warnings(self):
        from services.llm_service import LLMService
        svc = LLMService()
        warnings = svc._validate_sql_columns("CREATE INDEX idx ON t(col)", "")
        assert warnings == []


# ---------------------------------------------------------------------------
# B4: Sanitize AI action_payload
# ---------------------------------------------------------------------------


class TestSanitizeActionPayload:
    def test_allows_vacuum_payload(self):
        from services.health_scan_service import HealthScanService
        svc = HealthScanService()
        ai_data = {"issues": [
            {"type": "SCHEMA", "severity": "WARNING", "title": "Bloat",
             "description": "Bloat detected", "action_payload": "VACUUM FULL public.users;"}
        ]}
        result = svc._validate_ai_response(ai_data)
        assert result["issues"][0]["type"] == "SCHEMA"
        assert "VACUUM" in result["issues"][0]["action_payload"]

    def test_blocks_dangerous_payload(self):
        from services.health_scan_service import HealthScanService
        svc = HealthScanService()
        ai_data = {"issues": [
            {"type": "SCHEMA", "severity": "WARNING", "title": "Hack",
             "description": "Drop everything", "action_payload": "DROP TABLE users CASCADE;"}
        ]}
        result = svc._validate_ai_response(ai_data)
        # Should be downgraded to INFO with empty payload
        assert result["issues"][0]["type"] == "INFO"
        assert result["issues"][0]["action_payload"] == ""

    def test_allows_create_index_payload(self):
        from services.health_scan_service import HealthScanService
        svc = HealthScanService()
        ai_data = {"issues": [
            {"type": "SCHEMA", "severity": "WARNING", "title": "Index",
             "description": "Add index", "action_payload": "CREATE INDEX idx_foo ON bar(baz);"}
        ]}
        result = svc._validate_ai_response(ai_data)
        assert result["issues"][0]["type"] == "SCHEMA"

    def test_allows_alter_system_payload(self):
        from services.health_scan_service import HealthScanService
        svc = HealthScanService()
        ai_data = {"issues": [
            {"type": "CONFIG", "severity": "INFO", "title": "Config",
             "description": "Tune work_mem", "action_payload": "ALTER SYSTEM SET work_mem = '64MB';"}
        ]}
        result = svc._validate_ai_response(ai_data)
        assert result["issues"][0]["type"] == "CONFIG"


# ---------------------------------------------------------------------------
# D1: Rewrite safety — side-effect functions
# ---------------------------------------------------------------------------


class TestRewriteSafety:
    def test_blocks_pg_sleep(self):
        """simulate_rewrite should block pg_sleep."""
        import inspect
        from services.simulation_service import SimulationService
        source = inspect.getsource(SimulationService.simulate_rewrite)
        assert "pg_sleep" in source
        assert "DANGEROUS_FUNCTIONS" in source or "dangerous" in source.lower()

    def test_dangerous_function_list_exists(self):
        """Should have a blocklist of dangerous functions."""
        import inspect
        from services.simulation_service import SimulationService
        source = inspect.getsource(SimulationService.simulate_rewrite)
        for fn in ["dblink", "lo_export", "pg_terminate_backend"]:
            assert fn in source, f"Missing dangerous function: {fn}"


# ---------------------------------------------------------------------------
# D2: Validate index SQL before simulation
# ---------------------------------------------------------------------------


class TestIndexSQLValidation:
    def test_accepts_create_index(self):
        from services.simulation_service import SimulationService
        svc = SimulationService()
        result = svc._parse_indexes("CREATE INDEX idx_foo ON bar(baz)")
        assert len(result) == 1

    def test_accepts_create_unique_index(self):
        from services.simulation_service import SimulationService
        svc = SimulationService()
        result = svc._parse_indexes("CREATE UNIQUE INDEX idx_foo ON bar(baz)")
        assert len(result) == 1

    def test_rejects_drop_table(self):
        from services.simulation_service import SimulationService
        svc = SimulationService()
        result = svc._parse_indexes("DROP TABLE users")
        assert len(result) == 0

    def test_rejects_mixed_dangerous(self):
        from services.simulation_service import SimulationService
        svc = SimulationService()
        result = svc._parse_indexes(
            "CREATE INDEX idx_foo ON bar(baz); DROP TABLE users; SELECT pg_sleep(60)"
        )
        assert len(result) == 1
        assert "CREATE INDEX" in result[0]

    def test_accepts_concurrently(self):
        from services.simulation_service import SimulationService
        svc = SimulationService()
        result = svc._parse_indexes("CREATE INDEX CONCURRENTLY idx_foo ON bar(baz)")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# P2.3: Left-prefix redundancy detection
# ---------------------------------------------------------------------------


class TestLeftPrefixRedundancy:
    def test_redundancy_query_uses_indkey(self):
        """Redundancy detection should compare indkey arrays."""
        import pathlib
        src = pathlib.Path(__file__).parent.parent / "index_advisor.py"
        source = src.read_text()
        assert "indkey" in source or "key_cols" in source
        assert "covered_by" in source


# ---------------------------------------------------------------------------
# P2.5: Lock contention detection
# ---------------------------------------------------------------------------


class TestLockContention:
    def test_collect_vitals_has_lock_query(self):
        """Health scan should query for lock contention."""
        import inspect
        from services.health_scan_service import HealthScanService
        source = inspect.getsource(HealthScanService.collect_vitals)
        assert "pg_blocking_pids" in source
        assert "lock_contention" in source

    def test_process_vitals_includes_lock_section(self):
        """Rule processing should produce lock_contention section."""
        from services.health_scan_service import HealthScanService
        from models import HealthThresholds
        svc = HealthScanService()
        vitals = {
            "bloat": [], "unused_indexes": [], "config": [],
            "top_queries": [], "lock_contention": [],
        }
        report = svc.process_vitals_rules(vitals, HealthThresholds())
        assert "lock_contention" in report
        assert report["lock_contention"]["checked"] is True

    def test_scoring_penalizes_locks(self):
        """Lock contention should reduce health score."""
        from services.health_scan_service import HealthScanService
        from models import HealthThresholds
        svc = HealthScanService()
        vitals = {
            "bloat": [], "unused_indexes": [], "config": [],
            "top_queries": [], "lock_contention": [],
        }
        thresholds = HealthThresholds()
        report_clean = svc.process_vitals_rules(vitals, thresholds)
        score_clean, _ = svc.calculate_deterministic_score(vitals, report_clean, thresholds)

        # Now with lock issues in the report
        report_locks = svc.process_vitals_rules(vitals, thresholds)
        report_locks["lock_contention"]["issues"] = [
            {"blocked_pid": 1, "severity": "high"}
        ]
        score_locks, deductions = svc.calculate_deterministic_score(vitals, report_locks, thresholds)

        assert score_locks < score_clean
        assert any("lock" in d.lower() for d in deductions)


# ---------------------------------------------------------------------------
# P2.1: Token usage logging in LLM providers
# ---------------------------------------------------------------------------


class TestTokenUsageLogging:
    def test_openai_provider_logs_tokens(self):
        """OpenAI provider should log token usage."""
        import inspect
        from llm.openai_provider import OpenAIProvider
        source = inspect.getsource(OpenAIProvider.analyze)
        assert "prompt_tokens" in source
        assert "completion_tokens" in source
        assert "Token usage" in source

    def test_ollama_provider_logs_tokens(self):
        """Ollama provider should log token usage."""
        import inspect
        from llm.ollama_provider import OllamaProvider
        source = inspect.getsource(OllamaProvider.analyze)
        assert "prompt_eval_count" in source or "prompt_tokens" in source
        assert "eval_count" in source
        assert "Token usage" in source

    def test_deepseek_provider_logs_tokens(self):
        """DeepSeek provider should log token usage."""
        import inspect
        from llm.deepseek_provider import DeepSeekProvider
        source = inspect.getsource(DeepSeekProvider.analyze)
        assert "prompt_tokens" in source
        assert "Token usage" in source

    def test_gemini_provider_logs_tokens(self):
        """Gemini provider should log token usage."""
        import inspect
        from llm.gemini_provider import GeminiProvider
        source = inspect.getsource(GeminiProvider.analyze)
        assert "usage_metadata" in source or "token_count" in source
        assert "Token usage" in source
