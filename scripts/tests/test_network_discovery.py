"""Tests for the bounded network discovery helper.

tags: [network, discovery, nmap, tests]
routing_hints: [network-discovery, nmap, validation]
"""

from __future__ import annotations

import ipaddress
import unittest
from unittest.mock import patch

from scripts.network.discover_network import (
    InterfaceNetwork,
    build_nmap_command,
    canonical_network,
    parse_linux_interfaces,
    parse_nmap_xml,
    parse_windows_interfaces,
    run_nmap,
    validate_targets,
)


class NetworkDiscoveryTests(unittest.TestCase):
    def test_windows_parser_extracts_private_network(self) -> None:
        text = """
Ethernet adapter Ethernet:
   IPv4 Address. . . . . . . . . . . : 192.168.0.236(Preferred)
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
"""
        self.assertEqual(parse_windows_interfaces(text)[0].network, "192.168.0.0/24")

    def test_linux_parser_extracts_private_network(self) -> None:
        text = "2: eth0    inet 10.0.0.8/24 brd 10.0.0.255 scope global eth0"
        self.assertEqual(parse_linux_interfaces(text)[0].network, "10.0.0.0/24")

    def test_rejects_public_and_oversized_targets(self) -> None:
        with self.assertRaises(ValueError):
            canonical_network("8.8.8.0/24", max_hosts=256)
        with self.assertRaises(ValueError):
            canonical_network("192.168.0.0/16", max_hosts=256)

    def test_target_must_be_local_and_confirmed(self) -> None:
        local = [InterfaceNetwork("Ethernet", "192.168.0.236", "192.168.0.0/24")]
        with self.assertRaises(ValueError):
            validate_targets(["192.168.1.0/24"], ["192.168.1.0/24"], local, max_hosts=256, require_confirmation=True)
        target = validate_targets(["192.168.0.0/24"], ["192.168.0.0/24"], local, max_hosts=256, require_confirmation=True)
        self.assertEqual(target, [ipaddress.ip_network("192.168.0.0/24")])

    def test_nmap_command_is_fixed_to_host_discovery(self) -> None:
        command = build_nmap_command(ipaddress.ip_network("192.168.0.0/24"), nmap_path="nmap", timeout=30)
        self.assertIn("-sn", command)
        self.assertIn("-n", command)
        self.assertNotIn("-sV", command)
        self.assertEqual(command[-1], "192.168.0.0/24")

    def test_xml_parser_returns_ipv4_hosts(self) -> None:
        xml = '<nmaprun><host><status state="up"/><address addr="192.168.0.1" addrtype="ipv4"/></host></nmaprun>'
        self.assertEqual(parse_nmap_xml(xml), [{"address": "192.168.0.1", "state": "up"}])

    @patch("scripts.network.discover_network.subprocess.run")
    def test_run_nmap_uses_subprocess_result(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = '<nmaprun><host><status state="up"/><address addr="192.168.0.1" addrtype="ipv4"/></host></nmaprun>'
        run.return_value.stderr = ""
        result = run_nmap(ipaddress.ip_network("192.168.0.0/24"), nmap_path="nmap", timeout=30)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["hosts"]), 1)


if __name__ == "__main__":
    unittest.main()
