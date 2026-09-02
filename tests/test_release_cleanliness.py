import ast
import re
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGE = SRC / "supermarkt"


def _release_paths():
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        yield from ROOT.rglob("*")
        return

    for item in result.stdout.split(b"\0"):
        if item:
            yield ROOT / item.decode("utf-8")


def _dependency_names() -> set[str]:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    result = set()
    for requirement in metadata["project"]["dependencies"]:
        name = re.split(r"[<>=!~;\[\s]", requirement, maxsplit=1)[0]
        result.add(name.replace("_", "-").casefold())
    return result


def _external_imports() -> set[str]:
    external = set()
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".", 1)[0]]
            else:
                continue
            for name in names:
                if name not in sys.stdlib_module_names and name != "supermarkt":
                    external.add(name)
    return external


def test_source_root_contains_only_the_package():
    assert not list(SRC.glob("*.py"))
    assert {path.name for path in SRC.iterdir() if path.is_dir() and not path.name.endswith(".egg-info")} == {"supermarkt"}


def test_declared_runtime_dependencies_are_intentional_and_small():
    assert _dependency_names() == {"fastapi", "pydantic", "curl-cffi", "beautifulsoup4", "uvicorn", "python-multipart", "tzdata", "certifi"}


def test_external_python_imports_match_declared_runtime_components():
    assert _external_imports() == {"fastapi", "pydantic", "curl_cffi", "bs4", "certifi"}


def test_docker_system_dependencies_are_actually_used():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime = "\n".join(path.read_text(encoding="utf-8") for path in (PACKAGE / "sources").glob("*.py"))
    assert "chromium" in dockerfile and '"chromium"' in runtime
    assert " curl" in dockerfile and '"curl"' in runtime
    assert 'CMD ["uvicorn"' in dockerfile
    assert "USER 10001" in dockerfile
    assert "chown -R korbklar:korbklar /home/korbklar /data /app" in dockerfile
    assert "dumb-init" in dockerfile
    assert 'ENTRYPOINT ["dumb-init", "--"]' in dockerfile


def test_standalone_docker_defaults_use_the_persistent_volume():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "SUPERMARKT_DATA_DIR=/data" in dockerfile
    assert "SUPERMARKT_CACHE_DB=/data/supermarkt-cache.sqlite3" in dockerfile
    assert "SUPERMARKT_SIGNING_SECRET_FILE=/data/.signing-secret" in dockerfile
    assert "SUPERMARKT_IMAGE_CACHE_DIR=/data/supermarkt-images" in dockerfile
    assert "SUPERMARKT_KAUFLAND_CACHE_DIR=/data/kaufland" in dockerfile
    assert "SUPERMARKT_REWE_CACHE_DIR=/data/rewe" in dockerfile


def test_compose_is_one_self_contained_service():
    compose = (ROOT / "compose.yml").read_text(encoding="utf-8")
    assert compose.count("  korbklar:\n") == 1
    assert "korbklar-data:/data" in compose
    assert '"${SUPERMARKT_PORT:-8000}:8000"' in compose
    assert "healthcheck:" in compose
    assert "SUPERMARKT_DATA_DIR: ${SUPERMARKT_DATA_DIR:-/data}" in compose


def test_legacy_configuration_names_are_gone():
    legacy_names = ("TOOL" + "_API_KEY", "PUBLIC" + "_TOOL_URL")
    texts = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in _release_paths()
        if path.is_file() and path.suffix not in {".pyc", ".whl", ".gz", ".zip"}
    )
    assert all(name not in texts for name in legacy_names)


def test_runtime_version_matches_package_metadata():
    from supermarkt.config import USER_AGENT
    from supermarkt.version import __version__

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == __version__
    assert USER_AGENT == f"korb-klar/{__version__}"
    assert __version__ == "0.1.11"


def test_default_host_port_is_configurable_without_changing_container_port():
    compose = (ROOT / "compose.yml").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert '"${SUPERMARKT_PORT:-8000}:8000"' in compose
    assert "SUPERMARKT_PORT=8000" in env_example
    assert 'EXPOSE 8000' in (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_release_contains_no_runtime_state_or_patch_residue():
    forbidden_dirs = {".git", "build", "dist", "data"}
    forbidden_suffixes = {".rej", ".orig", ".bak", ".log", ".sqlite3", ".sqlite3-wal", ".sqlite3-shm"}
    for path in _release_paths():
        relative = path.relative_to(ROOT)
        assert not any(part in forbidden_dirs for part in relative.parts), relative
        if path.is_file():
            assert path.name != ".env", relative
            assert not any(path.name.endswith(suffix) for suffix in forbidden_suffixes), relative


def test_release_has_no_development_machine_references():
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in _release_paths()
        if path.is_file() and path.suffix in {".py", ".md", ".toml", ".yml", ".yaml", ".example", ".txt"}
    )
    for marker in ("/srv/" + "docker/", "192." + "168.0.", "042" + "09"):
        assert marker not in text


def test_release_carries_no_stray_compose_file():
    compose_files = sorted(path.name for path in ROOT.glob("compose*.yml"))
    assert compose_files == ["compose.kitchenowl.yml", "compose.proxy.yml", "compose.yml"]
    for name in compose_files:
        assert "supermarkt-ts" not in (ROOT / name).read_text(encoding="utf-8")


def test_all_supported_compose_environment_variables_are_documented():
    compose = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(ROOT.glob("compose*.yml"))
    )
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    names = set(re.findall(r"\$\{((?:SUPERMARKT|KORBKLAR|KITCHENOWL)_[A-Z0-9_]+)", compose))
    names.add("SUPERMARKT_PORT")
    for name in names:
        assert f"{name}=" in env_example, name


def test_the_proxy_is_a_separate_compose_file():
    """TLS must never be needed to run the comparison."""
    base = (ROOT / "compose.yml").read_text(encoding="utf-8")
    assert "caddy" not in base.casefold()
    overlay = (ROOT / "compose.proxy.yml").read_text(encoding="utf-8")
    # The overlay adds to the base rather than repeating it, and it takes the
    # published port off the public interfaces instead of adding a second one.
    assert "image: ghcr.io/lesecuritae/korbklar" not in overlay
    assert "ports: !override" in overlay
    assert "${KORBKLAR_BIND_ADDRESS:-127.0.0.1}:${SUPERMARKT_PORT:-8000}:8000" in overlay
    assert "condition: service_healthy" in overlay


def test_the_proxy_never_forwards_a_client_supplied_source_address():
    site = (ROOT / "deploy/caddy/sites/korbklar.caddy").read_text(encoding="utf-8")
    # Overwriting rather than appending is what keeps anything behind the
    # proxy from ever seeing an address the client chose.
    assert "header_up X-Forwarded-For {remote_host}" in site
    assert "{$KORBKLAR_DOMAIN}" in site
    for name in ("Caddyfile", "Caddyfile.kitchenowl"):
        entry = (ROOT / "deploy/caddy" / name).read_text(encoding="utf-8")
        assert "{$KORBKLAR_ACME_EMAIL}" in entry
        # Both entry points import the same site file, so the header handling
        # above cannot drift apart between them.
        assert "import /etc/caddy/sites/korbklar.caddy" in entry


def test_the_shopping_list_is_a_separate_compose_file():
    """KitchenOwl must never be needed to run the comparison."""
    base = (ROOT / "compose.yml").read_text(encoding="utf-8")
    assert "kitchenowl" not in base.casefold()
    overlay = (ROOT / "compose.kitchenowl.yml").read_text(encoding="utf-8")
    assert "image: ghcr.io/lesecuritae/korbklar" not in overlay
    # The backend speaks uwsgi rather than HTTP, so KorbKlar goes through the
    # web container, which proxies /api/.
    assert "SUPERMARKT_KITCHENOWL_URL:-http://kitchenowl-web}" in overlay
    # The image defaults its upstream to the service name from its own compose
    # example; nginx refuses to start when that host does not resolve.
    assert "BACK_URL: kitchenowl-back:5000" in overlay
    # A household list is not published on every interface by default.
    assert "${KITCHENOWL_BIND_ADDRESS:-127.0.0.1}" in overlay


def test_kitchenowl_cannot_start_without_a_signing_key():
    compose = (ROOT / "compose.kitchenowl.yml").read_text(encoding="utf-8")
    # KitchenOwl falls back to a published default and accepts an empty key,
    # so the stack has to refuse before its backend comes up.
    assert "kitchenowl-secret-check:" in compose
    assert "condition: service_completed_successfully" in compose
    assert "KITCHENOWL_JWT_SECRET} -lt 32" in compose
    assert 'OPEN_REGISTRATION: "false"' in compose


def test_every_relative_documentation_link_resolves():
    """A moved section must not leave a dead link behind."""
    pages = [ROOT / "README.md", ROOT / "README.de.md", ROOT / "README.en.md"]
    pages += sorted((ROOT / "docs").glob("*.md"))
    broken = []
    for page in pages:
        broken.extend(
            f"{page.name} -> {target}"
            for target in re.findall(r"\]\(([^)#:]+\.md)\)", page.read_text(encoding="utf-8"))
            if not (page.parent / target).resolve().is_file()
        )
    assert not broken, broken


def test_release_has_no_private_or_internal_revision_markers():
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in _release_paths()
        if path.is_file() and path.suffix in {".py", ".md", ".toml", ".yml", ".yaml", ".example", ".txt"}
    )
    forbidden = (
        "SNAPSHOT" + "_SCHEMA_VERSION",
        "supermarket_snapshots_" + "v",
        "idx_supermarket_" + "v",
        "INSTALLER" + "_REVISION",
        "FINALER VM-TEST" + "INSTALLER",
        "brand-footnote" + "-fix",
        "general" + "17",
        "042" + "09",
        "tail" + "scale",
        "TS_" + "AUTHKEY",
    )
    for marker in forbidden:
        assert marker.casefold() not in text.casefold(), marker


def test_public_branding_is_korbklar():
    public_files = [
        ROOT / "README.md",
        ROOT / "compose.yml",
        ROOT / "pyproject.toml",
        ROOT / ".env.example",
        ROOT / "src/supermarkt/asgi.py",
        ROOT / "src/supermarkt/ui.py",
        ROOT / "src/supermarkt/assets.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in public_files)
    assert "Supermarkt-Preisvergleich" not in text
    assert "KorbKlar" in text
    assert "supermarkt-preisvergleich/<Version>" not in text


def test_readme_header_is_well_formed_svg():
    import xml.etree.ElementTree as ET

    header = ROOT / "docs/readme-header.svg"
    root = ET.fromstring(header.read_text(encoding="utf-8"))
    assert root.tag.endswith("svg")
    assert root.attrib.get("viewBox") == "0 0 1200 480"
