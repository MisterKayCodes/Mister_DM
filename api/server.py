import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import config
from api.dependencies import verify_api_key

from api.routes.health import router as health_router
from api.routes.campaigns import router as campaigns_router
from api.routes.leads import router as leads_router
from api.routes.stats import router as stats_router
from api.routes.webhook import router as webhook_router

app = FastAPI(
    title="Mister DM API",
    description="API Gateway for Mister DM Campaign Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Public endpoints (no X-API-Key required — server-to-server webhook, stats & health check)
app.include_router(health_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")

# 2. Protected endpoints (require valid X-API-Key header)
app.include_router(campaigns_router, prefix="/api/v1", dependencies=[Depends(verify_api_key)])
app.include_router(leads_router, prefix="/api/v1", dependencies=[Depends(verify_api_key)])

async def start_api_server():
    server_config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=config.DM_API_PORT,
        log_level="info"
    )
    server = uvicorn.Server(server_config)
    await server.serve()
