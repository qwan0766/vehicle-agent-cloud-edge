from pathlib import Path


WORKFLOW = Path(".github/workflows/ci.yml")


def test_ci_workflow_runs_offline_delivery_check_without_real_keys():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "name: Offline Delivery CI" in text
    assert "DEEPSEEK_API_KEY: \"\"" in text
    assert "AMAP_API_KEY: \"\"" in text
    assert "BAIDU_MAP_AK: \"\"" in text
    assert "OPENCHARGEMAP_API_KEY: \"\"" in text
    assert "LOCAL_LLM_PROVIDER: mock_local" in text
    assert "ENABLE_LANGGRAPH: \"1\"" in text
    assert "python scripts/run_delivery_check.py --unit-timeout 300" in text


def test_ci_workflow_installs_optional_runtime_dependencies_and_uploads_report():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "python -m pip install pytest" in text
    assert "python -m pip install -r requirements-optional.txt" in text
    assert "actions/upload-artifact@v4" in text
    assert "reports/delivery_check_report.md" in text
