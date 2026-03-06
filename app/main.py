from fastapi import FastAPI
from routers import facebook_api
from websockets_routes import facebook_ws
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine, Base
import DBmodels.CommentModel

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created!")

origins = [
    "http://localhost:5173",  # your frontend
    # "https://yourdomain.com",  # production frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # domains allowed
    allow_credentials=True,
    allow_methods=["*"],         # allow all HTTP methods
    allow_headers=["*"],         # allow all headers
)

app.include_router(facebook_api.router, prefix="/facebook", tags=["facebook"])
app.include_router(facebook_ws.router, prefix="/websockets", tags=["websockets"])
