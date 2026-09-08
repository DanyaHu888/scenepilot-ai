"""ScenePilot's planning agent and deterministic fallback planner."""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from tools import (
    calculate_total_cost,
    calculate_total_shooting_time,
    check_equipment_availability,
    produce_constraint_warnings,
)


def _normalise_equipment(equipment: str | list[str]) -> list[str]:
    if isinstance(equipment, list):
        return [item.strip() for item in equipment if item and item.strip()]
    return [item.strip() for item in equipment.split(",") if item.strip()]


def _scene_subject(scene_description: str) -> str:
    clean = " ".join(scene_description.split())
    if not clean:
        return "the scene"
    return clean.rstrip(".")[:120]


def build_deterministic_draft(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a useful plan without a model, so the demo remains inspectable."""
    description = _scene_subject(inputs["scene_description"])
    location_type = inputs["location_type"]
    equipment = _normalise_equipment(inputs["equipment"])
    equipment_lower = {item.lower() for item in equipment}
    camera = next((item for item in equipment if "camera" in item.lower()), "camera package")
    audio = next(
        (item for item in equipment if any(token in item.lower() for token in ("mic", "audio", "recorder"))),
        "sound kit",
    )
    light = next(
        (item for item in equipment if any(token in item.lower() for token in ("light", "led", "lantern"))),
        "available light",
    )

    base_cost = 110 if "camera" in camera.lower() else 85
    has_stabiliser = any(
        token in equipment_lower for token in ("tripod", "gimbal", "slider", "dolly")
    )
    movement_shot = "Gimbal or tripod movement" if has_stabiliser else "Locked-off movement alternative"
    shots = [
        {
            "shot_number": 1,
            "shot_type": "Establishing wide",
            "description": f"Introduce {description} with a clean view of the {location_type} environment.",
            "equipment": [camera, light],
            "crew_required": min(3, max(2, int(inputs["crew_size"]))),
            "estimated_minutes": 35,
            "estimated_cost": base_cost,
        },
        {
            "shot_number": 2,
            "shot_type": "Master two-shot",
            "description": "Cover the complete action in one dependable performance take before moving closer.",
            "equipment": [camera, audio],
            "crew_required": min(4, max(2, int(inputs["crew_size"]))),
            "estimated_minutes": 45,
            "estimated_cost": base_cost + 25,
        },
        {
            "shot_number": 3,
            "shot_type": "Medium coverage",
            "description": "Capture the key exchange with enough space for performance and a clean edit.",
            "equipment": [camera, audio, light],
            "crew_required": min(4, max(2, int(inputs["crew_size"]))),
            "estimated_minutes": 40,
            "estimated_cost": base_cost + 15,
        },
        {
            "shot_number": 4,
            "shot_type": "Detail insert",
            "description": "Record the prop or gesture that gives the moment its visual punctuation.",
            "equipment": [camera, light],
            "crew_required": min(3, max(2, int(inputs["crew_size"]))),
            "estimated_minutes": 25,
            "estimated_cost": base_cost - 10,
        },
        {
            "shot_number": 5,
            "shot_type": "Movement option",
            "description": f"Add a restrained movement pass using {movement_shot.lower()} to give the sequence a lift.",
            "equipment": [camera, "gimbal" if has_stabiliser else "tripod"],
            "crew_required": min(4, max(2, int(inputs["crew_size"]))),
            "estimated_minutes": 40,
            "estimated_cost": base_cost + 35,
        },
    ]

    cast = "Lead performer(s) and any background talent described in the scene."
    if re.search(r"\b(two|couple|pair|friends|conversation)\b", description, re.I):
        cast = "Two speaking performers, with a small background presence if the location supports it."

    props = "Story-relevant objects called out in the scene; confirm continuity before the first take."
    if re.search(r"\b(letter|phone|key|cup|book|bag|car|table)\b", description, re.I):
        props = "The scene's hero prop, plus one continuity duplicate where practical."

    return {
        "scene_summary": f"A focused, shootable plan for {description}. The approach protects the story beat first, then adds coverage that can be achieved with a lean crew.",
        "scene_breakdown": {
            "cast": cast,
            "props": props,
            "location": f"{location_type.title()} setup with a short pre-light and a clear reset path between takes.",
            "lighting": f"Shape the key with {light}; keep a flexible natural-light option so the schedule can move quickly.",
            "production_risks": [
                "Continuity drift between coverage angles.",
                "Ambient sound changes during performance takes.",
                "The final movement shot may need to be simplified if time runs short.",
            ],
        },
        "shot_list": shots,
        "adaptations_made": [
            "Coverage is ordered from essential master material to optional polish so the scene can be protected under pressure.",
        ],
    }


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Gemini did not return a JSON object.")
    return json.loads(cleaned[start : end + 1])


def _gemini_prompt(inputs: dict[str, Any], draft: dict[str, Any], warnings: list[dict[str, Any]] | None = None) -> str:
    constraint_context = ""
    if warnings:
        constraint_context = (
            "\nA deterministic validator found these issues. Revise once to fix them where possible:\n"
            + json.dumps(warnings, ensure_ascii=False)
        )
    return f"""
You are the ScenePilot production planning agent. Return only a JSON object, never commentary.
Do not reveal hidden reasoning. Create a practical production plan from the input below.
Respect the requested budget, crew size, shooting hours, equipment, and location type.
Keep the exact response shape:
{{
  "scene_summary": "string",
  "scene_breakdown": {{
    "cast": "string",
    "props": "string",
    "location": "string",
    "lighting": "string",
    "production_risks": ["string"]
  }},
  "shot_list": [
    {{
      "shot_number": 1,
      "shot_type": "string",
      "description": "string",
      "equipment": ["string"],
      "crew_required": 1,
      "estimated_minutes": 1,
      "estimated_cost": 1
    }}
  ],
  "adaptations_made": ["string"]
}}

INPUT:
{json.dumps(inputs, ensure_ascii=False)}

CURRENT DRAFT:
{json.dumps(draft, ensure_ascii=False)}
{constraint_context}
"""


async def _run_adk(prompt: str) -> dict[str, Any]:
    """Run Gemini through Google ADK's in-memory runner."""
    from google.adk.agents import Agent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    agent = Agent(
        name="scenepilot_planner",
        model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
        description="Turns scene requirements into practical shooting plans.",
        instruction=(
            "Return strict JSON only. Use the input and current draft provided by the user. "
            "Never expose chain-of-thought or hidden reasoning."
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )
    runner = InMemoryRunner(agent=agent, app_name="scenepilot")
    events = await runner.run_debug(prompt, quiet=True)
    for event in reversed(events):
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text
            if text:
                return _extract_json(text)
    raise RuntimeError("The planning agent returned no final response.")


def _normalise_plan(plan: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    """Keep model output safe for the UI while retaining fallback coverage."""
    merged = {**fallback, **plan}
    merged["scene_breakdown"] = {**fallback["scene_breakdown"], **plan.get("scene_breakdown", {})}
    merged["shot_list"] = plan.get("shot_list") or fallback["shot_list"]
    merged["adaptations_made"] = plan.get("adaptations_made") or fallback["adaptations_made"]
    for shot_index, shot in enumerate(merged["shot_list"], start=1):
        shot.setdefault("shot_number", shot_index)
        shot.setdefault("shot_type", "Coverage shot")
        shot.setdefault("description", "Capture the essential story action.")
        shot.setdefault("equipment", [])
        shot.setdefault("crew_required", 2)
        shot.setdefault("estimated_minutes", 30)
        shot.setdefault("estimated_cost", 100)
    return merged


def create_production_plan(inputs: dict[str, Any]) -> dict[str, Any]:
    """Execute the requested analyse -> draft -> validate -> revise workflow."""
    draft = build_deterministic_draft(inputs)
    adaptations = list(draft["adaptations_made"])
    google_key_available = bool(os.getenv("GOOGLE_API_KEY"))

    if google_key_available:
        try:
            model_draft = asyncio.run(_run_adk(_gemini_prompt(inputs, draft)))
            draft = _normalise_plan(model_draft, draft)
        except Exception:
            adaptations.append("The first-pass agent response was unavailable, so the deterministic production draft was retained.")
    else:
        adaptations.append("No Google API key was available, so a deterministic draft was used.")

    warnings = produce_constraint_warnings(
        draft,
        budget=inputs["budget"],
        crew_size=inputs["crew_size"],
        shooting_hours=inputs["shooting_hours"],
        available_equipment=inputs["equipment"],
    )

    if warnings and google_key_available:
        try:
            revised = asyncio.run(_run_adk(_gemini_prompt(inputs, draft, warnings)))
            draft = _normalise_plan(revised, draft)
            adaptations.append("The plan was revised once against the time, budget, crew, and equipment warnings.")
            warnings = produce_constraint_warnings(
                draft,
                budget=inputs["budget"],
                crew_size=inputs["crew_size"],
                shooting_hours=inputs["shooting_hours"],
                available_equipment=inputs["equipment"],
            )
        except Exception:
            adaptations.append("A revision pass was requested but the original validated draft was kept.")

    total_minutes = calculate_total_shooting_time(draft["shot_list"])
    total_cost = calculate_total_cost(draft["shot_list"])
    allowed_minutes = int(inputs["shooting_hours"] * 60)
    constraint_status = "Ready with notes" if warnings else "Within constraints"

    schedule: list[dict[str, Any]] = []
    elapsed = 0
    for shot in draft["shot_list"]:
        start = elapsed
        elapsed += int(shot["estimated_minutes"])
        schedule.append(
            {
                "order": len(schedule) + 1,
                "shot_number": shot["shot_number"],
                "start_time": f"{start // 60:02d}:{start % 60:02d}",
                "end_time": f"{elapsed // 60:02d}:{elapsed % 60:02d}",
                "description": shot["description"],
            }
        )

    return {
        **draft,
        "shooting_schedule": schedule,
        "total_estimated_time": total_minutes,
        "total_estimated_cost": total_cost,
        "constraint_status": constraint_status,
        "warnings": warnings,
        "adaptations_made": adaptations,
        "workflow_stages": [
            {"name": "Analysing Scene", "status": "complete"},
            {"name": "Creating Shot Plan", "status": "complete"},
            {"name": "Checking Constraints", "status": "complete"},
            {"name": "Revising Plan", "status": "complete" if warnings else "skipped"},
        ],
        "available_minutes": allowed_minutes,
        "available_equipment": _normalise_equipment(inputs["equipment"]),
        "missing_equipment": check_equipment_availability(
            draft["shot_list"], inputs["equipment"]
        ),
    }