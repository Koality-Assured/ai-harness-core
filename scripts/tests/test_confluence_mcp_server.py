"""Unit tests for Confluence Model Context Protocol (MCP) server.

tags: [tests, confluence, mcp, jsonrpc, tools]
"""

from __future__ import annotations

import unittest
from scripts.confluence.confluence_mcp_server import (
    TOOLS_REGISTRY,
    handle_tool_call,
    SERVER_NAME,
    SERVER_VERSION,
)


class TestConfluenceMCPServer(unittest.TestCase):
    def test_tools_registry_contains_required_tools(self) -> None:
        tool_names = [t["name"] for t in TOOLS_REGISTRY]
        self.assertIn("confluence_create_space", tool_names)
        self.assertIn("confluence_scaffold_ia", tool_names)
        self.assertIn("confluence_publish_corpus", tool_names)
        self.assertIn("confluence_check_drift", tool_names)
        self.assertIn("confluence_search_cql", tool_names)
        self.assertIn("confluence_create_page", tool_names)
        self.assertIn("confluence_get_page", tool_names)

    def test_handle_tool_call_scaffold_ia_dry_run(self) -> None:
        res = handle_tool_call(
            "confluence_scaffold_ia",
            {"workspace": "koality-assured", "space_key": "SEC", "dry_run": True},
        )
        self.assertTrue(res.get("ok"))
        self.assertIn("parent_id_map", res)
        self.assertIn("Documentation/Standards", res["parent_id_map"])

    def test_handle_tool_call_create_space_dry_run(self) -> None:
        res = handle_tool_call(
            "confluence_create_space",
            {"workspace": "koality-assured", "space_key": "SEC", "name": "Information Security"},
        )
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("space_key"), "SEC")

    def test_handle_tool_call_search_cql_dry_run(self) -> None:
        res = handle_tool_call(
            "confluence_search_cql",
            {"workspace": "koality-assured", "cql": "space = 'SEC'"},
        )
        self.assertTrue(res.get("ok"))
        self.assertIn("results", res)

    def test_handle_unknown_tool(self) -> None:
        res = handle_tool_call("unknown_tool_xyz", {})
        self.assertFalse(res.get("ok"))
        self.assertIn("Unknown tool", res.get("error", ""))


if __name__ == "__main__":
    unittest.main()
