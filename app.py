import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import httpx

# --- Init ---
app = FastAPI()

# Plain httpx client (Render safe, no proxies arg)
http_client = httpx.Client()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=http_client
)




# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dummy data ---
listings = [
    {
        "id": 1,
        "city": "Mumbai",
        "price": 50,
        "wifi": True,
        "guests": 2
    },
    {
        "id": 2,
        "city": "Pune",
        "price": 70,
        "wifi": False,
        "guests": 3
    },
    {
        "id": 3,
        "city": "Delhi",
        "price": 40,
        "wifi": True,
        "guests": 2
    },
]

bookings = []


# --- Models ---
class Query(BaseModel):
    city: str | None = None
    guests: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    budget: int | None = None
    message: str | None = None


# --- Routes ---
@app.get("/")
async def home():
    return {"msg": "Welcome to StayFinder API"}


@app.post("/api/search")
async def search_stays(query: Query):
    results = [
        l for l in listings
        if (not query.city or l["city"].lower() == query.city.lower())
    ]
    if query.budget:
        results = [l for l in results if l["price"] <= query.budget]
    if query.guests:
        results = [l for l in results if l["guests"] >= query.guests]

    return {
        "results":
        results,
        "reply":
        f"Found {len(results)} stays{f' in {query.city}' if query.city else ''}."
    }


@app.post("/api/book")
async def book_stay(data: dict):
    booking = {"id": len(bookings) + 1, **data}
    bookings.append(booking)
    return {"msg": "Booking successful!", "booking": booking}


@app.post("/api/chat")
async def chat_with_assistant(q: Query):
    if not q.message:
        return {"reply": "Please type a message."}

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role":
                "system",
                "content":
                ("You are a helpful AI assistant for the StayFinder app. "
                 "Help users with bookings, listings, FAQs, travel advice, "
                 "and politely answer unrelated queries."),
            },
            {
                "role": "user",
                "content": q.message
            },
        ],
    )

    return {"reply": response.choices[0].message.content}


@app.post("/assistant")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role":
                    "system",
                    "content":
                    ("You are a helpful AI assistant. "
                     "Your main job is to help with the StayFinder app (bookings, listings, FAQs, support). "
                     "Answer unrelated queries politely as a general assistant."
                     ),
                },
                {
                    "role": "user",
                    "content": user_message
                },
            ],
        )
        reply = response.choices[0].message.content
        return {"reply": reply}

    except Exception as e:
        return {"error": str(e)}


# --- Optional Test Route ---
@app.get("/test")
async def test_openai():
    response = client.models.list()
    return {"models_count": len(response.data)}
