"""Resolve skill dependency DAGs, topological ordering, and execution stages.

tags: [routing, skills, dag]
routing_hints: [skills, dependencies, topological-sort, execution-plan, prerequisites]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Standard _lib imports
_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

try:
    from paths import REPO_ROOT as DEFAULT_ROOT
except ImportError:
    DEFAULT_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_RANKS = {"critical", "high", "medium", "low"}
ALLOWED_ISOLATION = {"mutate", "read-only"}
ALLOWED_FAILURE_POLICIES = {
    "abort_and_rollback",
    "fallback_degrade",
    "continue_with_partial",
}
DEFAULT_FAILURE_POLICY = "abort_and_rollback"
DEFAULT_SCHEMA_VERSION = "2.0.0"


class SkillGraphError(Exception):
    """Base exception for skill graph and DAG resolution errors."""


class SkillNotFoundError(SkillGraphError):
    """Raised when a requested skill cannot be found in the catalog."""


class MissingSkillDependencyError(SkillGraphError):
    """Raised when a skill depends on a non-existent skill."""


class SkillGraphCycleError(SkillGraphError):
    """Raised when a cyclic dependency is detected in the skill DAG."""


class InvalidSkillSchemaError(SkillGraphError):
    """Raised when a skill frontmatter does not satisfy schema requirements."""


class InvalidLifecyclePolicyError(SkillGraphError):
    """Raised when an unrecognized on_failure policy is specified."""


@dataclass
class SkillDefinition:
    name: str
    description: str = ""
    owner_agent: str = ""
    rank: str = "medium"
    isolation: str = "read-only"
    schema_version: str = DEFAULT_SCHEMA_VERSION
    on_failure: str = DEFAULT_FAILURE_POLICY
    required_skills: list[str] = field(default_factory=list)
    delegated_skills: list[str] = field(default_factory=list)
    in_session_skills: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    contracts: dict[str, Any] = field(default_factory=dict)
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "owner_agent": self.owner_agent,
            "rank": self.rank,
            "isolation": self.isolation,
            "schema_version": self.schema_version,
            "on_failure": self.on_failure,
            "required_skills": list(self.required_skills),
            "delegated_skills": list(self.delegated_skills),
            "in_session_skills": list(self.in_session_skills),
            "prerequisites": list(self.prerequisites),
            "contracts": self.contracts,
            "path": self.path,
        }


@dataclass
class ExecutionPlan:
    target: str
    stages: list[list[str]]
    topological_order: list[str]
    skills: dict[str, dict[str, Any]]
    on_failure_policies: dict[str, str]
    prerequisites_check: dict[str, dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "stages": self.stages,
            "topological_order": self.topological_order,
            "skills": self.skills,
            "on_failure_policies": self.on_failure_policies,
            "prerequisites_check": self.prerequisites_check,
        }

    def simulate_failure(self, failed_skill: str, adj: dict[str, list[str]] | None = None) -> dict[str, Any]:
        """Simulate the lifecycle behavior when a specific skill fails."""
        if failed_skill not in self.skills:
            raise SkillNotFoundError(f"Skill '{failed_skill}' is not part of this execution plan.")

        policy = self.on_failure_policies.get(failed_skill, DEFAULT_FAILURE_POLICY)

        # Find downstream dependent skills
        downstream: set[str] = set()
        if adj is not None:
            queue = list(adj.get(failed_skill, []))
            visited = set()
            while queue:
                curr = queue.pop(0)
                if curr not in visited:
                    visited.add(curr)
                    downstream.add(curr)
                    queue.extend(adj.get(curr, []))
        else:
            # Fallback based on topological order
            idx = self.topological_order.index(failed_skill) if failed_skill in self.topological_order else -1
            if idx != -1:
                downstream = set(self.topological_order[idx + 1:])

        if policy == "abort_and_rollback":
            return {
                "failed_skill": failed_skill,
                "policy": policy,
                "action": "abort_and_rollback",
                "aborted_skills": sorted(list(downstream)),
                "status": "failed_aborted",
                "description": "Execution halted; downstream dependent tasks aborted and state rollback triggered.",
            }
        elif policy == "fallback_degrade":
            return {
                "failed_skill": failed_skill,
                "policy": policy,
                "action": "fallback_degrade",
                "degraded_skills": [failed_skill] + sorted(list(downstream)),
                "status": "degraded_continue",
                "description": "Skill marked degraded; downstream stages proceed with fallback degradation.",
            }
        elif policy == "continue_with_partial":
            return {
                "failed_skill": failed_skill,
                "policy": policy,
                "action": "continue_with_partial",
                "partial_skills": [failed_skill],
                "status": "partial_continue",
                "description": "Partial failure recorded; unaffected downstream stages continue execution.",
            }
        else:
            return {
                "failed_skill": failed_skill,
                "policy": policy,
                "action": "unknown",
                "status": "error",
                "description": f"Unknown failure policy: {policy}",
            }


def parse_skill_frontmatter(text: str, source_path: Path | None = None) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and markdown body from a SKILL.md file."""
    if not text.startswith("---"):
        return {}, text
    rest = text[3:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]

    end = rest.find("\n---")
    if end == -1:
        end = rest.find("\r\n---")
        if end == -1:
            return {}, text

    raw_yaml = rest[:end]
    body = rest[end + 4 :]
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]

    try:
        data = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as exc:
        location = f" in {source_path}" if source_path else ""
        raise InvalidSkillSchemaError(f"Malformed YAML frontmatter{location}: {exc}") from exc

    if not isinstance(data, dict):
        location = f" in {source_path}" if source_path else ""
        raise InvalidSkillSchemaError(f"Frontmatter must be a YAML mapping{location}")

    return data, body


def load_skill_from_file(path: Path) -> SkillDefinition:
    """Load and parse a SkillDefinition from a SKILL.md file."""
    text = path.read_text(encoding="utf-8")
    data, _ = parse_skill_frontmatter(text, source_path=path)

    name = str(data.get("name", path.parent.name)).strip()
    if not name:
        name = path.parent.name

    schema_version = str(data.get("schema_version", "1.0.0")).strip()
    description = str(data.get("description", "")).strip()
    owner_agent = str(data.get("owner_agent", "")).strip()
    rank = str(data.get("rank", "medium")).strip()
    isolation = str(data.get("isolation", "read-only")).strip()
    on_failure = str(data.get("on_failure", DEFAULT_FAILURE_POLICY)).strip()

    if on_failure not in ALLOWED_FAILURE_POLICIES:
        raise InvalidLifecyclePolicyError(
            f"Invalid on_failure policy '{on_failure}' in {path}. "
            f"Must be one of {sorted(ALLOWED_FAILURE_POLICIES)}"
        )

    # Dependencies parsing
    deps_raw = data.get("dependencies") or {}
    required_skills: list[str] = []
    delegated_skills: list[str] = []
    in_session_skills: list[str] = []

    if isinstance(deps_raw, dict):
        req = deps_raw.get("required_skills") or []
        if isinstance(req, list):
            required_skills = [str(s).strip() for s in req if str(s).strip()]
        delg = deps_raw.get("delegated_skills") or []
        if isinstance(delg, list):
            delegated_skills = [str(s).strip() for s in delg if str(s).strip()]
        in_s = deps_raw.get("in_session_skills") or []
        if isinstance(in_s, list):
            in_session_skills = [str(s).strip() for s in in_s if str(s).strip()]

    # Prerequisites parsing
    prereqs_raw = data.get("prerequisites") or []
    prerequisites: list[str] = []
    if isinstance(prereqs_raw, list):
        prerequisites = [str(p).strip() for p in prereqs_raw if str(p).strip()]

    # Contracts parsing
    contracts_raw = data.get("contracts") or {}
    contracts = contracts_raw if isinstance(contracts_raw, dict) else {}

    return SkillDefinition(
        name=name,
        description=description,
        owner_agent=owner_agent,
        rank=rank,
        isolation=isolation,
        schema_version=schema_version,
        on_failure=on_failure,
        required_skills=required_skills,
        delegated_skills=delegated_skills,
        in_session_skills=in_session_skills,
        prerequisites=prerequisites,
        contracts=contracts,
        path=str(path.resolve()),
    )


class SkillGraph:
    """Directed graph representing skills and their required/delegated relationships."""

    def __init__(self) -> None:
        self.skills: dict[str, SkillDefinition] = {}

    def add_skill(self, skill: SkillDefinition) -> None:
        self.skills[skill.name] = skill

    @classmethod
    def from_directory(cls, skills_dir: Path) -> SkillGraph:
        graph = cls()
        if not skills_dir.exists():
            return graph
        for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
            skill = load_skill_from_file(skill_file)
            graph.add_skill(skill)
        return graph

    def check_prerequisites(self, skill_names: list[str] | None = None) -> dict[str, dict[str, Any]]:
        """Pre-flight check for binary prerequisites using shutil.which."""
        targets = [self.skills[name] for name in (skill_names or self.skills.keys()) if name in self.skills]
        tool_requirements: dict[str, set[str]] = {}
        for skill in targets:
            for tool in skill.prerequisites:
                tool_requirements.setdefault(tool, set()).add(skill.name)

        results: dict[str, dict[str, Any]] = {}
        for tool in sorted(tool_requirements.keys()):
            binary_path = shutil.which(tool)
            results[tool] = {
                "tool": tool,
                "available": binary_path is not None,
                "path": binary_path,
                "required_by": sorted(list(tool_requirements[tool])),
            }
        return results

    def build_adjacency(self, node_names: set[str]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """Build forward (u executes before v: u -> v) and reverse adjacency maps.

        Relationships:
        - If V requires U (U in V.required_skills): U must run before V -> edge U -> V
        - If U delegates to V (V in U.delegated_skills): U spawns V -> edge U -> V
        """
        forward_adj: dict[str, list[str]] = {n: [] for n in node_names}
        reverse_adj: dict[str, list[str]] = {n: [] for n in node_names}

        for v_name in node_names:
            skill = self.skills[v_name]
            # Required skills: req -> v
            for req in skill.required_skills:
                if req in node_names:
                    if v_name not in forward_adj[req]:
                        forward_adj[req].append(v_name)
                    if req not in reverse_adj[v_name]:
                        reverse_adj[v_name].append(req)

            # Delegated skills: v -> delg
            for delg in skill.delegated_skills:
                if delg in node_names:
                    if delg not in forward_adj[v_name]:
                        forward_adj[v_name].append(delg)
                    if v_name not in reverse_adj[delg]:
                        reverse_adj[delg].append(v_name)

        # Sort adjacency lists for deterministic results
        for k in forward_adj:
            forward_adj[k].sort()
        for k in reverse_adj:
            reverse_adj[k].sort()

        return forward_adj, reverse_adj

    def find_cycle(self, nodes: list[str], adj: dict[str, list[str]]) -> list[str] | None:
        """Find and return an exact cycle path if one exists in the graph."""
        state: dict[str, int] = {node: 0 for node in nodes}  # 0=unvisited, 1=visiting, 2=visited
        path: list[str] = []

        def dfs(u: str) -> list[str] | None:
            state[u] = 1
            path.append(u)
            for v in sorted(adj.get(u, [])):
                if v not in state:
                    continue
                if state[v] == 1:
                    cycle_start = path.index(v)
                    return path[cycle_start:] + [v]
                elif state[v] == 0:
                    res = dfs(v)
                    if res is not None:
                        return res
            path.pop()
            state[u] = 2
            return None

        for node in sorted(nodes):
            if state[node] == 0:
                cycle = dfs(node)
                if cycle is not None:
                    return cycle
        return None

    def resolve_subgraph_nodes(self, target_skill: str) -> set[str]:
        """Find all nodes in the DAG closure for a target skill."""
        if target_skill not in self.skills:
            raise SkillNotFoundError(f"Skill '{target_skill}' not found in catalog.")

        needed: set[str] = set()
        queue: list[str] = [target_skill]

        while queue:
            curr = queue.pop(0)
            if curr not in needed:
                needed.add(curr)
                if curr not in self.skills:
                    raise MissingSkillDependencyError(
                        f"Skill '{curr}' is referenced as a dependency but was not found in catalog."
                    )
                skill = self.skills[curr]
                for req in skill.required_skills:
                    if req not in self.skills:
                        raise MissingSkillDependencyError(
                            f"Skill '{curr}' requires '{req}', but '{req}' is not in catalog."
                        )
                    if req not in needed:
                        queue.append(req)
                for delg in skill.delegated_skills:
                    if delg not in self.skills:
                        raise MissingSkillDependencyError(
                            f"Skill '{curr}' delegates to '{delg}', but '{delg}' is not in catalog."
                        )
                    if delg not in needed:
                        queue.append(delg)

        return needed

    def resolve_plan(self, target: str | None = None, check_prereqs: bool = False) -> ExecutionPlan:
        """Resolve DAG execution plan for a single target skill or all skills."""
        if target is not None and target != "all":
            node_set = self.resolve_subgraph_nodes(target)
            target_name = target
        else:
            # Validate all references
            for s_name, skill in self.skills.items():
                for req in skill.required_skills:
                    if req not in self.skills:
                        raise MissingSkillDependencyError(
                            f"Skill '{s_name}' requires '{req}', but '{req}' is not in catalog."
                        )
                for delg in skill.delegated_skills:
                    if delg not in self.skills:
                        raise MissingSkillDependencyError(
                            f"Skill '{s_name}' delegates to '{delg}', but '{delg}' is not in catalog."
                        )
            node_set = set(self.skills.keys())
            target_name = "all"

        forward_adj, reverse_adj = self.build_adjacency(node_set)
        nodes_list = sorted(list(node_set))

        # Check for cycles
        cycle = self.find_cycle(nodes_list, forward_adj)
        if cycle is not None:
            cycle_str = " -> ".join(cycle)
            raise SkillGraphCycleError(f"Cyclic dependency detected: {cycle_str}")

        # Topological sorting and parallel staging using Kahn's algorithm
        # In-degree of v = number of predecessors in reverse_adj[v]
        in_degree = {n: len(reverse_adj[n]) for n in nodes_list}

        stages: list[list[str]] = []
        topological_order: list[str] = []

        current_stage = sorted([n for n in nodes_list if in_degree[n] == 0])

        while current_stage:
            stages.append(current_stage)
            topological_order.extend(current_stage)
            next_stage_candidates: list[str] = []
            for u in current_stage:
                for v in forward_adj[u]:
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        next_stage_candidates.append(v)
            current_stage = sorted(next_stage_candidates)

        if len(topological_order) < len(nodes_list):
            unresolved = [n for n in nodes_list if in_degree[n] > 0]
            raise SkillGraphCycleError(
                f"Cyclic dependency detected among unresolved skills: {', '.join(sorted(unresolved))}"
            )

        skills_meta = {n: self.skills[n].to_dict() for n in topological_order}
        failure_policies = {n: self.skills[n].on_failure for n in topological_order}

        prereqs_res = None
        if check_prereqs:
            prereqs_res = self.check_prerequisites(topological_order)

        return ExecutionPlan(
            target=target_name,
            stages=stages,
            topological_order=topological_order,
            skills=skills_meta,
            on_failure_policies=failure_policies,
            prerequisites_check=prereqs_res,
        )

    def validate_catalog(self, check_prereqs: bool = True) -> dict[str, Any]:
        """Validate entire skill catalog for broken dependencies, cycles, schema issues, and prereqs."""
        errors: list[str] = []
        warnings: list[str] = []
        missing_dependencies: list[dict[str, str]] = []

        # Check references
        for name, skill in sorted(self.skills.items()):
            for req in skill.required_skills:
                if req not in self.skills:
                    msg = f"Skill '{name}' requires unknown skill '{req}'"
                    errors.append(msg)
                    missing_dependencies.append({"source": name, "type": "required", "target": req})
            for delg in skill.delegated_skills:
                if delg not in self.skills:
                    msg = f"Skill '{name}' delegates to unknown skill '{delg}'"
                    errors.append(msg)
                    missing_dependencies.append({"source": name, "type": "delegated", "target": delg})

        # Check global cycles
        cycles: list[list[str]] = []
        try:
            forward_adj, _ = self.build_adjacency(set(self.skills.keys()))
            cycle = self.find_cycle(sorted(list(self.skills.keys())), forward_adj)
            if cycle is not None:
                cycles.append(cycle)
                errors.append(f"Cyclic dependency detected: {' -> '.join(cycle)}")
        except Exception as exc:
            errors.append(f"Cycle detection error: {exc}")

        # Check prerequisites
        prereqs_summary: dict[str, dict[str, Any]] = {}
        if check_prereqs:
            prereqs_summary = self.check_prerequisites()
            missing_tools = [tool for tool, data in prereqs_summary.items() if not data["available"]]
            if missing_tools:
                warnings.append(f"Missing binary tools on PATH: {', '.join(missing_tools)}")

        ok = len(errors) == 0
        return {
            "ok": ok,
            "total_skills": len(self.skills),
            "errors": errors,
            "warnings": warnings,
            "cycles_detected": cycles,
            "missing_dependencies": missing_dependencies,
            "prerequisites_summary": prereqs_summary,
        }


def format_plan_text(plan: ExecutionPlan) -> str:
    """Format an ExecutionPlan into human-readable text."""
    lines: list[str] = []
    lines.append(f"=== Skill Execution Plan: {plan.target} ===")
    lines.append(f"Total skills in plan: {len(plan.topological_order)}")
    lines.append(f"Total execution stages: {len(plan.stages)}\n")

    lines.append("--- Parallel Execution Stages ---")
    for idx, stage in enumerate(plan.stages):
        lines.append(f"Stage {idx} ({len(stage)} parallelizable skill{'s' if len(stage) != 1 else ''}):")
        for skill_name in stage:
            meta = plan.skills.get(skill_name, {})
            owner = meta.get("owner_agent", "unknown")
            rank = meta.get("rank", "medium")
            iso = meta.get("isolation", "read-only")
            fail_policy = meta.get("on_failure", DEFAULT_FAILURE_POLICY)
            prereqs = meta.get("prerequisites", [])
            prereq_str = f" [prereqs: {', '.join(prereqs)}]" if prereqs else ""
            lines.append(
                f"  - {skill_name:<24} | owner: {owner:<20} | rank: {rank:<8} | isolation: {iso:<9} | on_failure: {fail_policy}{prereq_str}"
            )
    lines.append("")

    lines.append(f"Topological Order: {' -> '.join(plan.topological_order)}\n")

    if plan.prerequisites_check:
        lines.append("--- Binary Prerequisites Status ---")
        for tool, data in plan.prerequisites_check.items():
            status = "FOUND" if data["available"] else "MISSING"
            path_str = f" ({data['path']})" if data["path"] else ""
            required_by = ", ".join(data.get("required_by", []))
            lines.append(f"  [{status:<7}] {tool:<12}{path_str} (needed by: {required_by})")
        lines.append("")

    return "\n".join(lines)


def format_validation_text(report: dict[str, Any]) -> str:
    """Format a catalog validation report into human-readable text."""
    lines: list[str] = []
    status_str = "PASSED" if report["ok"] else "FAILED"
    lines.append(f"=== Skill Catalog Validation: {status_str} ===")
    lines.append(f"Total skills inspected: {report['total_skills']}")

    if report["errors"]:
        lines.append("\nErrors:")
        for err in report["errors"]:
            lines.append(f"  [ERROR] {err}")

    if report["warnings"]:
        lines.append("\nWarnings:")
        for warn in report["warnings"]:
            lines.append(f"  [WARN]  {warn}")

    if report.get("prerequisites_summary"):
        lines.append("\nPrerequisites Summary:")
        for tool, data in report["prerequisites_summary"].items():
            status = "FOUND" if data["available"] else "MISSING"
            path_str = f" ({data['path']})" if data["path"] else ""
            lines.append(f"  [{status:<7}] {tool:<12}{path_str}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve skill dependency DAGs, topological ordering, and execution stages."
    )
    parser.add_argument(
        "--skill",
        help="Resolve DAG and execution plan for a specific skill name (e.g. isolate-work).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Resolve the full DAG across all registered skills.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured execution plan or validation report in JSON.",
    )
    parser.add_argument(
        "--check-prereqs",
        action="store_true",
        help="Perform pre-flight verification of binary prerequisites on PATH using shutil.which.",
    )
    parser.add_argument(
        "--validate-all",
        action="store_true",
        help="Validate all skills in the catalog for dependency completeness, schema, cycles, and prereqs.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Optional path to repository root (defaults to auto-detected root).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Flag accepted for convention compatibility (resolution never mutates state).",
    )

    args = parser.parse_args(argv)

    if not args.skill and not args.all and not args.validate_all:
        parser.print_help(file=sys.stderr)
        return 2

    repo_root = args.repo_root.resolve()
    skills_dir = repo_root / "ai-tooling" / "skills"

    try:
        graph = SkillGraph.from_directory(skills_dir)

        if args.validate_all:
            report = graph.validate_catalog(check_prereqs=args.check_prereqs)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(format_validation_text(report))
            return 0 if report["ok"] else 1

        target = args.skill if args.skill else "all"
        plan = graph.resolve_plan(target=target, check_prereqs=args.check_prereqs)

        if args.json:
            print(json.dumps({"ok": True, "plan": plan.to_dict()}, indent=2))
        else:
            print(format_plan_text(plan))
        return 0

    except SkillGraphError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                    },
                    indent=2,
                )
            )
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                    },
                    indent=2,
                )
            )
        else:
            print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
