"""Tests for environment configuration isolation:
1. Environment variables from current working directory are not arbitrarily loaded.
2. In production or on Render, local .env files are never loaded into Settings.
3. Dedicated local/staging configuration is strictly isolated.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.config import Settings, _resolve_env_files


class TestEnvironmentConfigIsolation(unittest.TestCase):
    def test_production_environment_ignores_local_env_files(self):
        """When ENVIRONMENT=production, _resolve_env_files returns None."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "RENDER": ""}, clear=False):
            result = _resolve_env_files()
            self.assertIsNone(result)

    def test_render_environment_ignores_local_env_files(self):
        """When RENDER=true, _resolve_env_files returns None."""
        with patch.dict(os.environ, {"RENDER": "true", "ENVIRONMENT": "development"}, clear=False):
            result = _resolve_env_files()
            self.assertIsNone(result)

    def test_explicit_env_file_honored_when_valid(self):
        """When an explicit ENV_FILE path is provided, it is returned as a single candidate."""
        backend_dir = Path(__file__).resolve().parent.parent
        example_file = backend_dir / ".env.example"
        if example_file.is_file():
            with patch.dict(os.environ, {"ENV_FILE": str(example_file), "RENDER": "", "ENVIRONMENT": "development"}, clear=False):
                result = _resolve_env_files()
                self.assertEqual(result, (str(example_file),))

    def test_cwd_outside_repo_is_not_loaded(self):
        """A random .env in another directory (like /tmp or parent) is never in _resolve_env_files."""
        with patch.dict(os.environ, {"RENDER": "", "ENVIRONMENT": "development", "ENV_FILE": ""}, clear=False):
            candidates = _resolve_env_files()
            if candidates:
                for path in candidates:
                    p = Path(path).resolve()
                    # Must be within the p2p project tree
                    self.assertTrue(
                        "p2p" in str(p),
                        f"Expected path within p2p project tree, got {p}"
                    )
