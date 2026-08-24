"""Sandboxed Agent-to-Agent (A2A) protocol implementation.

Enforces:
- 8-exchange budget decrementer and budget limits
- Structured result envelope validation (task_id, status, artifacts, handoff_requests, metrics)
- Untrusted response content sanitization (responses are data, no prompt injections)
- Clean-state context isolation (no chat history carryover)
- Prevention of self-delegation loops and unauthorized destructive side-effects
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from ..config import A2AConfig, HarnessConfig
except (ImportError, ValueError):
    _HARNESS_ROOT = Path(__file__).resolve().parents[1]
    if str(_HARNESS_ROOT) not in sys.path:
        sys.path.insert(0, str(_HARNESS_ROOT))
    from config import A2AConfig, HarnessConfig

VALID_STATUSES = {
    "completed",
    "failed",
    "in_progress",
    "budget_exhausted",
    "blocked",
    "rejected",
}

INJECTION_PATTERNS = [
    re.compile(r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior)\s+instructions\b"),
    re.compile(r"(?i)\b(?:system\s*prompt|system\s*instructions)\s*override\b"),
    re.compile(r"(?i)<\s*system\s*>"),
    re.compile(r"(?i)<\s*/\s*system\s*>"),
    re.compile(r"(?i)\b(?:you\s+must\s+now|disregard)\s+(?:all\s+)?(?:rules|constraints)\b"),
]

SECRET_PATTERNS = [
    re.compile(r"\b(?:sk-[a-zA-Z0-9-_]{20,})\b"),
    re.compile(r"\b(?:ghp_[a-zA-Z0-9]{30,})\b"),
    re.compile(r"\b(?:Bearer\s+[a-zA-Z0-9_\-\.]{30,})\b"),
    re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
]

DESTRUCTIVE_ACTIONS = {
    "deploy",
    "delete",
    "destroy",
    "drop_database",
    "rotate_key",
    "terminate_instance",
    "reconfigure_iam",
}


class A2AProtocolError(Exception):
    """Base exception for A2A protocol violations."""


class A2AValidationError(A2AProtocolError):
    """Raised when an envelope fails structural validation."""


class A2ABudgetExceededError(A2AProtocolError):
    """Raised when an exchange exceeds the allocated budget."""


class A2ASecurityError(A2AProtocolError):
    """Raised when an envelope contains prompt injections, secrets, or forbidden loops."""


@dataclass
class A2AResultEnvelope:
    """Structured envelope returned by any A2A agent execution."""

    task_id: str
    status: str
    artifacts: list[dict[str, Any] | str] = field(default_factory=list)
    handoff_requests: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    result_data: Any = None
    error: str | None = None
    agent_id: str = ""
    timestamp_utc: str = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert envelope to dictionary."""
        return asdict(self)


@dataclass
class A2ABudgetTracker:
    """Tracks and decrements exchange budget with human-authorized extensions."""

    total_budget: int = 8
    max_budget: int = 24
    remaining_exchanges: int = 8
    exchanges_used: int = 0
    extensions: list[dict[str, Any]] = field(default_factory=list)

    def decrement(self) -> int:
        """Decrement budget by one exchange. Raise error if budget exhausted."""
        if self.remaining_exchanges <= 0:
            raise A2ABudgetExceededError(
                f"A2A call budget exhausted (used {self.exchanges_used}/{self.total_budget}). "
                "Human authorization is required to extend budget."
            )
        self.remaining_exchanges -= 1
        self.exchanges_used += 1
        return self.remaining_exchanges

    def extend(self, additional_exchanges: int, authorization_note: str) -> None:
        """Extend budget with explicit human authorization."""
        if additional_exchanges <= 0:
            raise ValueError("additional_exchanges must be greater than 0")
        if not authorization_note.strip():
            raise ValueError("authorization_note cannot be empty when extending budget")
        if self.total_budget + additional_exchanges > self.max_budget:
            raise A2ABudgetExceededError(
                f"Cannot extend budget by {additional_exchanges}: would exceed max budget limit ({self.max_budget})"
            )
        self.total_budget += additional_exchanges
        self.remaining_exchanges += additional_exchanges
        self.extensions.append({
            "added": additional_exchanges,
            "authorization": authorization_note,
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })


@dataclass
class A2AExchange:
    """Record of a single request-response exchange between two agents."""

    exchange_id: int
    session_id: str
    request: dict[str, Any] | str
    response: A2AResultEnvelope
    timestamp_utc: str = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


class A2AProtocol:
    """Validates and enforces the sandboxed Agent-to-Agent protocol."""

    def __init__(self, config: A2AConfig | HarnessConfig | None = None) -> None:
        if isinstance(config, HarnessConfig):
            self.config = config.a2a
        elif isinstance(config, A2AConfig):
            self.config = config
        else:
            self.config = A2AConfig()

    @staticmethod
    def detect_injections(text: str) -> list[str]:
        """Scan text for instruction-shaped prompt injections."""
        hits: list[str] = []
        for pat in INJECTION_PATTERNS:
            match = pat.search(text)
            if match:
                hits.append(match.group(0))
        return hits

    @staticmethod
    def detect_secrets(text: str) -> list[str]:
        """Scan text for inadvertent credential or secret exposure."""
        hits: list[str] = []
        for pat in SECRET_PATTERNS:
            match = pat.search(text)
            if match:
                hits.append(match.group(0))
        return hits

    def validate_envelope(
        self,
        data: dict[str, Any],
        strict_security: bool = True,
    ) -> A2AResultEnvelope:
        """Validate raw dictionary as a conformant A2AResultEnvelope."""
        if not isinstance(data, dict):
            raise A2AValidationError(f"Envelope must be a dictionary, got {type(data).__name__}")

        # Check required fields
        task_id = str(data.get("task_id", "")).strip()
        if not task_id:
            raise A2AValidationError("Result envelope missing required non-empty 'task_id'")

        status = str(data.get("status", "")).strip()
        if not status:
            raise A2AValidationError("Result envelope missing required non-empty 'status'")
        if status not in VALID_STATUSES:
            raise A2AValidationError(
                f"Invalid status '{status}'. Must be one of: {sorted(VALID_STATUSES)}"
            )

        artifacts = data.get("artifacts")
        if artifacts is None or not isinstance(artifacts, list):
            raise A2AValidationError("Result envelope missing required 'artifacts' list")

        handoff_requests = data.get("handoff_requests")
        if handoff_requests is None or not isinstance(handoff_requests, list):
            raise A2AValidationError("Result envelope missing required 'handoff_requests' list")

        metrics = data.get("metrics")
        if metrics is None or not isinstance(metrics, dict):
            raise A2AValidationError("Result envelope missing required 'metrics' dictionary")

        result_data = data.get("result_data")
        error = data.get("error")
        agent_id = str(data.get("agent_id", ""))
        timestamp_utc = str(
            data.get("timestamp_utc", dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        )

        # Validate security and content hygiene if enabled
        if strict_security:
            # Check string fields for injections and secrets
            fields_to_check = [
                str(result_data) if result_data is not None else "",
                str(error) if error is not None else "",
            ]
            for val in fields_to_check:
                injections = self.detect_injections(val)
                if injections:
                    raise A2ASecurityError(
                        f"Envelope content rejected: instruction-shaped injection detected: {injections}"
                    )
                secrets = self.detect_secrets(val)
                if secrets:
                    raise A2ASecurityError(
                        "Envelope content rejected: secret or API key pattern detected"
                    )

            # Check handoff requests for unauthorized destructive operations
            if self.config.disallow_destructive:
                for req in handoff_requests:
                    if isinstance(req, dict):
                        action = str(req.get("action", "")).lower()
                        has_auth = bool(req.get("human_authorization"))
                        if action in DESTRUCTIVE_ACTIONS and not has_auth:
                            raise A2ASecurityError(
                                f"Destructive delegation '{action}' is disallowed without explicit 'human_authorization'"
                            )

        return A2AResultEnvelope(
            task_id=task_id,
            status=status,
            artifacts=artifacts,
            handoff_requests=handoff_requests,
            metrics=metrics,
            result_data=result_data,
            error=str(error) if error is not None else None,
            agent_id=agent_id,
            timestamp_utc=timestamp_utc,
        )

    def create_session(
        self,
        task_id: str,
        parent_agent: str,
        target_agent: str,
        budget: int | None = None,
        clean_state: bool = True,
    ) -> A2AExchangeSession:
        """Initialize an active A2A delegation session."""
        if parent_agent == target_agent:
            raise A2ASecurityError(
                f"Self-delegation loop detected: parent '{parent_agent}' cannot spawn itself as target '{target_agent}'"
            )

        budget_val = budget or self.config.default_budget
        tracker = A2ABudgetTracker(
            total_budget=budget_val,
            max_budget=self.config.max_budget,
            remaining_exchanges=budget_val,
        )

        return A2AExchangeSession(
            protocol=self,
            session_id=f"a2a-{task_id}-{dt.datetime.now(dt.timezone.utc).strftime('%H%M%S')}",
            task_id=task_id,
            parent_agent=parent_agent,
            target_agent=target_agent,
            budget_tracker=tracker,
            clean_state=clean_state,
        )


class A2AExchangeSession:
    """Manages the state and budget lifecycle for a multi-turn delegation."""

    def __init__(
        self,
        protocol: A2AProtocol,
        session_id: str,
        task_id: str,
        parent_agent: str,
        target_agent: str,
        budget_tracker: A2ABudgetTracker,
        clean_state: bool = True,
    ) -> None:
        self.protocol = protocol
        self.session_id = session_id
        self.task_id = task_id
        self.parent_agent = parent_agent
        self.target_agent = target_agent
        self.budget_tracker = budget_tracker
        self.clean_state = clean_state
        self.exchanges: list[A2AExchange] = []
        self.closed: bool = False

    def record_exchange(
        self,
        request: dict[str, Any] | str,
        response: dict[str, Any] | A2AResultEnvelope,
    ) -> A2AExchange:
        """Record an exchange turn, decrementing budget and validating the response envelope."""
        if self.closed:
            raise A2AProtocolError("Session is closed; cannot record further exchanges")

        # Clean-state check on request: ensure parent chat transcripts are not carried over
        if self.clean_state and isinstance(request, dict):
            if "chat_history" in request or "transcript" in request or "conversation_logs" in request:
                raise A2ASecurityError(
                    "Clean-state rule violation: conversational transcripts / chat history must not be passed to child specialist."
                )

        # Decrement budget
        self.budget_tracker.decrement()

        # Validate response envelope
        if isinstance(response, A2AResultEnvelope):
            envelope = response
        else:
            envelope = self.protocol.validate_envelope(response)

        exchange = A2AExchange(
            exchange_id=len(self.exchanges) + 1,
            session_id=self.session_id,
            request=request,
            response=envelope,
        )
        self.exchanges.append(exchange)

        if envelope.status in {"completed", "failed", "budget_exhausted", "rejected"}:
            self.closed = True

        return exchange

    def extend_budget(self, additional_exchanges: int, authorization_note: str) -> None:
        """Extend exchange budget for this session."""
        was_budget_exhausted = (
            self.closed
            and bool(self.exchanges)
            and self.exchanges[-1].response.status == "budget_exhausted"
        )
        self.budget_tracker.extend(additional_exchanges, authorization_note)
        if was_budget_exhausted and self.budget_tracker.remaining_exchanges > 0:
            self.closed = False
