"""API 路由注册"""
from fastapi import APIRouter

from app.api.router import router as api_keys_router
from app.api.v1 import router as magazine_router

api_router = APIRouter()
api_router.include_router(api_keys_router)
api_router.include_router(magazine_router)
