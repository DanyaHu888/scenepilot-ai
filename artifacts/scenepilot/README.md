# ScenePilot

ScenePilot turns a scene description and production constraints into a practical shooting plan for filmmakers. It uses Google ADK with Gemini when `GOOGLE_API_KEY` is available, then validates and (when needed) revises the draft with deterministic Python planning tools.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Set `GOOGLE_API_KEY` before starting the app. Set `GOOGLE_GENAI_USE_ENTERPRISE=true` when using Google Cloud Agent Platform Express Mode. `PORT` is provided automatically by Replit.

## API

`POST /api/plan` accepts:

```json
{
  "scene_description": "A night-time conversation in a quiet diner...",
  "budget": 1200,
  "crew_size": 4,
  "shooting_hours": 6,
  "equipment": "camera, tripod, LED panel, boom mic",
  "location_type": "indoor"
}
```

The response includes the scene summary, scene breakdown, shot list, shooting schedule, totals, constraint status, warnings, and adaptations.

## Deployment

The app is configured to bind to `0.0.0.0` and use Replit's injected `PORT`, so it is ready for public deployment without a database or authentication layer.