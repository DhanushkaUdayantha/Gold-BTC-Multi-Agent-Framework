"""
Global pytest configuration and environment isolation.

Ensures that test suite execution is 100% idempotent:
- Redirects report exports away from tracked data/reports/ to isolated tempfile directory.
- Redirects gemini_usage.json writes away from root repository to isolated tempfile.
- Redirects gating_state.json mutations away from data/gating_state.json to isolated tempfile.
- Completely eliminates git-tracked file mutations during 'pytest -q'.
"""
import os
import shutil
import tempfile
import importlib
import pytest

REPORT_MODULES = [
    "src.research.ai_calibration",
    "src.research.asset_research_engine",
    "src.research.counterfactual_engine",
    "src.research.drawdown_analyzer",
    "src.research.feature_intelligence",
    "src.research.filter_ablation",
    "src.research.lookahead_audit",
    "src.research.overfitting_audit",
    "src.research.phase_exit_validator",
    "src.research.project_auditor",
    "src.research.research_decision_engine",
    "src.research.robustness_score",
    "src.research.signal_pipeline_auditor",
    "src.research.signal_quality_optimizer",
    "src.research.threshold_specification",
    "src.services.live_validation_engine",
    "src.services.point_in_time_validator",
    "src.services.strength_backtest_calibration",
    "src.services.strength_probability_calibrator",
    "src.services.stable_expectancy_researcher",
]

_TEMP_DIR = None
_ORIG_VALUES = {}


def pytest_configure(config):
    """Setup isolated environment before test collection."""
    global _TEMP_DIR, _ORIG_VALUES
    _TEMP_DIR = tempfile.mkdtemp(prefix="trade_pytest_isolation_")
    
    # 1. Isolate data/reports
    temp_reports = os.path.join(_TEMP_DIR, "reports")
    if os.path.exists("data/reports"):
        shutil.copytree("data/reports", temp_reports)
    else:
        os.makedirs(temp_reports, exist_ok=True)
        
    # 2. Isolate gemini_usage.json
    temp_usage = os.path.join(_TEMP_DIR, "gemini_usage.json")
    if os.path.exists("gemini_usage.json"):
        shutil.copy("gemini_usage.json", temp_usage)
        
    # 3. Isolate data/gating_state.json & audit log
    temp_gating = os.path.join(_TEMP_DIR, "gating_state.json")
    if os.path.exists("data/gating_state.json"):
        shutil.copy("data/gating_state.json", temp_gating)
    temp_audit = os.path.join(_TEMP_DIR, "gating_audit.log")

    # Patch report modules
    for mod_name in REPORT_MODULES:
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "REPORTS_DIR"):
                _ORIG_VALUES[f"{mod_name}.REPORTS_DIR"] = getattr(mod, "REPORTS_DIR")
                setattr(mod, "REPORTS_DIR", temp_reports)
        except Exception:
            pass

    # Patch default args in data_quality, stress_testing, walk_forward_validator
    for mod_name, func_name in [
        ("src.research.data_quality", "DataQualityAuditor.export_reports"),
        ("src.research.stress_testing", "ExecutionStressTester.run_stress_suite"),
        ("src.research.walk_forward_validator", "WalkForwardValidator.export_reports"),
    ]:
        try:
            mod = importlib.import_module(mod_name)
            cls_name, m_name = func_name.split(".")
            cls_obj = getattr(mod, cls_name)
            func_obj = getattr(cls_obj, m_name)
            # Find and patch default arg
            if hasattr(func_obj, "__defaults__") and func_obj.__defaults__:
                new_defaults = tuple(
                    temp_reports if d == "data/reports" else d for d in func_obj.__defaults__
                )
                _ORIG_VALUES[f"{mod_name}.{func_name}.defaults"] = func_obj.__defaults__
                func_obj.__defaults__ = new_defaults
        except Exception:
            pass

    # Patch request_manager
    try:
        import src.services.ai.request_manager as rm
        _ORIG_VALUES["rm._USAGE_FILE_PATH"] = getattr(rm, "_USAGE_FILE_PATH", None)
        setattr(rm, "_USAGE_FILE_PATH", temp_usage)
    except Exception:
        pass

    # Patch gating_control
    try:
        import src.core.gating_control as gc
        _ORIG_VALUES["gc._STATE_FILE_PATH"] = getattr(gc, "_STATE_FILE_PATH", "data/gating_state.json")
        _ORIG_VALUES["gc._AUDIT_LOG_PATH"] = getattr(gc, "_AUDIT_LOG_PATH", "data/audit/gating_audit.log")
        _ORIG_VALUES["gc.defaults"] = gc.GatingControlManager.__init__.__defaults__
        setattr(gc, "_STATE_FILE_PATH", temp_gating)
        setattr(gc, "_AUDIT_LOG_PATH", temp_audit)
        gc.GatingControlManager.__init__.__defaults__ = (temp_gating, temp_audit)
        gc._gating_control_instance = None
    except Exception:
        pass

    # Patch signal_repository
    try:
        import src.services.signal_repository as sr
        temp_signal_records = os.path.join(_TEMP_DIR, "signal_records.json")
        # Pre-seed with existing file so tests that read records still work
        if os.path.exists("signal_records.json"):
            import shutil as _shutil
            _shutil.copy("signal_records.json", temp_signal_records)
        _ORIG_VALUES["sr._REPO_FILE_PATH"] = getattr(sr, "_REPO_FILE_PATH", None)
        _ORIG_VALUES["sr._repo_instance"] = getattr(sr, "_repo_instance", None)
        _ORIG_VALUES["sr.defaults"] = sr.SignalRepository.__init__.__defaults__
        setattr(sr, "_REPO_FILE_PATH", temp_signal_records)
        sr.SignalRepository.__init__.__defaults__ = (temp_signal_records,)
        # Reset singleton so next call re-initialises with temp path
        sr._repo_instance = None
    except Exception:
        pass

    # Patch forward_shadow engine
    try:
        import src.research.governance.forward_shadow as fwd_mod
        temp_fwd_db = os.path.join(_TEMP_DIR, "isolated_forward_shadow.db")
        if os.path.exists("data/historical/historical_market_data.db"):
            try:
                import sqlite3
                conn_src = sqlite3.connect("file:data/historical/historical_market_data.db?mode=ro", uri=True)
                conn_dst = sqlite3.connect(temp_fwd_db)
                c_src = conn_src.cursor()
                row = c_src.execute("SELECT sql FROM sqlite_master WHERE name=?", ("forward_shadow_signals",)).fetchone()
                if row and row[0]:
                    conn_dst.execute(row[0])
                    rows = c_src.execute("SELECT * FROM forward_shadow_signals").fetchall()
                    if rows:
                        placeholders = ",".join(["?"] * len(rows[0]))
                        conn_dst.executemany(f"INSERT INTO forward_shadow_signals VALUES ({placeholders})", rows)
                    conn_dst.commit()
                conn_src.close()
                conn_dst.close()
            except Exception:
                pass

        _ORIG_VALUES["fwd_mod._forward_shadow_engine"] = getattr(fwd_mod, "_forward_shadow_engine", None)
        _ORIG_VALUES["fwd_engine_init_defaults"] = fwd_mod.ForwardShadowEngine.__init__.__defaults__
        fwd_mod.ForwardShadowEngine.__init__.__defaults__ = (temp_fwd_db,)
        fwd_mod._forward_shadow_engine = fwd_mod.ForwardShadowEngine(db_path=temp_fwd_db)
    except Exception:
        pass


def pytest_unconfigure(config):
    """Restore originals and clean up temporary directory."""
    global _TEMP_DIR, _ORIG_VALUES
    
    # Restore gating control
    try:
        import src.core.gating_control as gc
        if "gc._STATE_FILE_PATH" in _ORIG_VALUES:
            setattr(gc, "_STATE_FILE_PATH", _ORIG_VALUES["gc._STATE_FILE_PATH"])
        if "gc._AUDIT_LOG_PATH" in _ORIG_VALUES:
            setattr(gc, "_AUDIT_LOG_PATH", _ORIG_VALUES["gc._AUDIT_LOG_PATH"])
        if "gc.defaults" in _ORIG_VALUES:
            gc.GatingControlManager.__init__.__defaults__ = _ORIG_VALUES["gc.defaults"]
        gc._gating_control_instance = None
    except Exception:
        pass

    # Restore request manager
    try:
        import src.services.ai.request_manager as rm
        if "rm._USAGE_FILE_PATH" in _ORIG_VALUES:
            setattr(rm, "_USAGE_FILE_PATH", _ORIG_VALUES["rm._USAGE_FILE_PATH"])
    except Exception:
        pass

    # Restore signal_repository
    try:
        import src.services.signal_repository as sr
        if "sr._REPO_FILE_PATH" in _ORIG_VALUES:
            setattr(sr, "_REPO_FILE_PATH", _ORIG_VALUES["sr._REPO_FILE_PATH"])
        if "sr.defaults" in _ORIG_VALUES:
            sr.SignalRepository.__init__.__defaults__ = _ORIG_VALUES["sr.defaults"]
        # Reset singleton so next production call reinitialises with real path
        sr._repo_instance = None
    except Exception:
        pass

    # Restore forward_shadow engine
    try:
        import src.research.governance.forward_shadow as fwd_mod
        if "fwd_engine_init_defaults" in _ORIG_VALUES:
            fwd_mod.ForwardShadowEngine.__init__.__defaults__ = _ORIG_VALUES["fwd_engine_init_defaults"]
        if "fwd_mod._forward_shadow_engine" in _ORIG_VALUES:
            fwd_mod._forward_shadow_engine = _ORIG_VALUES["fwd_mod._forward_shadow_engine"]
    except Exception:
        pass

    # Restore report modules
    for key, orig_val in _ORIG_VALUES.items():
        if key.endswith(".REPORTS_DIR"):
            mod_name = key[:-len(".REPORTS_DIR")]
            try:
                mod = importlib.import_module(mod_name)
                setattr(mod, "REPORTS_DIR", orig_val)
            except Exception:
                pass
        elif key.endswith(".defaults") and not key.startswith("gc.") and not key.startswith("sr."):
            mod_cls_func = key[:-len(".defaults")]
            parts = mod_cls_func.split(".")
            mod_name = ".".join(parts[:-2])
            cls_name = parts[-2]
            func_name = parts[-1]
            try:
                mod = importlib.import_module(mod_name)
                cls_obj = getattr(mod, cls_name)
                func_obj = getattr(cls_obj, func_name)
                func_obj.__defaults__ = orig_val
            except Exception:
                pass

    # Remove temp dir
    if _TEMP_DIR and os.path.exists(_TEMP_DIR):
        shutil.rmtree(_TEMP_DIR, ignore_errors=True)
