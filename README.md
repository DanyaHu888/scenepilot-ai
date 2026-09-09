# ScenePilot

ScenePilot is an AI production-planning assistant that transforms a scene description and practical constraints into a shoot-ready production plan.

It uses Google Gemini through Google ADK for creative planning, while deterministic Python tools verify time, crew, equipment and budget requirements.

## Features

- Gemini-generated scene analysis
- Structured shot list and shooting schedule
- Budget, crew, time and equipment validation
- Automatic Gemini revision when constraints are violated
- Deterministic production-cost calculations
- Detailed cost breakdown
- Gemini/Fallback generation indicator
- Automatic retry for temporary API errors
- Print and Save as PDF
- Responsive desktop and mobile interface
- Deterministic fallback when Gemini is unavailable

## Agent workflow

1. The user enters a scene description and production constraints.
2. Gemini analyses the scene and generates a structured production plan.
3. Python tools calculate production costs and validate the plan.
4. If constraints are violated, the warnings are returned to Gemini.
5. Gemini revises the plan once.
6. ScenePilot returns the final validated production plan.

Gemini handles the creative decisions. Python handles calculations and constraint checks that need consistent results.

## Technology

- Python
- Flask
- Google Agent Development Kit
- Gemini
- HTML
- CSS
- JavaScript
- Replit

No database, authentication system or external media-generation service is required.

## Project structure

```text
scenepilot/
├── app.py
├── agent.py
├── tools.py
├── requirements.txt
├── templates/
│   └── index.html
├── static/
│   ├── app.js
│   └── style.css
├── README.md
├── LICENSE
└── .gitignore
```

## Environment variables

Create these as secure Replit Secrets:

```text
GOOGLE_API_KEY=your_google_api_key
GOOGLE_GENAI_USE_ENTERPRISE=TRUE
```

Optional:

```text
GOOGLE_MODEL=gemini-2.5-flash
```

Never place API keys directly in the source code or commit them to version control.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

For the current Replit development environment:

```bash
PORT=20941 python3 app.py
```

## Planning endpoint

ScenePilot accepts planning requests at:

```text
POST /generate-plan
```

Example request:

```json
{
  "scene_description": "A courier runs into a rainy street while being followed by a suspicious car.",
  "budget": 1500,
  "crew_size": 1,
  "shooting_hours": 4,
  "equipment": "Mirrorless camera, tripod, LED panel, lav mic",
  "location_type": "mixed"
}
```

The response contains:

- Scene summary
- Cast, props, location, lighting and risks
- Shot list
- Shooting schedule
- Total time and cost
- Cost breakdown
- Constraint status
- Warnings
- Adaptations
- Generation source

## Cost estimates

The deterministic cost model includes:

- Labour at $50 per crew member per hour
- Location and permit allowance
- Transport
- Meals
- Props and consumables
- 10% contingency

These values are illustrative planning estimates and are not professional production quotes.

## Reliability

If Gemini encounters a temporary rate-limit or service error, ScenePilot retries once. If Gemini remains unavailable, the deterministic fallback planner returns a usable plan and clearly labels it as a fallback result.

## License

This project is licensed under the MIT License.