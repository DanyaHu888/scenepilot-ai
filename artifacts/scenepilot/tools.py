"""Deterministic planning tools used by ScenePilot's agent workflow."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _equipment_tokens(items: Iterable[str] | str) -> list[str]:
    if isinstance(items, str):
        items = items.split(",")
    return [item.strip().lower() for item in items if item and item.strip()]


def calculate_total_shooting_time(shot_list: list[dict[str, Any]]) -> int:
    """Return the total estimated minutes across all shots."""
    return sum(max(0, int(shot.get("estimated_minutes", 0))) for shot in shot_list)


def calculate_total_cost(shot_list: list[dict[str, Any]]) -> float:
    """Return the total estimated cost across all shots."""
    return round(sum(max(0.0, float(shot.get("estimated_cost", 0))) for shot in shot_list), 2)


def check_equipment_availability(
    shot_list: list[dict[str, Any]], available_equipment: Iterable[str] | str
) -> list[dict[str, Any]]:
    """Find shots that need equipment not present in the production kit."""
    available = set(_equipment_tokens(available_equipment))
    missing: list[dict[str, Any]] = []

    for shot in shot_list:
        required = _equipment_tokens(shot.get("equipment", []))
        absent = [item for item in required if item not in available]
        if absent:
            missing.append(
                {
                    "shot_number": shot.get("shot_number"),
                    "missing_equipment": absent,
                }
            )
    return missing


def check_constraints(
    plan: dict[str, Any],
    *,
    budget: float,
    crew_size: int,
    shooting_hours: float,
    available_equipment: Iterable[str] | str,
) -> list[dict[str, Any]]:
    """Check the returned plan against the shooter's hard constraints."""
    shot_list = plan.get("shot_list", [])
    warnings: list[dict[str, Any]] = []
    total_minutes = calculate_total_shooting_time(shot_list)
    total_cost = calculate_total_cost(shot_list)
    allowed_minutes = max(0, int(shooting_hours * 60))

    if total_minutes > allowed_minutes:
        warnings.append(
            {
                "type": "time",
                "severity": "high",
                "message": f"The plan needs {total_minutes} minutes, but only {allowed_minutes} minutes are available.",
            }
        )

    if total_cost > budget:
        warnings.append(
            {
                "type": "budget",
                "severity": "high",
                "message": f"The plan is estimated at ${total_cost:,.0f}, which is above the ${budget:,.0f} budget.",
            }
        )

    over_crew_shots = [
        shot.get("shot_number")
        for shot in shot_list
        if int(shot.get("crew_required", 0)) > crew_size
    ]
    if over_crew_shots:
        warnings.append(
            {
                "type": "crew",
                "severity": "high",
                "message": f"Shot(s) {', '.join(map(str, over_crew_shots))} need more than the available {crew_size}-person crew.",
            }
        )

    missing_equipment = check_equipment_availability(shot_list, available_equipment)
    if missing_equipment:
        details = "; ".join(
            f"shot {item['shot_number']}: {', '.join(item['missing_equipment'])}"
            for item in missing_equipment
        )
        warnings.append(
            {
                "type": "equipment",
                "severity": "medium",
                "message": f"Equipment gaps detected — {details}.",
            }
        )

    return warnings


def produce_constraint_warnings(
    plan: dict[str, Any],
    *,
    budget: float,
    crew_size: int,
    shooting_hours: float,
    available_equipment: Iterable[str] | str,
) -> list[dict[str, Any]]:
    """Public alias used by the agent and the API layer."""
    return check_constraints(
        plan,
        budget=budget,
        crew_size=crew_size,
        shooting_hours=shooting_hours,
        available_equipment=available_equipment,
    )