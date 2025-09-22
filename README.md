# Calorie Tracker (Camera + AI) – README

This repository contains a full‑stack calories counter app with a React frontend, FastAPI backend, and MongoDB. Users can capture or upload meal photos, estimate calories using an AI vision model, save meals to a Day Log, and track daily intake vs. a computed daily target.

Live Frontend: Use REACT_APP_BACKEND_URL configured in frontend/.env to reach the backend (all endpoints are prefixed with /api).


## Tech Stack
- Frontend: React, Tailwind (custom CSS), Axios (with a centralized client and JWT interceptor)
- Backend: FastAPI, Motor (MongoDB async driver), Pydantic, Passlib (bcrypt), jose (JWT)
- AI Integration: emergentintegrations.llm.chat with OpenAI gpt-4o (vision)
- Database: MongoDB (UUID string IDs; no ObjectId in APIs)


## Key Features
1) Authentication
- Email/password registration and login
- JWT-based sessions; interceptor injects JWT for all API calls
- 401 auto handling: session-expired event prompts user to re-login

2) Profile & Daily Target
- Profile inputs: height (cm), weight (kg), age, gender, activity level, goal, intensity, optional goal weight
- Daily calories computed using Mifflin–St Jeor + activity factor + goal adjustment
- Profile values hydrate UI after load/save

3) Camera & Image Upload (Mobile friendly)
- Start/stop camera, capture image
- Upload image (mobile/desktop)
- Always render video/canvas in DOM to avoid ref issues

4) AI Calories Estimation (Vision)
- Provider: OpenAI gpt-4o via emergentintegrations.llm.chat
- Strict JSON schema enforced; parsing retry + conservative fallback
- Key policy:
  - Test mode ON: simulated, deterministic sample
  - Live mode + Provided key (non-empty): use exactly that key; no fallback; invalid -> 401 error
  - Live mode + Empty key: use Emergent LLM Key from backend environment
  - Responses include engine_info: { key_mode, model }

5) Day Log & Daily Total
- Save estimated meal with items, notes, and image base64
- Fetch meals for any local date; daily total and progress vs. profile target
- Delete meal entries
- CSV export for selected date (created_at uses local time with offset)

6) Timezone & Dates (Resolved)
- Saving: frontend sends captured_at in local time with timezone offset (e.g., 2025-09-21T14:05:00+02:00)
- Backend stores created_at (tz-aware) and display_local (verbatim local timestamp when provided)
- Listing (/meals): query window converts local YYYY-MM-DD + tz_offset_minutes into UTC [start, end) correctly
- UI prefers display_local for showing times; otherwise formats created_at in friendly local format


## Frontend – How to Use
- Account panel:
  - Register or Login with email/password
  - Session stored in localStorage; interceptor applies JWT automatically
- Profile panel:
  - Fill out inputs; Save & Compute shows daily target
  - Inputs hydrate from saved profile after load/save
- Scan a Meal:
  - Start Camera or Upload Image
  - Optional description
  - Modes:
    - Test mode ON (default on first run): simulated estimate, no key needed
    - Live mode OFF -> ON: if API key field empty, backend uses Emergent key; if filled, uses provided key only
  - Save to Day Log adds the meal to today’s entries; Day Log updates from server
- Day Log:
  - Choose a date (local calendar day)
  - Shows entries with image thumbnails, friendly time, items, and kcal
  - Shows daily total and progress bar vs target
  - Delete to remove an entry
  - Download CSV (created_at in local time with timezone offset)


## Backend – API Summary (all routes prefixed with /api)
- GET /api/health – status, model, llm_key_available
- Auth
  - POST /api/auth/register { email, password } -> { access_token }
  - POST /api/auth/login { email, password } -> { access_token }
- Profile (JWT required)
  - GET /api/profile/me -> { id, email, profile }
  - PUT /api/profile { height_cm, weight_kg, age, gender, activity_level, goal, goal_intensity, goal_weight_kg? } -> { id, email, profile }
- AI Estimate
  - POST /api/ai/estimate-calories { message?, images:[{ data(base64), mime_type, filename? }], simulate?, api_key? }
    - Key policy: provided key only if non-empty; else Emergent key; else simulated if simulate=true; returns engine_info
    - Response JSON schema:
      {
        total_calories: number,
        items: [ { name, quantity_units, calories, confidence } ],
        confidence: number,
        notes?: string,
        engine_info: { key_mode, model }
      }
- Meals (JWT required)
  - POST /api/meals { total_calories, items[], notes?, image_base64?, captured_at? } -> MealOut
    - Server also stores display_local if captured_at provided (for exact local display)
  - GET /api/meals?date=YYYY-MM-DD&tz_offset_minutes=number -> { date, meals: MealOut[], daily_total }
  - DELETE /api/meals/{id} -> { deleted: true }
  - GET /api/meals/stats -> { current_streak_days, best_streak_days }

MealOut:
{
  id: string,
  total_calories: number,
  items: [ { name, quantity_units, calories, confidence } ],
  notes?: string,
  image_base64?: string,
  created_at: string (ISO),
  display_local?: string (local ISO with offset at save time)
}


## Environment & Configuration
- Frontend: REACT_APP_BACKEND_URL must point to the backend; never hardcode URLs in code
- Backend binds at 0.0.0.0:8001 (supervisor); all routes must be prefixed by /api
- MongoDB: backend/.env supplies MONGO_URL; DB name from DB_NAME (defaults to test_database)
- Emergent LLM Key: backend/.env sets EMERGENT_LLM_KEY (used when Live mode key input is empty)


## Security Notes
- JWT stored in localStorage; centralized axios client injects Authorization headers
- On 401, UI clears local tokens and prompts for login
- Passwords hashed using bcrypt via passlib


## Known Edge Cases & Troubleshooting
- Invalid token on save: log out/in to refresh JWT; interceptor should handle 401 globally
- Camera permission denied: fall back to Upload Image
- Live estimate returns empty: backend now retries with strict JSON prompt and uses a conservative fallback
- Wrong day in Day Log: ensure date picker shows local date; backend uses tz_offset_minutes correctly


## Development Notes
- All backend endpoints under /api – required for ingress
- IDs in API are UUID strings to simplify client usage
- Images stored/sent as base64
- Time handling: prefer display_local for UI; created_at for storage and UTC querying


## License
This project is provided as-is for demonstration and internal use. Please ensure you comply with all third-party API terms and handle user data responsibly.