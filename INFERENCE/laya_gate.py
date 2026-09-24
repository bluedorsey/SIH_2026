"""Laya decision-model gate: is this a safety observation or routine operations?

Runs BEFORE the existing scope gate and GLiNER. Laya is a non-autoregressive
"System 1" decision model (convaiinnovations/laya) that answers structured
questions in a single forward pass (~33 ms on GPU, ~120 ms on CPU).

Unlike the logistic scope gate, Laya can distinguish "a vehicle struck a worker"
(safety event involving a vehicle) from "a vehicle was parked in the designated
area" (routine operations mentioning a vehicle) because its bidirectional encoder
reads the FULL context, not just isolated keywords.

Fault-tolerant: if the `laya` package is not installed or the model fails to
load, `available` stays False and the pipeline behaves exactly as before — the
existing scope gate + evidence gate still run.
"""
from __future__ import annotations

import logging

from .config import LAYA_ENABLED, LAYA_MODEL, LAYA_ROUTINE_THRESHOLD, BASE_MODELS_DIR

log = logging.getLogger("inference.laya_gate")


# The structured questions Laya answers in a single forward pass.
# `noul` = boolean probability (is this statement true?).
# `choice` = pick the best label from a defined set.
QUESTIONS = {
    "is_safety_event": {
        "type": "noul",
        "instructions": (
            "This statement describes a workplace safety incident, unsafe act, "
            "unsafe condition, near-miss, hazardous situation, injury, damage, "
            "spill, leak, fall, struck-by event, or any situation where a worker "
            "was exposed to danger or a safety barrier was missing or failed."
        ),
    },
    "is_routine": {
        "type": "noul",
        "instructions": (
            "This statement describes routine, normal, safe operations such as "
            "vehicle arrival, parking, scheduled maintenance completed without "
            "issues, toolbox talks conducted, permits issued normally, equipment "
            "inspections with no findings, or administrative activities."
        ),
    },
    "event_type": {
        "type": "choice",
        "instructions": "What type of event does this statement describe?",
        "criteria": {
            "safety_incident": (
                "injury, near-miss, unsafe act, unsafe condition, equipment failure, "
                "spill, leak, fall, struck-by, fire, explosion, exposure to hazard, "
                "missing or failed safety barrier"
            ),
            "routine_operations": (
                "normal work, vehicle arrival, parking, shift handover, scheduled "
                "task completed safely, equipment functioning normally, area clear"
            ),
            "administrative": (
                "paperwork, meetings, reports filed, permits issued without issues, "
                "training attendance, canteen, IT, HR, payroll"
            ),
            "maintenance_log": (
                "equipment status readings, routine inspection with no findings, "
                "calibration completed, preventive maintenance done"
            ),
        },
    },
}


class LayaGate:
    """Wraps the Laya Router for use as a pipeline pre-filter."""

    def __init__(self) -> None:
        self.router = None
        self.available = False
        self.enabled = LAYA_ENABLED
        self.model = LAYA_MODEL
        self.threshold = LAYA_ROUTINE_THRESHOLD

    def load(self) -> "LayaGate":
        """Load the Laya model. Called once; subsequent calls are no-ops."""
        if self.router is not None:
            return self
        if not self.enabled:
            log.info("Laya gate disabled via config (LAYA_ENABLED=False)")
            return self
        try:
            from laya import Router  # noqa: WPS433

            local_model_path = BASE_MODELS_DIR / "laya_multilingual"
            if (local_model_path / "model.safetensors").exists():
                log.info("Laya gate using local offline model: %s", local_model_path)
                # Pass a custom models dict so 'multilingual' resolves to our local path
                self.router = Router(models={"multilingual": str(local_model_path)}, preload=True)
            else:
                self.router = Router(preload=True)
                
            self.available = True
            log.info(
                "Laya gate loaded (model=%s, threshold=%.2f)",
                self.model,
                self.threshold,
            )
        except ImportError:
            log.warning(
                "Laya gate unavailable: `laya` package not installed. "
                "Install with `pip install laya`. Pipeline continues without it."
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Laya gate failed to load: %s", str(exc)[:200])
        return self

    def check(self, text: str) -> dict:
        """Classify a statement as routine/administrative or safety-relevant.

        Returns
        -------
        dict with keys:
            reject : bool   — True when the statement is routine/admin and should
                              skip the full EEI pipeline (verdict = NON_EVENT).
            event_type : str — "safety_incident", "routine_operations",
                               "administrative", or "maintenance_log".
            p_routine : float|None — probability that the statement is routine.
            p_safety : float|None — probability that the statement is a safety event.
            reason : str    — human-readable explanation.
        """
        if not self.available:
            return {
                "reject": False,
                "event_type": None,
                "p_routine": None,
                "p_safety": None,
                "reason": "laya gate unavailable",
            }
            
        import re
        ROUTINE_DESCRIPTIONS = [
            r"vehicle arrived at the gate",
            r"parked in the designated area",
            r"toolbox talk conducted",
            r"routine patrol",
        ]
        for pattern in ROUTINE_DESCRIPTIONS:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    "reject": True,
                    "event_type": "routine_operations",
                    "p_routine": 1.0,
                    "p_safety": 0.0,
                    "reason": f"rule engine match: {pattern}"
                }

        try:
            result = self.router.predict(text, QUESTIONS, model=self.model)

            # Extract probabilities
            p_routine = float(result.get("is_routine", {}).get("probability", 0.0))
            p_safety = float(result.get("is_safety_event", {}).get("probability", 0.0))

            # Extract event_type choice
            event_choice = result.get("event_type", {})
            event_type = event_choice.get("prediction", "safety_incident")
            event_prob = float(event_choice.get("probability", 0.0))

            # Extract noul probabilities (might be uncalibrated 0.0 initially)
            p_routine = float(result.get("is_routine", {}).get("probability", 0.0))
            p_safety = float(result.get("is_safety_event", {}).get("probability", 0.0))

            # The gate should only reject (skip EEI) if it is HIGHLY CONFIDENT
            # that this is routine/admin. If the model is uncalibrated (returning 0.0s),
            # this safely falls through and lets the existing pipeline handle it.
            is_routine_type = event_type in ("routine_operations", "administrative", "maintenance_log")
            
            # Reject if either the 'choice' is very confident OR the 'noul' is very confident
            confident_routine = (is_routine_type and event_prob >= self.threshold) or (p_routine >= self.threshold)
            
            # Don't reject if safety signals are high
            safety_override = p_safety >= (1.0 - self.threshold)

            reject = confident_routine and not safety_override

            reason = (
                f"laya: event_type={event_type}@{event_prob:.2f}, p_routine={p_routine:.2f}, "
                f"p_safety={p_safety:.2f}"
            )
            if reject:
                reason = f"routine operations — {reason}"

            return {
                "reject": reject,
                "event_type": event_type,
                "p_routine": round(p_routine, 4),
                "p_safety": round(p_safety, 4),
                "reason": reason,
            }

        except Exception as exc:  # noqa: BLE001
            log.warning("Laya gate inference failed: %s", str(exc)[:200])
            return {
                "reject": False,
                "event_type": None,
                "p_routine": None,
                "p_safety": None,
                "reason": f"laya inference error: {str(exc)[:100]}",
            }


# ---- singleton ----

_GATE: LayaGate | None = None


def get_laya_gate() -> LayaGate:
    global _GATE  # noqa: PLW0603
    if _GATE is None:
        _GATE = LayaGate().load()
    return _GATE
