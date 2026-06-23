"""Public repository and HACS publication guardrails."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = PROJECT_ROOT / "custom_components" / "saj_as1_modbus"
REPO_URL = "https://github.com/mactron254/home-assistant-saj-as1-modbus"


def test_hacs_manifest_exists_and_targets_custom_repository() -> None:
    """HACS custom repository metadata should be present at repository root."""
    hacs = json.loads((PROJECT_ROOT / "hacs.json").read_text(encoding="utf-8"))

    assert hacs["name"] == "SAJ AS1 Modbus"
    assert hacs["homeassistant"] >= "2026.5.0"
    assert hacs["hacs"] >= "2.0.0"


def test_public_manifest_urls_and_owner_are_ready() -> None:
    """The custom integration manifest should point to the public repository."""
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["documentation"] == REPO_URL
    assert manifest["issue_tracker"] == f"{REPO_URL}/issues"
    assert manifest["codeowners"] == ["@mactron254"]
    assert manifest["version"] == "3.1.0"


def test_public_readmes_include_disclaimer_and_transport_scope() -> None:
    """Public entry points must make unofficial and Modbus TCP/IP scope clear."""
    expected = {
        "README.md": (
            "Unofficial community integration",
            "Not affiliated with, endorsed, approved, or supported by SAJ",
            "Modbus TCP/IP only",
        ),
        "README.es.md": (
            "Integracion comunitaria no oficial",
            "No afiliada, aprobada, respaldada ni soportada por SAJ",
            "Modbus TCP/IP solamente",
        ),
        "README.de.md": (
            "Inoffizielle Community-Integration",
            "nicht von SAJ genehmigt",
            "nur Modbus TCP/IP",
        ),
        "README.fr.md": (
            "Integration communautaire non officielle",
            "ni prise en charge par SAJ",
            "Modbus TCP/IP uniquement",
        ),
    }

    for file_name, snippets in expected.items():
        text = (PROJECT_ROOT / file_name).read_text(encoding="utf-8")
        for snippet in snippets:
            assert snippet in text


def test_legal_and_safety_documents_exist() -> None:
    """Repository should include visible liability and safety documents."""
    for file_name in (
        "LICENSE",
        "DISCLAIMER.md",
        "SAFETY.md",
        "NOTICE.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "docs/AI_CONTEXT.md",
        "docs/REFERENCES.md",
    ):
        path = PROJECT_ROOT / file_name
        assert path.exists(), file_name
        assert path.stat().st_size > 0, file_name

    disclaimer = (PROJECT_ROOT / "DISCLAIMER.md").read_text(encoding="utf-8")
    assert "SAJ does not develop, review, validate, or provide support" in disclaimer
    assert "AI assistance" in disclaimer
    assert "not legal advice" in disclaimer


def test_internal_material_is_excluded_from_public_repository() -> None:
    """Large/private working material should stay out of the public repo."""
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    for ignored in (
        "copia_As1/",
        "docs/internal/",
        "docs/emhass/",
        "docs/evcc/",
        "docs/INFORME_TECNICO_COMPLETO.md",
        "docs/README_CORRECCIONES.md",
        "docs/reference/AS1Main*.pdf",
        "docs/reference/Documentacion pymodbus*.md",
        "docs/reference/host_controller_display_panel_protocol.md",
        "*.log",
        ".env",
    ):
        assert ignored in gitignore


def test_github_templates_and_validation_workflow_exist() -> None:
    """Public repository should have issue templates, PR template, and CI."""
    workflow = PROJECT_ROOT / ".github" / "workflows" / "validate.yml"
    workflow_text = workflow.read_text(encoding="utf-8")

    assert "hacs/action@main" in workflow_text
    assert "category: integration" in workflow_text
    assert "home-assistant/actions/hassfest@master" in workflow_text
    assert "pytest tests --rootdir=tests" in workflow_text
    assert "mypy --strict" in workflow_text

    assert (PROJECT_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").exists()
    assert (PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").exists()
    assert (
        PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml"
    ).exists()


def test_brand_asset_exists_for_hacs() -> None:
    """HACS requires brand assets for integration repositories."""
    icon = PROJECT_ROOT / "brands" / "saj_as1_modbus" / "icon.png"

    assert icon.exists()
    assert icon.stat().st_size > 0
