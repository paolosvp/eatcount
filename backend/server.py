from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone, date as date_cls
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from jose import jwt, JWTError
from dotenv import load_dotenv
import os
import uuid
import logging
import json

# LLM integration
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

# Load .env
ROOT_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(ROOT_DIR, '.env'))

# --- Environment and Config ---
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-change-me')
JWT_ALG = os.environ.get('JWT_ALG', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# MongoDB
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# App and router
app = FastAPI(title="Calorie Counter API")
api = APIRouter(prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---- Helpers ----

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)
    return encoded_jwt


async def get_current_user(request: Request) -> Dict[str, Any]:
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.lower().startswith('bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        user = await db.users.find_one({"_id": user_id})
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ---- Models ----
class AuthRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class AuthLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdate(BaseModel):
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    age: int = Field(gt=0)
    gender: str = Field(pattern=r"^(male|female|other)$")
    activity_level: str = Field(pattern=r"^(sedentary|light|moderate|very|extra)$")
    goal: str = Field(pattern=r"^(lose|maintain|gain)$")
    goal_intensity: str = Field(pattern=r"^(mild|moderate|aggressive)$", default="moderate")
    goal_weight_kg: Optional[float] = Field(default=None, gt=0)


class ProfileResponse(BaseModel):
    id: str
    email: EmailStr
    profile: Optional[Dict[str, Any]]


class ImageAttachment(BaseModel):
    data: str  # base64 only
    mime_type: str = Field(pattern=r"^image\/(jpeg|png|gif|webp)$")
    filename: Optional[str] = None


class AIItem(BaseModel):
    name: str
    quantity_units: str
    calories: float
    confidence: float


class AIRequest(BaseModel):
    message: Optional[str] = ""
    images: List[ImageAttachment]
    api_key: Optional[str] = None
    simulate: Optional[bool] = False


class AIResponse(BaseModel):
    total_calories: float
    items: List[AIItem]
    confidence: float
    notes: Optional[str] = None


# ---- Calorie computation ----
ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "very": 1.725,
    "extra": 1.9,
}

GOAL_ADJUST = {
    ("lose", "mild"): -250,
    ("lose", "moderate"): -500,
    ("lose", "aggressive"): -750,
    ("maintain", "mild"): 0,
    ("maintain", "moderate"): 0,
    ("maintain", "aggressive"): 0,
    ("gain", "mild"): 250,
    ("gain", "moderate"): 400,
    ("gain", "aggressive"): 600,
}


def compute_daily_calories(height_cm: float, weight_kg: float, age: int, gender: str, activity_level: str, goal: str, goal_intensity: str) -> int:
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if gender == 'male' else -161)
    tdee = bmr * ACTIVITY_FACTORS[activity_level]
    adjust = GOAL_ADJUST[(goal, goal_intensity)]
    return max(1200, int(round(tdee + adjust)))


# ---- Routes ----
@api.get('/')
async def root():
    return {"message": "Calorie Counter API running"}


@api.get('/health')
async def health():
    return {
        "status": "ok",
        "db": True,
        "model": "gpt-4o",
        "llm_key_available": bool(EMERGENT_LLM_KEY),
        "time": datetime.utcnow().isoformat()
    }


# Auth
@api.post('/auth/register', response_model=TokenResponse)
async def register(payload: AuthRegister):
    email = payload.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    uid = str(uuid.uuid4())
    user_doc = {
        "_id": uid,
        "email": email,
        "password_hash": hash_password(payload.password),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "profile": None,
    }
    await db.users.insert_one(user_doc)
    token = create_access_token({"sub": uid, "email": email})
    return TokenResponse(access_token=token)


@api.post('/auth/login', response_model=TokenResponse)
async def login(payload: AuthLogin):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get('password_hash', '')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user['_id'], "email": email})
    return TokenResponse(access_token=token)


@api.get('/profile/me', response_model=ProfileResponse)
async def me(user=Depends(get_current_user)):
    return ProfileResponse(id=user['_id'], email=user['email'], profile=user.get('profile'))


@api.put('/profile', response_model=ProfileResponse)
async def update_profile(update: ProfileUpdate, user=Depends(get_current_user)):
    daily = compute_daily_calories(update.height_cm, update.weight_kg, update.age, update.gender, update.activity_level, update.goal, update.goal_intensity)
    profile = {
        "height_cm": update.height_cm,
        "weight_kg": update.weight_kg,
        "age": update.age,
        "gender": update.gender,
        "activity_level": update.activity_level,
        "goal": update.goal,
        "goal_intensity": update.goal_intensity,
        "goal_weight_kg": update.goal_weight_kg,
        "recommended_daily_calories": daily,
        "updated_at": datetime.utcnow().isoformat(),
    }
    await db.users.update_one({"_id": user['_id']}, {"$set": {"profile": profile, "updated_at": datetime.utcnow()}})
    user_after = await db.users.find_one({"_id": user['_id']})
    return ProfileResponse(id=user_after['_id'], email=user_after['email'], profile=user_after.get('profile'))


# ---- AI Estimation ----
SYSTEM_PROMPT = (
    "You are a careful nutrition assistant. Given food images and an optional user note, "
    "estimate calories conservatively. Return ONLY strict JSON in this exact schema, no extra text: "
    "{\n  \"total_calories\": number,\n  \"items\": [ { \"name\": string, \"quantity_units\": string, \"calories\": number, \"confidence\": number } ],\n  \"confidence\": number,\n  \"notes\": string\n}. "
    "Use metric units where possible. Confidence must be 0-1."
)


def _force_extract_json(text: str) -> Dict[str, Any]:
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end+1])
    except Exception:
        pass
    return {
        "total_calories": 0,
        "items": [],
        "confidence": 0.0,
        "notes": "Failed to parse model output"
    }


@api.post('/ai/estimate-calories')
async def estimate_calories(payload: AIRequest):
    # Use Emergent LLM Key by default if available; still allow simulate toggle
    if payload.simulate or not (payload.api_key or EMERGENT_LLM_KEY):
        sample = {
            "total_calories": 420,
            "items": [
                {"name": "Grilled chicken", "quantity_units": "150g", "calories": 250, "confidence": 0.78},
                {"name": "Mixed salad", "quantity_units": "1 bowl", "calories": 80, "confidence": 0.7},
                {"name": "Olive oil", "quantity_units": "1 tbsp", "calories": 90, "confidence": 0.65}
            ],
            "confidence": 0.74,
            "notes": "Simulated estimate (no API key provided)"
        }
        return JSONResponse(content=sample)

    key = payload.api_key or EMERGENT_LLM_KEY
    try:
        chat = LlmChat(api_key=key, session_id=str(uuid.uuid4()), system_message=SYSTEM_PROMPT).with_model("openai", "gpt-4o")
        files: List[ImageContent] = [ImageContent(image_base64=img.data) for img in payload.images]
        user_text = payload.message or "Estimate calories for the attached food image(s)."
        umsg = UserMessage(text=user_text, file_contents=files)
        resp = await chat.send_message(umsg)
        raw_text = str(resp)
        try:
            parsed = json.loads(raw_text)
        except Exception:
            parsed = _force_extract_json(raw_text)
        if not isinstance(parsed, dict) or 'total_calories' not in parsed:
            parsed = _force_extract_json(raw_text)
        return JSONResponse(content=parsed)
    except Exception as e:
        logger.exception("LLM estimation failed")
        raise HTTPException(status_code=500, detail=f"AI Estimation failed: {e}")


# ---- Meals (Day Log) ----
class MealItem(BaseModel):
    name: str
    quantity_units: str
    calories: float
    confidence: float


class MealCreate(BaseModel):
    total_calories: float = Field(ge=0)
    items: List[MealItem]
    notes: Optional[str] = None
    image_base64: Optional[str] = None
    captured_at: Optional[str] = None


class MealOut(BaseModel):
    id: str
    total_calories: float
    items: List[MealItem]
    notes: Optional[str]
    image_base64: Optional[str]
    created_at: str


class MealsForDateResponse(BaseModel):
    date: str
    meals: List[MealOut]
    daily_total: float


def _today_range_utc(date_str: Optional[str] = None):
    if date_str:
        try:
            y, m, d = [int(x) for x in date_str.split('-')]
            start = datetime(y, m, d, 0, 0, 0, tzinfo=timezone.utc)
        except Exception:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


@api.post('/meals', response_model=MealOut)
async def add_meal(meal: MealCreate, user=Depends(get_current_user)):
    meal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    created_at = now if not meal.captured_at else datetime.fromisoformat(meal.captured_at)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    doc = {
        "_id": meal_id,
        "user_id": user['_id'],
        "total_calories": float(meal.total_calories),
        "items": [i.model_dump() for i in meal.items],
        "notes": meal.notes,
        "image_base64": meal.image_base64,
        "created_at": created_at
    }
    await db.meals.insert_one(doc)
    return MealOut(
        id=meal_id,
        total_calories=doc['total_calories'],
        items=[MealItem(**i) for i in doc['items']],
        notes=doc['notes'],
        image_base64=doc['image_base64'],
        created_at=doc['created_at'].isoformat()
    )


@api.get('/meals', response_model=MealsForDateResponse)
async def list_meals(date: Optional[str] = Query(default=None, description="YYYY-MM-DD"), user=Depends(get_current_user)):
    start, end = _today_range_utc(date)
    cursor = db.meals.find({
        "user_id": user['_id'],
        "created_at": {"$gte": start, "$lt": end}
    }).sort("created_at", 1)
    meals = []
    total = 0.0
    async for m in cursor:
        total += float(m.get('total_calories', 0))
        meals.append(MealOut(
            id=m['_id'],
            total_calories=float(m.get('total_calories', 0)),
            items=[MealItem(**i) for i in m.get('items', [])],
            notes=m.get('notes'),
            image_base64=m.get('image_base64'),
            created_at=m.get('created_at').isoformat() if m.get('created_at') else datetime.now(timezone.utc).isoformat()
        ))
    date_out = (start.date()).isoformat()
    return MealsForDateResponse(date=date_out, meals=meals, daily_total=round(total, 2))


@api.delete('/meals/{meal_id}')
async def delete_meal(meal_id: str, user=Depends(get_current_user)):
    res = await db.meals.delete_one({"_id": meal_id, "user_id": user['_id']})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Meal not found")
    return {"deleted": True}


@api.get('/meals/stats')
async def meal_stats(user=Depends(get_current_user)):
    # Aggregate unique days with meals (UTC)
    cursor = db.meals.find({"user_id": user['_id']}, {"created_at": 1}).sort("created_at", 1)
    days = []
    async for m in cursor:
        dt = m.get('created_at')
        if not dt:
            continue
        day = dt.date()
        if not days or days[-1] != day:
            days.append(day)

    # Compute current streak (consecutive days ending today)
    today = datetime.now(timezone.utc).date()
    day_set = set(days)
    cur = 0
    d = today
    while d in day_set:
        cur += 1
        d = d - timedelta(days=1)

    # Compute best streak
    best = 0
    i = 0
    days_sorted = sorted(day_set)
    while i < len(days_sorted):
        j = i
        while j + 1 < len(days_sorted) and days_sorted[j + 1] == days_sorted[j] + timedelta(days=1):
            j += 1
        best = max(best, j - i + 1)
        i = j + 1

    return {"current_streak_days": cur, "best_streak_days": best}


# Include router
app.include_router(api)


@app.on_event("shutdown")
async def shutdown_db():
    mongo_client.close()