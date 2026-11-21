from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.health import router as health_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.matching import router as matching_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.skill_gaps import router as skill_gaps_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(interviews_router)
api_router.include_router(auth_router)
api_router.include_router(candidates_router)
api_router.include_router(jobs_router)
api_router.include_router(matching_router)
api_router.include_router(resumes_router)
api_router.include_router(skill_gaps_router)
