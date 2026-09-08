"""Flask entrypoint for ScenePilot."""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, render_template, request

from agent import create_production_plan


app = Flask(__name__, template_folder="templates", static_folder="static")


def _parse_inputs(payload: dict[str, Any]) -> dict[str, Any]:
    scene_description = str(payload.get("scene_description", "")).strip()
    if len(scene_description) < 20:
        raise ValueError("Add a little more scene detail — at least 20 characters helps the plan stay specific.")

    try:
        budget = float(payload.get("budget", 0))
        crew_size = int(payload.get("crew_size", 0))
        shooting_hours = float(payload.get("shooting_hours", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Budget, crew size, and shooting hours must be valid numbers.") from exc

    if budget <= 0:
        raise ValueError("Enter a budget greater than $0.")
    if crew_size <= 0:
        raise ValueError("Enter a crew size of at least 1.")
    if shooting_hours <= 0:
        raise ValueError("Enter at least 1 available shooting hour.")

    equipment = payload.get("equipment", "")
    if isinstance(equipment, list):
        equipment = ", ".join(str(item) for item in equipment)
    equipment = str(equipment).strip()
    if not equipment:
        raise ValueError("List at least one available piece of equipment.")

    location_type = str(payload.get("location_type", "")).lower().strip()
    location_type = {
        "interior": "indoor",
        "exterior": "outdoor",
        "controlled_stage": "indoor",
    }.get(location_type, location_type)
    if location_type not in {"indoor", "outdoor", "mixed"}:
        raise ValueError("Choose indoor, outdoor, or mixed for the location type.")

    return {
        "scene_description": scene_description,
        "budget": round(budget, 2),
        "crew_size": crew_size,
        "shooting_hours": shooting_hours,
        "equipment": equipment,
        "location_type": location_type,
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/healthz")
def healthz():
    return jsonify({"status": "ok", "service": "scenepilot"})


@app.post("/api/plan")
def plan():
    if not request.is_json:
        return jsonify({"error": "Send the planning inputs as JSON."}), 400
    try:
        inputs = _parse_inputs(request.get_json(silent=True) or {})
        return jsonify(create_production_plan(inputs))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("ScenePilot planning request failed")
        return jsonify({"error": "ScenePilot could not complete the plan. Try again with a little more scene detail."}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)