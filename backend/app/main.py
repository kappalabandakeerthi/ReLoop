import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base
from .seeds.seed_data import seed_database
from .routers import (
    auth_router,
    devices_router,
    assessments_router,
    recommendations_router,
    providers_router,
    recovery_router,
    admin_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize schema and baseline seeds in thread pool
    await asyncio.to_thread(Base.metadata.create_all, bind=engine)
    try:
        await asyncio.to_thread(seed_database)
    except Exception as e:
        print(f"[ReLoop Startup] Seed notice: {e}")
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ReLoop Smart Electronic Device Recovery Platform REST APIs",
    lifespan=lifespan
)

# CORS Middleware for Next.js frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers under API prefix
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(devices_router, prefix=settings.API_V1_PREFIX)
app.include_router(assessments_router, prefix=settings.API_V1_PREFIX)
app.include_router(recommendations_router, prefix=settings.API_V1_PREFIX)
app.include_router(providers_router, prefix=settings.API_V1_PREFIX)
app.include_router(recovery_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "platform": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "tagline": "Give Your Electronics a Second Chance",
        "docs_url": "/docs",
        "status": "operational"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ReLoop Backend API & Decision Engine"
    }
