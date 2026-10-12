"""Automated repository branding, beautification, and hardening tool.

Synthesizes high-contrast vector XML logos and hero banners adhering to the
Koality-Assured design language and Art Router representation registry, generates
auto-updating live badges (CI, license, language, domain, conventional commits),
produces authoritative README.md heroes, and hardens pyproject.toml against
setuptools flat-layout discovery collisions.

tags: [repos, branding, beautification, svg, badges, hardening]
routing_hints: [beautify, branding, vector-logo, vector-banner, badges, pyproject-hardening]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))


DEFAULT_ORG = "Koality-Assured"

MIT_LICENSE_TEMPLATE = """MIT License

Copyright (c) 2026 Koality-Assured

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


@dataclass
class DomainBrandingSpec:
    """Design, branding, and hardening parameters for a repository."""

    name: str
    domain: str = "none"
    title: str = ""
    tagline: str = ""
    org: str = DEFAULT_ORG
    primary_color: str = "#00F0FF"
    secondary_color: str = "#7C3AED"
    accent_color: str = "#10B981"
    motif: str = "compass"
    category_label: str = "KOALITY-ASSURED • DOMAIN HARNESS"
    chips: list[str] = field(default_factory=list)
    ci_workflow: str = "ci.yml"
    python_version: str | None = "3.11+"
    license_type: str = "MIT"
    visibility: str = "public"


DOMAIN_PRESETS: dict[str, dict[str, Any]] = {
    "legal": {
        "title": "Legal Router",
        "tagline": "Domain AI Agent Harness for Legal Research, Compliance & Bluebook Citations",
        "primary_color": "#E11D48",
        "secondary_color": "#9F1239",
        "accent_color": "#F59E0B",
        "motif": "scales",
        "category_label": "KOALITY-ASSURED • DOMAIN HARNESS",
        "chips": ["US Primary Law", "Bluebook Citations", "Contract Risk", "SEC / Compliance"],
    },
    "ui-ux": {
        "title": "UI/UX Router",
        "tagline": "Domain AI Agent Harness for Design Systems, WCAG Conformance & Visual QA",
        "primary_color": "#D946EF",
        "secondary_color": "#8B5CF6",
        "accent_color": "#06B6D4",
        "motif": "artboard",
        "category_label": "KOALITY-ASSURED • DOMAIN HARNESS",
        "chips": ["DTCG Design Tokens", "WCAG 2.2 AAA", "Component Kits", "Visual Regression"],
    },
    "financial": {
        "title": "Financial Advisement Router",
        "tagline": "Domain AI Agent Harness for Quantitative Finance, Portfolio Risk & Regulatory Modeling",
        "primary_color": "#F59E0B",
        "secondary_color": "#10B981",
        "accent_color": "#0F172A",
        "motif": "candlestick",
        "category_label": "KOALITY-ASSURED • DOMAIN HARNESS",
        "chips": ["Markowitz MPT", "Value-at-Risk (VaR)", "SEC Reg BI", "Fixed-Point Decimal"],
    },
    "game-dev": {
        "title": "Game Dev Router",
        "tagline": "Domain AI Agent Harness for Game Mechanics, ECS Architecture & Shader Pipelines",
        "primary_color": "#10B981",
        "secondary_color": "#8B5CF6",
        "accent_color": "#00F0FF",
        "motif": "gamepad",
        "category_label": "KOALITY-ASSURED • DOMAIN HARNESS",
        "chips": ["ECS Systems", "Shader Synthesis", "Game Math / Phys", "Asset Pipelines"],
        "license_type": "Proprietary",
        "visibility": "private",
    },
    "art": {
        "title": "Art Router",
        "tagline": "Domain AI Agent Harness for Generative Art, Vector Assets & Creative Media Pipelines",
        "primary_color": "#A855F7",
        "secondary_color": "#00F0FF",
        "accent_color": "#EC4899",
        "motif": "palette",
        "category_label": "KOALITY-ASSURED • DOMAIN HARNESS",
        "chips": ["24 Representation Routes", "Vector XML Synthesis", "Neural Image Pipelines", "Audio / Video Spec"],
    },
    "inventory": {
        "title": "Koality Inventory",
        "tagline": "Enterprise Multi-Tenant Inventory & Warehouse Platform for AI Agents and Human Operators",
        "primary_color": "#10B981",
        "secondary_color": "#0F172A",
        "accent_color": "#14B8A6",
        "motif": "warehouse",
        "category_label": "KOALITY-ASSURED • ENTERPRISE PLATFORM",
        "chips": ["Agent-First ULID", "PostgreSQL / SQLite", "PWA Barcode Scanner", "FEFO / FIFO Dispatch"],
    },
    "mcp": {
        "title": "Koality Inventory MCP",
        "tagline": "Model Context Protocol Server Exposing Warehouse and Ledger Tools to Autonomous Agents",
        "primary_color": "#14B8A6",
        "secondary_color": "#6366F1",
        "accent_color": "#00F0FF",
        "motif": "socket",
        "category_label": "KOALITY-ASSURED • PROTOCOL SERVER",
        "chips": ["Stdio / Streamable HTTP", "Stock Ledger Tools", "Zero Dual-Transport Drift", "Claude / Antigravity"],
    },
    "harness-core": {
        "title": "AI Harness Core",
        "tagline": "Decoupled Multi-Agent Harness Engine, 5-Tier Context Hierarchy & Sandboxed Worktrees",
        "primary_color": "#00F0FF",
        "secondary_color": "#7C3AED",
        "accent_color": "#E2E8F0",
        "motif": "gear",
        "category_label": "KOALITY-ASSURED • CORE ENGINE",
        "chips": ["5-Tier Context", "Mode A / Mode B", "Worktree Isolation", "Cost Layers"],
    },
    "skills": {
        "title": "Agent Skills & Tools",
        "tagline": "Reusable Agent Skills Library, JSON Schemas & Automated Verification Suites",
        "primary_color": "#F59E0B",
        "secondary_color": "#EAB308",
        "accent_color": "#3B82F6",
        "motif": "puzzle",
        "category_label": "KOALITY-ASSURED • STANDARDS & SKILLS",
        "chips": ["Schema Draft 2020-12", "90+ Domain Skills", "20 Domain Families", "Automated Linter"],
    },
    "standards": {
        "title": "Agent Standards",
        "tagline": "Normative Standards for 5-Tier Context Management, A2A Interaction Protocols & Agent Safety",
        "primary_color": "#2563EB",
        "secondary_color": "#06B6D4",
        "accent_color": "#8B5CF6",
        "motif": "rings",
        "category_label": "KOALITY-ASSURED • NORMATIVE STANDARDS",
        "chips": ["5-Tier Context", "A2A Handshake v1", "Untrusted Boundary Defense", "Exchange Budgets"],
    },
    "security": {
        "title": "Security Standards",
        "tagline": "Normative Cybersecurity Standards & Threat Models Across 20+ Operational Domains",
        "primary_color": "#DC2626",
        "secondary_color": "#F59E0B",
        "accent_color": "#475569",
        "motif": "shield",
        "category_label": "KOALITY-ASSURED • CYBERSECURITY",
        "chips": ["STRIDE Threat Models", "20+ Security Domains", "Zero-Trust Architecture", "Automated Validation"],
    },
    "references": {
        "title": "Industry References",
        "tagline": "Normalized Machine-Readable Catalogs for Industry Security & Engineering Frameworks",
        "primary_color": "#059669",
        "secondary_color": "#D97706",
        "accent_color": "#334155",
        "motif": "columns",
        "category_label": "KOALITY-ASSURED • REFERENCE CATALOGS",
        "chips": ["OWASP Top 10", "MITRE ATT&CK", "NIST CSF / SP 800-53", "CWE Top 25"],
    },
    "benchmarks": {
        "title": "AI Research & Benchmarks",
        "tagline": "Comparative AI Agent Harness Research, Empirical Benchmarks & Cost Telemetry",
        "primary_color": "#2563EB",
        "secondary_color": "#7C3AED",
        "accent_color": "#00F0FF",
        "motif": "calipers",
        "category_label": "KOALITY-ASSURED • EMPIRICAL RESEARCH",
        "chips": ["Task-Eval Suites", "Cost Telemetry Engine", "Tool Efficiency", "Retrieval Benchmarks"],
    },
    "factory": {
        "title": "Agent Factory",
        "tagline": "Product-Agnostic AI Agent QA, Promotion Foundry & Run Spec Orchestration",
        "primary_color": "#EA580C",
        "secondary_color": "#00F0FF",
        "accent_color": "#334155",
        "motif": "foundry",
        "category_label": "KOALITY-ASSURED • AGENT FOUNDRY",
        "chips": ["11-Agent Roster", "Run Spec Contracts", "Automated Promotion", "QA Fleet"],
    },
    "cli": {
        "title": "Harness CLI",
        "tagline": "Cross-Platform High-Performance Control Plane for AI Harnesses & Autonomous Agents",
        "primary_color": "#00ADD8",
        "secondary_color": "#00F0FF",
        "accent_color": "#1E293B",
        "motif": "terminal",
        "category_label": "KOALITY-ASSURED • CONTROL PLANE",
        "chips": ["Sub-15ms Boot", "Worktree Isolation", "TUI Dashboard", "Homebrew & Scoop"],
    },
    "archive": {
        "title": "Agent Factory History Archive",
        "tagline": "Immutable Historical Audit & Execution Ledger Archive for the Agent Factory",
        "primary_color": "#D97706",
        "secondary_color": "#0F172A",
        "accent_color": "#7C3AED",
        "motif": "vault",
        "category_label": "KOALITY-ASSURED • AUDIT ARCHIVE",
        "chips": ["Immutable Audit Trail", "Historical Run Specs", "Promotion Receipts", "Provenance Ledgers"],
    },
    "cloud": {
        "title": "Cloud Router",
        "tagline": "Domain AI Agent Harness for Multi-Cloud Infrastructure, IaC & Least-Privilege IAM",
        "primary_color": "#0284C7",
        "secondary_color": "#6366F1",
        "accent_color": "#10B981",
        "motif": "cloud",
        "category_label": "KOALITY-ASSURED • DOMAIN HARNESS",
        "chips": ["Terraform / OpenTofu", "AWS / Azure / GCP", "Least Privilege IAM", "FinOps Optimization"],
    },
    "wiki": {
        "title": "Core Harness Wiki",
        "tagline": "Universal Zero-Dependency Static Documentation Wiki & Knowledge Base Engine",
        "primary_color": "#00F0FF",
        "secondary_color": "#3B82F6",
        "accent_color": "#10B981",
        "motif": "wiki",
        "category_label": "KOALITY-ASSURED • STATIC WIKI ENGINE",
        "chips": ["Zero-Dependency", "Fluid Widescreen", "Static Engine", "Fast Manifest"],
        "ci_workflow": "deploy.yml",
        "python_version": None,
    },
    "scanner": {
        "title": "Koality PII Scanner",
        "tagline": "Deterministic PII, Credential & Sensitive Data Scanner for Developer Workflows",
        "primary_color": "#EF4444",
        "secondary_color": "#F59E0B",
        "accent_color": "#00F0FF",
        "motif": "scanner",
        "category_label": "KOALITY-ASSURED • SECURITY SCANNER",
        "chips": ["Deterministic Regex", "SARIF 2.1.0", "Secret Scanning", "Agent Pipelines"],
        "ci_workflow": "ci.yml",
        "python_version": ">=3.11",
    },
    "bot": {
        "title": "Backdoors & Breaches Discord Bot",
        "tagline": "Interactive Incident Response Tabletop Simulator & Card Game Bot for Discord",
        "primary_color": "#8B5CF6",
        "secondary_color": "#EC4899",
        "accent_color": "#F59E0B",
        "motif": "cards",
        "category_label": "KOALITY-ASSURED • DISCORD BOT",
        "chips": ["Incident Response", "B&B Tabletop", "571 Cards Indexed", "Dockerized"],
        "ci_workflow": "ci.yml",
        "python_version": "3.10+",
    },
    "cloud-scripts": {
        "title": "Cloud Scripts",
        "tagline": "Multi-Cloud Security, FinOps, Inventory & Automation Tooling across AWS, GCP, Azure & Prisma Cloud",
        "primary_color": "#0284C7",
        "secondary_color": "#10B981",
        "accent_color": "#F59E0B",
        "motif": "cloud",
        "category_label": "KOALITY-ASSURED • MULTI-CLOUD AUTOMATION",
        "chips": ["Multi-Cloud FinOps", "AWS / GCP / Azure", "Prisma Cloud RQL", "Least-Privilege IAM"],
        "ci_workflow": "ci.yml",
        "python_version": "3.9+",
    },
    "logscale": {
        "title": "LogScale Examples & Architecture",
        "tagline": "Enterprise Streaming Parsers, CQL Reference Blueprints & AWS Log Ingestion Pipelines",
        "primary_color": "#F59E0B",
        "secondary_color": "#DC2626",
        "accent_color": "#00F0FF",
        "motif": "telemetry",
        "category_label": "KOALITY-ASSURED • LOGSCALE BLUEPRINTS",
        "chips": ["CrowdStrike CQL", "Falcon LogScale", "Streaming Parsers", "AWS Ingestion"],
        "ci_workflow": "ci.yml",
        "python_version": None,
    },
    "pulumi": {
        "title": "Pulumi Infrastructure Examples",
        "tagline": "Production-Grade Multi-Cloud IaC Patterns, Policy-as-Code & Matrixed Automations",
        "primary_color": "#8B5CF6",
        "secondary_color": "#00F0FF",
        "accent_color": "#10B981",
        "motif": "layers",
        "category_label": "KOALITY-ASSURED • PULUMI ARCHITECTURE",
        "chips": ["Multi-Cloud IaC", "Pulumi YAML/Python", "CrossGuard Policies", "Serverless Stacks"],
        "ci_workflow": "ci.yml",
        "python_version": None,
    },
    "whitepapers": {
        "title": "Koality-Assured Whitepapers",
        "tagline": "Domain-Organized Technical White Paper Series with Sources, Methods & Evidence Limits",
        "primary_color": "#3B82F6",
        "secondary_color": "#6366F1",
        "accent_color": "#00F0FF",
        "motif": "manuscript",
        "category_label": "KOALITY-ASSURED • TECHNICAL RESEARCH",
        "chips": ["Domain-Organized", "Evidence Ledgers", "Primary Sources", "Reproducibility"],
        "ci_workflow": "ci.yml",
        "python_version": None,
    },
    "portfolio": {
        "title": "Personal Portfolio",
        "tagline": "Production Resume, Engineering Portfolio & Live Interactive Showcase",
        "primary_color": "#00F0FF",
        "secondary_color": "#7C3AED",
        "accent_color": "#10B981",
        "motif": "briefcase",
        "category_label": "KOALITY-ASSURED • PERSONAL PORTFOLIO",
        "chips": ["Cloudflare Pages", "Vite / React", "Live Demonstrations", "Responsive UI"],
        "ci_workflow": "ci.yml",
        "python_version": None,
    },
}


def _title_from_name(name: str) -> str:
    """Derive Title Case representation from kebab-case repo name."""
    words = [w.capitalize() for w in name.replace("_", "-").split("-") if w]
    titled = " ".join(words)
    replacements = {
        "Ai": "AI",
        "Mcp": "MCP",
        "Cli": "CLI",
        "Ui Ux": "UI/UX",
        "Iac": "IaC",
        "Wcag": "WCAG",
        "Api": "API",
    }
    for old, new in replacements.items():
        titled = re.sub(rf"\b{old}\b", new, titled)
    return titled


def get_domain_spec(
    name: str,
    domain: str = "none",
    org: str = DEFAULT_ORG,
    **overrides: Any,
) -> DomainBrandingSpec:
    """Build a resolved DomainBrandingSpec combining presets and explicit options."""
    preset_key = domain
    if preset_key not in DOMAIN_PRESETS:
        # Check if name maps directly to a preset (longest match first)
        for key in sorted(DOMAIN_PRESETS.keys(), key=len, reverse=True):
            if key in name:
                preset_key = key
                break

    base = DOMAIN_PRESETS.get(preset_key, {})
    resolved_domain = domain if domain != "none" else (preset_key if preset_key in DOMAIN_PRESETS else "none")
    title = overrides.get("title") or base.get("title") or _title_from_name(name)
    tagline = (
        overrides.get("tagline")
        or base.get("tagline")
        or f"Domain AI Agent Harness and Tooling Engine for {title}"
    )
    chips = overrides.get("chips") or base.get("chips") or [
        "Domain Routing",
        "Worktree Isolation",
        "5-Tier Context",
        "Automated CI",
    ]

    py_version = (
        overrides.get("python_version")
        or base.get("python_version", "3.11+")
    )

    spec = DomainBrandingSpec(
        name=name,
        domain=resolved_domain,
        title=title,
        tagline=tagline,
        org=org,
        primary_color=overrides.get("primary_color") or base.get("primary_color", "#00F0FF"),
        secondary_color=overrides.get("secondary_color") or base.get("secondary_color", "#7C3AED"),
        accent_color=overrides.get("accent_color") or base.get("accent_color", "#10B981"),
        motif=overrides.get("motif") or base.get("motif", "compass"),
        category_label=overrides.get("category_label")
        or base.get("category_label", "KOALITY-ASSURED • DOMAIN HARNESS"),
        chips=chips,
        ci_workflow=overrides.get("ci_workflow") or base.get("ci_workflow", "ci.yml"),
        python_version=py_version,
        license_type=overrides.get("license_type") or base.get("license_type", "MIT"),
        visibility=overrides.get("visibility") or base.get("visibility", "public"),
    )
    return spec


# -----------------------------------------------------------------------------
# Vector SVG Generation
# -----------------------------------------------------------------------------


def _render_motif_paths(motif: str, p: str, s: str, a: str) -> str:
    """Generate thematic geometric SVG paths for a given motif."""
    if motif == "scales":
        # Judicial scales of justice
        return f"""
    <!-- Scales of Justice Motif -->
    <line x1="256" y1="160" x2="256" y2="350" stroke="{p}" stroke-width="6" stroke-linecap="round" />
    <line x1="170" y1="200" x2="342" y2="200" stroke="{s}" stroke-width="5" stroke-linecap="round" />
    <!-- Center Pivot Fulcrum -->
    <polygon points="256,150 244,170 268,170" fill="{a}" />
    <!-- Left Scale Pan -->
    <line x1="170" y1="200" x2="140" y2="270" stroke="{s}" stroke-width="2" />
    <line x1="170" y1="200" x2="200" y2="270" stroke="{s}" stroke-width="2" />
    <path d="M 130 270 Q 170 295 210 270 Z" fill="{p}" opacity="0.85" />
    <!-- Right Scale Pan -->
    <line x1="342" y1="200" x2="312" y2="270" stroke="{s}" stroke-width="2" />
    <line x1="342" y1="200" x2="372" y2="270" stroke="{s}" stroke-width="2" />
    <path d="M 302 270 Q 342 295 382 270 Z" fill="{a}" opacity="0.85" />
    <!-- Base Pedestal -->
    <rect x="226" y="345" width="60" height="15" rx="4" fill="{p}" />
    <rect x="206" y="358" width="100" height="12" rx="4" fill="{s}" />
        """
    elif motif == "artboard":
        # Design artboard with bezier pen and contrast iris
        return f"""
    <!-- Artboard & Bezier Motif -->
    <rect x="166" y="150" width="180" height="180" rx="16" fill="none" stroke="{p}" stroke-width="4" stroke-dasharray="12 6" />
    <circle cx="256" cy="240" r="54" fill="none" stroke="{s}" stroke-width="5" />
    <circle cx="256" cy="240" r="24" fill="{a}" opacity="0.8" />
    <!-- Bezier Curve & Anchor Nodes -->
    <path d="M 140 310 C 190 170 322 310 372 170" fill="none" stroke="{a}" stroke-width="4" />
    <circle cx="140" cy="310" r="6" fill="{p}" />
    <circle cx="372" cy="170" r="6" fill="{s}" />
    <circle cx="256" cy="240" r="6" fill="#FFFFFF" />
        """
    elif motif == "candlestick":
        # Financial candlestick and MPT frontier
        return f"""
    <!-- Candlestick Telemetry Motif -->
    <!-- Candle 1: Bullish -->
    <line x1="186" y1="180" x2="186" y2="330" stroke="{s}" stroke-width="3" />
    <rect x="174" y="210" width="24" height="80" rx="4" fill="{s}" />
    <!-- Candle 2: Bullish Peak -->
    <line x1="256" y1="140" x2="256" y2="340" stroke="{p}" stroke-width="4" />
    <rect x="242" y="170" width="28" height="110" rx="4" fill="{p}" />
    <!-- Candle 3: High Momentum -->
    <line x1="326" y1="160" x2="326" y2="320" stroke="{a}" stroke-width="3" />
    <rect x="314" y="190" width="24" height="70" rx="4" fill="{a}" />
    <!-- Trend Polynomial Line -->
    <path d="M 150 310 Q 256 120 362 200" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" stroke-dasharray="6 4" />
        """
    elif motif == "gamepad":
        # Retro-arcade D-pad and gem mesh
        return f"""
    <!-- Gamepad / Arcade Motif -->
    <rect x="156" y="170" width="200" height="140" rx="36" fill="none" stroke="{p}" stroke-width="5" />
    <!-- D-Pad Plus -->
    <path d="M 200 216 H 216 V 200 H 228 V 216 H 244 V 228 H 228 V 244 H 216 V 228 H 200 Z" fill="{s}" />
    <!-- Action Buttons -->
    <circle cx="286" cy="216" r="8" fill="{a}" />
    <circle cx="308" cy="228" r="8" fill="{p}" />
    <circle cx="286" cy="240" r="8" fill="{s}" />
    <circle cx="264" cy="228" r="8" fill="#FFFFFF" />
        """
    elif motif == "palette":
        # Artist palette and creative synthesis nodes
        return f"""
    <!-- Artist Palette Motif -->
    <path d="M 256 150 C 180 150 140 200 140 260 C 140 320 190 350 240 350 C 270 350 290 330 320 330 C 350 330 372 300 372 260 C 372 190 320 150 256 150 Z" 
          fill="none" stroke="{p}" stroke-width="5" />
    <circle cx="200" cy="220" r="14" fill="{s}" />
    <circle cx="246" cy="190" r="14" fill="{a}" />
    <circle cx="300" cy="210" r="14" fill="{p}" />
    <circle cx="330" cy="260" r="14" fill="#FFFFFF" />
    <circle cx="260" cy="300" r="18" fill="#0B0F19" stroke="{p}" stroke-width="3" />
        """
    elif motif == "warehouse":
        # Inventory warehouse rack & barcode
        return f"""
    <!-- Warehouse Rack & Barcode Motif -->
    <rect x="160" y="160" width="192" height="170" rx="10" fill="none" stroke="{p}" stroke-width="4" />
    <line x1="160" y1="216" x2="352" y2="216" stroke="{s}" stroke-width="3" />
    <line x1="160" y1="272" x2="352" y2="272" stroke="{s}" stroke-width="3" />
    <!-- Stored Packages -->
    <rect x="180" y="174" width="34" height="34" rx="4" fill="{p}" opacity="0.8" />
    <rect x="230" y="174" width="50" height="34" rx="4" fill="{a}" opacity="0.8" />
    <rect x="180" y="230" width="60" height="34" rx="4" fill="{s}" opacity="0.8" />
    <rect x="260" y="230" width="40" height="34" rx="4" fill="{p}" opacity="0.8" />
    <!-- Barcode Strip -->
    <g transform="translate(180, 290)" fill="{a}">
      <rect x="0" y="0" width="4" height="24" /><rect x="8" y="0" width="8" height="24" />
      <rect x="20" y="0" width="4" height="24" /><rect x="28" y="0" width="12" height="24" />
      <rect x="46" y="0" width="6" height="24" /><rect x="58" y="0" width="10" height="24" />
      <rect x="74" y="0" width="4" height="24" /><rect x="84" y="0" width="8" height="24" />
      <rect x="98" y="0" width="14" height="24" /><rect x="118" y="0" width="6" height="24" />
      <rect x="130" y="0" width="8" height="24" /><rect x="144" y="0" width="4" height="24" />
    </g>
        """
    elif motif == "socket":
        # MCP socket and neural plug
        return f"""
    <!-- Model Context Protocol Socket Motif -->
    <circle cx="256" cy="256" r="90" fill="none" stroke="{p}" stroke-width="5" stroke-dasharray="16 8" />
    <circle cx="256" cy="256" r="60" fill="#0B0F19" stroke="{s}" stroke-width="4" />
    <!-- Socket Pins -->
    <circle cx="226" cy="236" r="10" fill="{p}" />
    <circle cx="286" cy="236" r="10" fill="{p}" />
    <circle cx="226" cy="276" r="10" fill="{a}" />
    <circle cx="286" cy="276" r="10" fill="{a}" />
    <circle cx="256" cy="256" r="6" fill="#FFFFFF" />
    <!-- Neural Bus Rays -->
    <line x1="166" y1="256" x2="130" y2="256" stroke="{s}" stroke-width="4" stroke-linecap="round" />
    <line x1="346" y1="256" x2="382" y2="256" stroke="{s}" stroke-width="4" stroke-linecap="round" />
        """
    elif motif == "gear":
        # Harness gear and orbital ring
        return f"""
    <!-- Harness Engine Gear Motif -->
    <circle cx="256" cy="256" r="86" fill="none" stroke="{p}" stroke-width="6" stroke-dasharray="24 12" />
    <circle cx="256" cy="256" r="54" fill="#0B0F19" stroke="{s}" stroke-width="4" />
    <polygon points="256,190 270,240 320,240 280,270 295,320 256,290 217,320 232,270 192,240 242,240" fill="{a}" opacity="0.85" />
    <circle cx="256" cy="256" r="14" fill="#FFFFFF" />
        """
    elif motif == "shield":
        # Cybersecurity armor shield and padlock
        return f"""
    <!-- Armor Shield & Lock Motif -->
    <path d="M 256 140 L 356 185 V 265 C 356 325 256 370 256 370 C 256 370 156 325 156 265 V 185 Z" 
          fill="none" stroke="{p}" stroke-width="6" />
    <!-- Inner Padlock -->
    <path d="M 236 230 V 210 C 236 195 276 195 276 210 V 230" fill="none" stroke="{s}" stroke-width="5" />
    <rect x="220" y="230" width="72" height="54" rx="8" fill="{a}" />
    <circle cx="256" cy="252" r="6" fill="#0B0F19" />
    <line x1="256" y1="256" x2="256" y2="268" stroke="#0B0F19" stroke-width="3" />
        """
    elif motif == "terminal":
        # CLI terminal chevron and speed bolt
        return f"""
    <!-- Terminal Chevron Motif -->
    <rect x="150" y="160" width="212" height="160" rx="16" fill="#0B0F19" stroke="{p}" stroke-width="5" />
    <!-- Header Window Dots -->
    <circle cx="175" cy="182" r="5" fill="#EF4444" />
    <circle cx="195" cy="182" r="5" fill="#F59E0B" />
    <circle cx="215" cy="182" r="5" fill="#10B981" />
    <!-- Chevron >_ -->
    <path d="M 180 220 L 210 245 L 180 270" fill="none" stroke="{s}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
    <line x1="225" y1="270" x2="260" y2="270" stroke="{a}" stroke-width="6" stroke-linecap="round" />
        """
    elif motif == "vault":
        # Immutable ledger vault seal
        return f"""
    <!-- Vault Archive Motif -->
    <circle cx="256" cy="256" r="90" fill="none" stroke="{p}" stroke-width="6" />
    <circle cx="256" cy="256" r="70" fill="none" stroke="{s}" stroke-width="4" stroke-dasharray="10 6" />
    <!-- Vault Handle Cross -->
    <line x1="216" y1="256" x2="296" y2="256" stroke="{a}" stroke-width="6" stroke-linecap="round" />
    <line x1="256" y1="216" x2="256" y2="296" stroke="{a}" stroke-width="6" stroke-linecap="round" />
    <circle cx="256" cy="256" r="18" fill="{p}" />
    <circle cx="256" cy="256" r="8" fill="#FFFFFF" />
        """
    elif motif == "cloud":
        # Cloud infrastructure cluster
        return f"""
    <!-- Cloud Cluster Motif -->
    <path d="M 200 280 H 320 C 350 280 370 260 370 230 C 370 205 350 185 325 185 C 320 155 295 135 265 135 C 235 135 210 155 205 185 C 180 190 160 210 160 235 C 160 260 180 280 200 280 Z"
          fill="none" stroke="{p}" stroke-width="5" />
    <!-- Infrastructure Nodes -->
    <rect x="200" y="220" width="30" height="20" rx="3" fill="{s}" />
    <rect x="245" y="220" width="30" height="20" rx="3" fill="{a}" />
    <rect x="290" y="220" width="30" height="20" rx="3" fill="{p}" />
    <line x1="256" y1="280" x2="256" y2="330" stroke="{s}" stroke-width="4" stroke-dasharray="6 4" />
    <circle cx="256" cy="336" r="8" fill="{a}" />
        """
    elif motif == "wiki":
        # Interactive Knowledge Base & Documentation Wiki
        return f"""
    <!-- Interactive Knowledge Wiki Motif -->
    <path d="M 256 180 C 220 160 170 160 140 175 V 335 C 170 320 220 320 256 340 C 292 320 342 320 372 335 V 175 C 342 160 292 160 256 180 Z" 
          fill="none" stroke="{p}" stroke-width="5" stroke-linejoin="round" />
    <line x1="256" y1="180" x2="256" y2="340" stroke="{s}" stroke-width="4" />
    <!-- Knowledge Nodes on Left Page -->
    <circle cx="180" cy="220" r="6" fill="{s}" />
    <circle cx="220" cy="250" r="6" fill="{a}" />
    <circle cx="180" cy="280" r="6" fill="{p}" />
    <line x1="180" y1="220" x2="220" y2="250" stroke="{s}" stroke-width="2" />
    <line x1="220" y1="250" x2="180" y2="280" stroke="{a}" stroke-width="2" />
    <!-- Article Text Lines on Right Page -->
    <line x1="280" y1="215" x2="345" y2="215" stroke="{s}" stroke-width="3" stroke-linecap="round" />
    <line x1="280" y1="240" x2="335" y2="240" stroke="{a}" stroke-width="3" stroke-linecap="round" />
    <line x1="280" y1="265" x2="350" y2="265" stroke="{p}" stroke-width="3" stroke-linecap="round" />
    <line x1="280" y1="290" x2="320" y2="290" stroke="{s}" stroke-width="3" stroke-linecap="round" />
    <!-- Top Knowledge Nexus Beacon -->
    <polygon points="256,140 264,155 256,170 248,155" fill="{a}" />
        """
    elif motif == "scanner":
        # Cyber Security & PII Scanner
        return f"""
    <!-- Scanner Reticle & Radar Sweep Motif -->
    <circle cx="256" cy="256" r="95" fill="none" stroke="{p}" stroke-width="4" stroke-dasharray="14 8" />
    <circle cx="256" cy="256" r="65" fill="none" stroke="{s}" stroke-width="3" />
    <circle cx="256" cy="256" r="35" fill="none" stroke="{a}" stroke-width="2" stroke-dasharray="6 4" />
    <!-- Reticle Crosshairs -->
    <line x1="256" y1="140" x2="256" y2="200" stroke="{p}" stroke-width="3" stroke-linecap="round" />
    <line x1="256" y1="312" x2="256" y2="372" stroke="{p}" stroke-width="3" stroke-linecap="round" />
    <line x1="140" y1="256" x2="200" y2="256" stroke="{p}" stroke-width="3" stroke-linecap="round" />
    <line x1="312" y1="256" x2="372" y2="256" stroke="{p}" stroke-width="3" stroke-linecap="round" />
    <!-- Radar Sweep Wedge -->
    <path d="M 256 256 L 330 190 A 95 95 0 0 1 351 256 Z" fill="{s}" opacity="0.35" />
    <line x1="256" y1="256" x2="330" y2="190" stroke="{a}" stroke-width="3" />
    <!-- Target Detection Blip -->
    <circle cx="305" cy="215" r="7" fill="{a}" />
    <circle cx="305" cy="215" r="14" fill="none" stroke="{a}" stroke-width="2" opacity="0.6" />
    <circle cx="256" cy="256" r="6" fill="#FFFFFF" />
        """
    elif motif == "cards":
        # Backdoors & Breaches Tabletop Cards & D20 Die
        return f"""
    <!-- Incident Response Cards & D20 Motif -->
    <!-- Card 1: Angled Left (Threat Vector) -->
    <rect x="160" y="165" width="90" height="135" rx="8" transform="rotate(-15 205 232)" 
          fill="#0B0F19" stroke="{s}" stroke-width="4" />
    <!-- Card 2: Angled Right (Procedure Defense) -->
    <rect x="262" y="165" width="90" height="135" rx="8" transform="rotate(15 307 232)" 
          fill="#0B0F19" stroke="{p}" stroke-width="4" />
    <!-- Card 2 Shield Emblem -->
    <path d="M 307 195 L 325 205 V 225 C 325 240 307 252 307 252 C 307 252 289 240 289 225 V 205 Z" 
          fill="{p}" opacity="0.6" />
    <!-- Center D20 Die Facet -->
    <polygon points="256,200 294,222 294,268 256,290 218,268 218,222" fill="#0F172A" stroke="{a}" stroke-width="4" />
    <!-- D20 Internal Triangle -->
    <polygon points="256,215 282,260 230,260" fill="none" stroke="{p}" stroke-width="2.5" />
    <line x1="256" y1="200" x2="256" y2="215" stroke="{a}" stroke-width="2" />
    <line x1="294" y1="222" x2="282" y2="260" stroke="{a}" stroke-width="2" />
    <line x1="218" y1="222" x2="230" y2="260" stroke="{a}" stroke-width="2" />
    <circle cx="256" cy="245" r="5" fill="#FFFFFF" />
        """
    elif motif == "telemetry":
        # Falcon LogScale Streaming Telemetry & Signal Waves
        return f"""
    <!-- Streaming Log Telemetry & Signal Wave Motif -->
    <rect x="150" y="160" width="212" height="170" rx="14" fill="#0B0F19" stroke="{p}" stroke-width="4" />
    <!-- Stream Pulse Wave -->
    <path d="M 165 245 L 205 245 L 220 185 L 238 295 L 256 220 L 272 265 L 288 205 L 304 245 L 345 245" 
          fill="none" stroke="{a}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
    <!-- Parsing Marker Indices -->
    <circle cx="220" cy="185" r="5" fill="{p}" />
    <circle cx="238" cy="295" r="5" fill="{s}" />
    <circle cx="288" cy="205" r="5" fill="{p}" />
    <!-- Data Ingestion Status Bars -->
    <rect x="175" y="178" width="18" height="6" rx="2" fill="{s}" />
    <rect x="200" y="178" width="28" height="6" rx="2" fill="{p}" />
    <rect x="235" y="178" width="12" height="6" rx="2" fill="{a}" />
    <!-- Stream Vector Flow Lines -->
    <line x1="165" y1="305" x2="345" y2="305" stroke="{s}" stroke-width="2" stroke-dasharray="8 6" />
        """
    elif motif == "layers":
        # Pulumi Multi-Tier Infrastructure As Code Layers
        return f"""
    <!-- Infrastructure as Code Stacked Layers Motif -->
    <!-- Top Layer: App & Policy Layer -->
    <polygon points="256,155 345,195 256,235 167,195" fill="#0F172A" stroke="{a}" stroke-width="4" />
    <polygon points="256,165 325,195 256,225 187,195" fill="none" stroke="{a}" stroke-width="1.5" opacity="0.6" />
    <!-- Middle Layer: Compute & Security Layer -->
    <polygon points="256,210 345,250 256,290 167,250" fill="#0F172A" stroke="{p}" stroke-width="4" />
    <!-- Bottom Layer: Base Network & Cloud Foundation -->
    <polygon points="256,265 345,305 256,345 167,305" fill="#0F172A" stroke="{s}" stroke-width="4" />
    <!-- Vertical Interconnect Data Buses -->
    <line x1="167" y1="195" x2="167" y2="305" stroke="{p}" stroke-width="3" stroke-dasharray="4 4" />
    <line x1="345" y1="195" x2="345" y2="305" stroke="{p}" stroke-width="3" stroke-dasharray="4 4" />
    <line x1="256" y1="235" x2="256" y2="345" stroke="{a}" stroke-width="3" />
    <circle cx="256" cy="195" r="7" fill="{a}" />
        """
    elif motif == "manuscript":
        # Technical Whitepaper Series & Evidence Ledger
        return f"""
    <!-- Technical Whitepaper Manuscript Motif -->
    <!-- Back Page Shadow -->
    <rect x="180" y="160" width="160" height="190" rx="8" fill="#0F172A" stroke="{s}" stroke-width="3" opacity="0.6" />
    <!-- Main Manuscript Leaf -->
    <rect x="165" y="145" width="160" height="190" rx="8" fill="#0B0F19" stroke="{p}" stroke-width="4" />
    <!-- Bookmark Ribbon -->
    <polygon points="280,145 305,145 305,200 292.5,188 280,200" fill="{a}" />
    <!-- Document Content Lines -->
    <line x1="190" y1="180" x2="260" y2="180" stroke="{p}" stroke-width="4" stroke-linecap="round" />
    <line x1="190" y1="205" x2="255" y2="205" stroke="{s}" stroke-width="3" stroke-linecap="round" />
    <line x1="190" y1="225" x2="300" y2="225" stroke="{s}" stroke-width="3" stroke-linecap="round" />
    <line x1="190" y1="245" x2="295" y2="245" stroke="{s}" stroke-width="3" stroke-linecap="round" />
    <line x1="190" y1="265" x2="275" y2="265" stroke="{s}" stroke-width="3" stroke-linecap="round" />
    <!-- Evidence Verification Crest -->
    <circle cx="245" cy="300" r="16" fill="{s}" opacity="0.8" />
    <path d="M 238 300 L 243 305 L 253 294" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
        """
    elif motif == "briefcase":
        # Professional Portfolio & Showcase
        return f"""
    <!-- Personal Portfolio Briefcase Motif -->
    <rect x="160" y="180" width="192" height="145" rx="14" fill="#0B0F19" stroke="{p}" stroke-width="5" />
    <!-- Handle -->
    <path d="M 216 180 V 155 C 216 148 226 142 236 142 H 276 C 286 142 296 148 296 155 V 180" fill="none" stroke="{s}" stroke-width="5" />
    <!-- Center Dividing Band & Latch -->
    <line x1="160" y1="240" x2="352" y2="240" stroke="{s}" stroke-width="3" />
    <rect x="238" y="230" width="36" height="22" rx="4" fill="{a}" />
    <!-- Code Bracket Accents inside Case -->
    <path d="M 200 270 L 188 282 L 200 294" fill="none" stroke="{p}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M 312 270 L 324 282 L 312 294" fill="none" stroke="{p}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
    <line x1="246" y1="282" x2="266" y2="282" stroke="{s}" stroke-width="3" stroke-linecap="round" />
        """
    else:
        # Default: Cybernetic routing compass & hexagram nexus
        return f"""
    <!-- Routing Nexus Hexagram -->
    <polygon points="256,150 340,198 340,294 256,342 172,294 172,198" 
             fill="none" stroke="{p}" stroke-width="5" stroke-linejoin="round" />
    <polygon points="256,170 320,285 192,285" fill="none" stroke="{s}" stroke-width="3" opacity="0.8" />
    <polygon points="256,322 192,207 320,207" fill="none" stroke="{a}" stroke-width="3" opacity="0.8" />
    <circle cx="256" cy="256" r="32" fill="#0B0F19" stroke="{p}" stroke-width="3" />
    <circle cx="256" cy="256" r="10" fill="#FFFFFF" />
        """


def generate_vector_logo(spec: DomainBrandingSpec) -> str:
    """Synthesize a production-ready, high-contrast 512x512 vector XML SVG logo."""
    p = spec.primary_color
    s = spec.secondary_color
    a = spec.accent_color
    motif_code = _render_motif_paths(spec.motif, p, s, a)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#080C14" />
      <stop offset="50%" stop-color="#0F172A" />
      <stop offset="100%" stop-color="#080C14" />
    </linearGradient>
    <linearGradient id="primary-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{p}" />
      <stop offset="50%" stop-color="{s}" />
      <stop offset="100%" stop-color="{a}" />
    </linearGradient>
    <linearGradient id="accent-cyan" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{p}" />
      <stop offset="100%" stop-color="{s}" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Background Shield Canvas -->
  <rect width="512" height="512" rx="112" fill="url(#bg-grad)" stroke="#1E293B" stroke-width="4" />

  <!-- Background Geometric Orbit Tracks -->
  <g opacity="0.2" stroke="#475569" stroke-width="1.5">
    <circle cx="256" cy="256" r="210" fill="none" stroke-dasharray="6 8" />
    <circle cx="256" cy="256" r="160" fill="none" />
    <circle cx="256" cy="256" r="110" fill="none" stroke-dasharray="4 6" />
    <line x1="256" y1="46" x2="256" y2="466" />
    <line x1="46" y1="256" x2="466" y2="256" />
  </g>

  <!-- Outer Orbit Nodes -->
  <circle cx="256" cy="256" r="185" fill="none" stroke="url(#accent-cyan)" stroke-width="3" opacity="0.5" stroke-dasharray="40 20 80 20" />
  <g fill="#0B0F19" stroke-width="3">
    <circle cx="256" cy="71" r="14" stroke="{p}" />
    <circle cx="256" cy="71" r="5" fill="{p}" />
    <circle cx="441" cy="256" r="14" stroke="{s}" />
    <circle cx="441" cy="256" r="5" fill="{s}" />
    <circle cx="256" cy="441" r="14" stroke="{a}" />
    <circle cx="256" cy="441" r="5" fill="{a}" />
    <circle cx="71" cy="256" r="14" stroke="{p}" />
    <circle cx="71" cy="256" r="5" fill="{p}" />
  </g>

  <!-- Central Emblem Geometry -->
  <g filter="url(#glow)">
{motif_code}
  </g>

  <!-- Bus Trajectory Pulses -->
  <circle cx="176" cy="134" r="4" fill="{p}" filter="url(#glow)" />
  <circle cx="336" cy="134" r="4" fill="{s}" filter="url(#glow)" />
  <circle cx="336" cy="378" r="4" fill="{a}" filter="url(#glow)" />
  <circle cx="176" cy="378" r="4" fill="{p}" filter="url(#glow)" />
</svg>
"""
    return svg.strip() + "\n"


def _xml_escape(text: str) -> str:
    """Escape XML special characters for safe SVG text embedding."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def generate_vector_banner(spec: DomainBrandingSpec) -> str:
    """Synthesize a production-ready, high-contrast 1280x400 vector XML SVG hero banner."""
    p = spec.primary_color
    s = spec.secondary_color
    a = spec.accent_color
    motif_code = _render_motif_paths(spec.motif, p, s, a)

    # Clean, uppercase, and escape title for typography
    disp_title = _xml_escape(spec.title.upper())
    escaped_category = _xml_escape(spec.category_label)
    escaped_tagline = _xml_escape(spec.tagline)

    # Build chips XML
    chips_xml = []
    x_offset = 0
    chip_colors = [p, s, a, "#38BDF8"]
    for i, chip_text in enumerate(spec.chips[:4]):
        col = chip_colors[i % len(chip_colors)]
        w = max(len(chip_text) * 9 + 48, 140)
        esc_chip = _xml_escape(chip_text)
        chips_xml.append(f"""      <!-- Chip {i+1}: {esc_chip} -->
      <g transform="translate({x_offset}, 0)">
        <rect x="0" y="0" width="{w}" height="38" rx="8" fill="#111827" stroke="{col}" stroke-width="1.5" />
        <circle cx="18" cy="19" r="4" fill="{col}" />
        <text x="32" y="24" fill="#E2E8F0" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13" font-weight="600">{esc_chip}</text>
      </g>""")
        x_offset += w + 14

    rendered_chips = "\n".join(chips_xml)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 400" width="100%" height="100%">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#080C14" />
      <stop offset="40%" stop-color="#0F172A" />
      <stop offset="100%" stop-color="#080C14" />
    </linearGradient>
    <linearGradient id="accent-cyan" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{p}" />
      <stop offset="100%" stop-color="{s}" />
    </linearGradient>
    <linearGradient id="core-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{p}" />
      <stop offset="50%" stop-color="{s}" />
      <stop offset="100%" stop-color="{a}" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Background Backdrop -->
  <rect width="1280" height="400" fill="url(#bg)" />

  <!-- Tech Matrix Blueprint Grid -->
  <g opacity="0.12" stroke="{p}" stroke-width="1">
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" />
    </pattern>
    <rect width="1280" height="400" fill="url(#grid)" />
  </g>

  <!-- High-Tech Data Stream Vectors -->
  <g opacity="0.25">
    <path d="M -50 100 Q 300 60 640 180 T 1330 220" fill="none" stroke="{p}" stroke-width="2" />
    <path d="M -50 280 Q 400 340 780 240 T 1330 140" fill="none" stroke="{s}" stroke-width="2" />
  </g>

  <!-- Left: Hero Graphic Emblematics -->
  <g transform="translate(180, 200)">
    <!-- Concentric Orbit Rings -->
    <circle cx="0" cy="0" r="140" fill="none" stroke="#334155" stroke-width="1.5" stroke-dasharray="6 8" opacity="0.4" />
    <circle cx="0" cy="0" r="110" fill="none" stroke="{p}" stroke-width="2" stroke-dasharray="30 15 60 15" opacity="0.7" />
    <circle cx="0" cy="0" r="80" fill="none" stroke="{s}" stroke-width="2" opacity="0.6" />
    
    <!-- Outer Spoke Nodes -->
    <circle cx="0" cy="-140" r="10" fill="#0B0F19" stroke="{p}" stroke-width="3" />
    <circle cx="140" cy="0" r="10" fill="#0B0F19" stroke="{s}" stroke-width="3" />
    <circle cx="0" cy="140" r="10" fill="#0B0F19" stroke="{a}" stroke-width="3" />
    <circle cx="-140" cy="0" r="10" fill="#0B0F19" stroke="{p}" stroke-width="3" />

    <!-- Central Iconography Transformed -->
    <g transform="translate(-256, -256)">
{motif_code}
    </g>
  </g>

  <!-- Right: Typography & Capability Badges -->
  <g transform="translate(420, 100)">
    <!-- Overline Category Capsule -->
    <rect x="0" y="0" width="310" height="26" rx="13" fill="#1E293B" stroke="#334155" stroke-width="1" />
    <circle cx="14" cy="13" r="5" fill="{p}" filter="url(#glow)" />
    <text x="28" y="17" fill="#94A3B8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="11" font-weight="700" letter-spacing="1.5">{escaped_category}</text>

    <!-- Project Title -->
    <text x="0" y="72" fill="#FFFFFF" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="48" font-weight="900" letter-spacing="1">{disp_title}</text>

    <!-- Subtitle -->
    <text x="0" y="110" fill="#94A3B8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="17" font-weight="400">{escaped_tagline}</text>

    <!-- Capability Chips -->
    <g transform="translate(0, 150)">
{rendered_chips}
    </g>
  </g>
</svg>
"""
    return svg.strip() + "\n"


def validate_svg_xml(content: str) -> bool:
    """Empirically parse SVG content to ensure valid XML syntax."""
    try:
        ET.fromstring(content)  # nosec B314 - purely local SVG generation
        return True
    except ET.ParseError:
        return False


# -----------------------------------------------------------------------------
# Live Badges & Markdown Hero Generation
# -----------------------------------------------------------------------------


def generate_live_badges(spec: DomainBrandingSpec) -> list[str]:
    """Generate Markdown strings for auto-updating live Shields.io and GitHub badges."""
    badges = []

    # CI Workflow Badge
    if spec.ci_workflow:
        ci_url = f"https://github.com/{spec.org}/{spec.name}/actions/workflows/{spec.ci_workflow}"
        badges.append(f"[![CI]({ci_url}/badge.svg)]({ci_url})")

    # License Badge
    if spec.license_type.upper() == "MIT":
        badges.append("[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)")
    else:
        badges.append(
            f"[![License: {spec.license_type}](https://img.shields.io/badge/License-{spec.license_type}-red.svg)](LICENSE)"
        )

    # Language / Python Runtime Badge (only when python_version is set)
    if spec.python_version:
        badges.append(
            f"[![Python {spec.python_version}](https://img.shields.io/badge/python-{spec.python_version}-blue.svg)](pyproject.toml)"
        )

    # Domain Classification Badge
    clean_domain = spec.domain if spec.domain != "none" else "ecosystem"
    badges.append(
        f"[![Domain: {clean_domain.title()}](https://img.shields.io/badge/domain-{clean_domain}-blueviolet.svg)]()"
    )

    # Conventional Commits Badge
    badges.append(
        "[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)"
    )

    return badges


def generate_readme_hero(spec: DomainBrandingSpec) -> str:
    """Generate the centered visual hero markdown block with banner, logo, tagline, and badges."""
    badges = generate_live_badges(spec)
    badge_str = "\n".join(badges)

    hero = f"""<div align="center">

![{spec.title} Banner](assets/{spec.name}-banner.svg)

# {spec.title}

<p align="center">
  <img src="assets/{spec.name}-logo.svg" alt="{spec.title} Logo" width="128" height="128" />
</p>

**{spec.tagline}**

{badge_str}

</div>

---
"""
    return hero


# -----------------------------------------------------------------------------
# Hardening Helpers
# -----------------------------------------------------------------------------


def harden_pyproject_toml_content(content: str) -> str:
    """Harden pyproject.toml against setuptools flat-layout multiple-package auto-discovery crashes.

    When assets/ or other non-package folders exist in the repository root alongside code,
    setuptools >= 61 raises:
      `error: Multiple top-level packages discovered in a flat-layout: ['assets', '...']`
    This function configures `[tool.setuptools] packages = []` or explicit exclusions to
    prevent package discovery from failing pip install.
    """
    if "[tool.setuptools]" in content:
        # Check if packages or find is already specified
        if "packages" in content or "find" in content:
            return content
        # Append packages = [] under [tool.setuptools]
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if line.strip() == "[tool.setuptools]":
                new_lines.append("packages = []")
        return "\n".join(new_lines) + "\n"

    # Append complete [tool.setuptools] block
    hardening_block = """
[tool.setuptools]
packages = []
"""
    return content.rstrip() + "\n" + hardening_block.lstrip()


def harden_repo_directory(repo_dir: Path) -> dict[str, Any]:
    """Apply filesystem hardening: pyproject.toml setuptools config and MIT license."""
    report: dict[str, Any] = {"hardened": [], "created": []}

    pyproject_path = repo_dir / "pyproject.toml"
    if pyproject_path.exists():
        original = pyproject_path.read_text(encoding="utf-8")
        hardened = harden_pyproject_toml_content(original)
        if hardened != original:
            pyproject_path.write_text(hardened, encoding="utf-8")
            report["hardened"].append("pyproject.toml")

    license_path = repo_dir / "LICENSE"
    if not license_path.exists():
        license_path.write_text(MIT_LICENSE_TEMPLATE, encoding="utf-8")
        report["created"].append("LICENSE")

    return report


# -----------------------------------------------------------------------------
# End-to-End Beautification Orchestration
# -----------------------------------------------------------------------------


def beautify_repository(
    repo_dir: Path,
    spec: DomainBrandingSpec | None = None,
    *,
    domain: str = "none",
    org: str = DEFAULT_ORG,
    dry_run: bool = False,
    update_readme: bool = True,
) -> dict[str, Any]:
    """Execute complete repository beautification, branding, and hardening."""
    repo_path = repo_dir.resolve()
    name = repo_path.name

    if spec is None:
        spec = get_domain_spec(name=name, domain=domain, org=org)

    assets_dir = repo_path / "assets"
    logo_path = assets_dir / f"{spec.name}-logo.svg"
    banner_path = assets_dir / f"{spec.name}-banner.svg"
    readme_path = repo_path / "README.md"

    logo_content = generate_vector_logo(spec)
    banner_content = generate_vector_banner(spec)

    if not validate_svg_xml(logo_content):
        raise ValueError(f"Generated logo for {spec.name} is not valid XML")
    if not validate_svg_xml(banner_content):
        raise ValueError(f"Generated banner for {spec.name} is not valid XML")

    files_written = []

    if not dry_run:
        assets_dir.mkdir(parents=True, exist_ok=True)
        logo_path.write_text(logo_content, encoding="utf-8")
        banner_path.write_text(banner_content, encoding="utf-8")
        files_written.extend([str(logo_path.relative_to(repo_path)), str(banner_path.relative_to(repo_path))])
        hardening_report = harden_repo_directory(repo_path)
        files_written.extend(hardening_report.get("created", []))

        if update_readme:
            hero_header = generate_readme_hero(spec)
            if readme_path.exists():
                existing_text = readme_path.read_text(encoding="utf-8")
                # If existing README already has a hero block or title, inject hero cleanly
                if not existing_text.startswith('<div align="center">'):
                    # Strip leading top-level header if present
                    clean_body = re.sub(r"^#\s+[^\n]+\n+", "", existing_text).lstrip()
                    # Strip any immediate badge lines right below the old title
                    clean_body = re.sub(r"^(?:\[\!\[[^\]]+\]\([^\)]+\)\]\([^\)]+\)|<a\s+href=[^>]+>.*?</a>|\s*)+\n+", "", clean_body, flags=re.MULTILINE).lstrip()
                    # If clean_body starts with a horizontal rule, strip it
                    clean_body = re.sub(r"^---\s*\n+", "", clean_body).lstrip()
                    new_text = hero_header + "\n" + clean_body
                    readme_path.write_text(new_text, encoding="utf-8")
                    files_written.append("README.md")
            else:
                initial_readme = hero_header + f"""
## Mission Statement

Provide a dedicated, hardened domain harness and orchestration system for `{spec.title}` within the Koality-Assured ecosystem.

## Key Capabilities

- **Automated Worktree Isolation**: Enforces clean git worktrees per task.
- **5-Tier Context Hierarchy**: Context management preventing model bloat.
- **Continuous Integration**: Strict multi-version Python and lint verification.
- **Live Auto-Updating Badges**: Shields.io and GitHub Actions integration.

## Installation & Quickstart

```bash
# Clone the repository
git clone https://github.com/{spec.org}/{spec.name}.git
cd {spec.name}

# Verify test suites
python -m unittest discover -s scripts/tests
```
"""
                readme_path.write_text(initial_readme.strip() + "\n", encoding="utf-8")
                files_written.append("README.md")

    return {
        "status": "success",
        "repo": spec.name,
        "domain": spec.domain,
        "files_written": files_written,
        "dry_run": dry_run,
    }


def main() -> int:
    """CLI entrypoint for repository beautification and hardening."""
    parser = argparse.ArgumentParser(
        description="Automated repository branding, beautification, and hardening tool."
    )
    parser.add_argument(
        "--repo-dir",
        type=Path,
        required=True,
        help="Path to repository directory to beautify.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Repository name override (defaults to folder name).",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="none",
        help="Domain classification (legal, ui-ux, financial, game-dev, art, inventory, etc.).",
    )
    parser.add_argument(
        "--org",
        type=str,
        default=DEFAULT_ORG,
        help=f"GitHub organization (defaults to {DEFAULT_ORG}).",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Custom project title.",
    )
    parser.add_argument(
        "--tagline",
        type=str,
        default=None,
        help="Custom project tagline.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without modifying files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON summary report.",
    )

    args = parser.parse_args()
    name = args.name or args.repo_dir.name
    spec = get_domain_spec(
        name=name,
        domain=args.domain,
        org=args.org,
        title=args.title,
        tagline=args.tagline,
    )

    try:
        res = beautify_repository(
            repo_dir=args.repo_dir,
            spec=spec,
            domain=args.domain,
            org=args.org,
            dry_run=args.dry_run,
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Successfully beautified repository: {res['repo']}")
            for f in res.get("files_written", []):
                print(f"  + {f}")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        if args.json:
            print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        else:
            print(f"Error beautifying repository: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

