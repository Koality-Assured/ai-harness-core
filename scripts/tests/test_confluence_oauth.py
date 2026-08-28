"""Unit tests for Confluence OAuth 2.0 (3LO) authorization and Cloud ID discovery.

tags: [tests, confluence, oauth, 3lo, tokens]
"""

from __future__ import annotations

import tempfile
import unittest
import urllib.parse
from pathlib import Path

from scripts.confluence.confluence_oauth import (
    build_authorization_url,
    exchange_code_for_token,
    refresh_access_token,
    get_accessible_resources,
    save_token_cache,
    load_token_cache,
    clear_token_cache,
    login_browser,
    DEFAULT_SCOPES,
)
from scripts.confluence.confluence_ops import _get_api_url, _get_web_url, _get_auth_headers


class TestConfluenceOAuth(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = Path(self.temp_dir.name) / ".test_oauth_token.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_authorization_url(self) -> None:
        client_id = "test_client_12345"
        redirect_uri = "http://localhost:8080/callback"
        auth_url, state = build_authorization_url(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=["read:confluence-content.all", "write:confluence-content"],
        )
        parsed = urllib.parse.urlparse(auth_url)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "auth.atlassian.com")
        self.assertEqual(parsed.path, "/authorize")

        params = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(params["audience"][0], "api.atlassian.com")
        self.assertEqual(params["client_id"][0], client_id)
        self.assertEqual(params["redirect_uri"][0], redirect_uri)
        self.assertEqual(params["state"][0], state)
        self.assertEqual(params["response_type"][0], "code")
        self.assertIn("read:confluence-content.all", params["scope"][0])

    def test_exchange_code_for_token_dry_run(self) -> None:
        res = exchange_code_for_token(
            client_id="mock_id",
            client_secret="mock_sec",
            code="mock_code",
            dry_run=True,
        )
        self.assertTrue(res["ok"])
        self.assertTrue(res["access_token"].startswith("mock_oauth_access_token_"))
        self.assertTrue(res["refresh_token"].startswith("mock_oauth_refresh_token_"))
        self.assertEqual(res["token_type"], "Bearer")
        self.assertEqual(res["expires_in"], 3600)

    def test_refresh_access_token_dry_run(self) -> None:
        res = refresh_access_token(
            client_id="mock_id",
            client_secret="mock_sec",
            refresh_token="mock_refresh",
            dry_run=True,
        )
        self.assertTrue(res["ok"])
        self.assertTrue(res["access_token"].startswith("mock_refreshed_access_token_"))
        self.assertEqual(res["token_type"], "Bearer")

    def test_get_accessible_resources_dry_run(self) -> None:
        res = get_accessible_resources("mock_token", dry_run=True)
        self.assertEqual(len(res), 1)
        site = res[0]
        self.assertEqual(site["name"], "koality-assured")
        self.assertEqual(site["url"], "https://koality-assured.atlassian.net")
        self.assertEqual(site["id"], "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    def test_token_cache_lifecycle(self) -> None:
        token_data = {
            "access_token": "secret_access_token",
            "refresh_token": "secret_refresh_token",
            "active_cloud_id": "test-cloud-id-123",
        }
        save_token_cache(token_data, path=self.cache_file)
        self.assertTrue(self.cache_file.exists())

        loaded = load_token_cache(path=self.cache_file)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["access_token"], "secret_access_token")
        self.assertEqual(loaded["active_cloud_id"], "test-cloud-id-123")

        cleared = clear_token_cache(path=self.cache_file)
        self.assertTrue(cleared)
        self.assertFalse(self.cache_file.exists())

    def test_login_browser_dry_run(self) -> None:
        res = login_browser(
            client_id="test_id",
            client_secret="test_secret",
            dry_run=True,
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["action"], "oauth_login")
        self.assertIn("token", res)
        tok = res["token"]
        self.assertEqual(tok["active_cloud_id"], "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        self.assertEqual(tok["active_site_url"], "https://koality-assured.atlassian.net")

    def test_ops_oauth_gateway_resolution(self) -> None:
        # Default without OAuth
        api_url = _get_api_url(workspace="koality-assured")
        self.assertEqual(api_url, "https://koality-assured.atlassian.net")
        web_url = _get_web_url(workspace="koality-assured")
        self.assertEqual(web_url, "https://koality-assured.atlassian.net")

        # Explicit base_url overrides
        custom_api = _get_api_url(base_url="https://api.atlassian.com/ex/confluence/custom-id")
        self.assertEqual(custom_api, "https://api.atlassian.com/ex/confluence/custom-id")


if __name__ == "__main__":
    unittest.main()
