"""Settings that are easy to get wrong and expensive to get wrong."""
import importlib
import os
from pathlib import Path


def _config_with(tmp_path: Path, **env):
    """Re-import config with a clean environment pointed at a throwaway storage directory."""
    saved = {k: os.environ.get(k) for k in ("LL_JWT_SECRET", "LL_STORAGE_DIR")}
    os.environ["LL_STORAGE_DIR"] = str(tmp_path)
    os.environ.pop("LL_JWT_SECRET", None)
    for k, v in env.items():
        os.environ[k] = v
    try:
        import backend.api.config as config
        return importlib.reload(config)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_the_signing_key_is_the_same_for_every_worker(tmp_path):
    """A key generated per process means `uvicorn --workers 4` hands out tokens its own
    siblings reject. Without LL_JWT_SECRET the key is written once and shared."""
    first = _config_with(tmp_path).JWT_SECRET
    second = _config_with(tmp_path).JWT_SECRET   # a second worker, same machine
    assert first == second
    assert (tmp_path / "jwt_secret").read_text(encoding="utf-8").strip() == first
    assert len(first) >= 32


def test_the_environment_still_wins(tmp_path):
    assert _config_with(tmp_path, LL_JWT_SECRET="from-the-environment").JWT_SECRET == "from-the-environment"


def test_the_upload_limits_are_sane(tmp_path):
    c = _config_with(tmp_path)
    assert 0 < c.MAX_UPLOAD_MB <= 100
    assert 1_000_000 < c.MAX_IMAGE_PIXELS <= 500_000_000
    assert ".pdf" in c.ALLOWED_EXTENSIONS and ".exe" not in c.ALLOWED_EXTENSIONS
