from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
import time

# Core & Infrastructure
from app.core.logger import logger
from app.core.exception_handler import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

# --- 1. SpiffWorkflow BPMN 2.0 Engine & Human Tasks APIs ---
from app.workflow.api.definitions import router as workflow_definitions_router
from app.workflow.api.human_tasks import router as workflow_tasks_router
from app.workflow.api.monitoring import router as workflow_monitoring_router
from app.workflow.api.jobs import router as workflow_jobs_router
from app.workflow.api.executor import router as workflow_executor_router

# --- 2. Workflow Management, Platform Lifecycle & Migrations API ---
from app.workflow_management.api import router as workflow_management_router

# --- 3. Generic Workflow Graph Definition & Validation API ---
from app.workflow_definition.api import router as workflow_definition_router

# --- 4. Visual Workflow Studio & Node Catalog API ---
from app.workflow_studio.api import (
    router as workflow_studio_router,
    catalog_router as workflow_studio_catalog_router
)
from app.workflow_studio.connections_api import router as workflow_connections_router
from app.workflow.api.client_gateway import router as client_gateway_router
from app.workflow.api.workflows_api import router as workflows_api_router

# Trigger dynamic registration of custom & generic workflow service tasks
import app.workflow.activities.generic_activities
import app.workflow_activities.custom_activities

load_dotenv()

app = FastAPI(
    title="Enterprise Workflow Engine & Studio API",
    description="Dedicated BPMN 2.0 Workflow Management, Visual Studio & Execution Engine API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for Workflow Studio Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check ---
@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "healthy",
        "service": "Workflow Engine & Studio Platform API",
        "version": "2.0.0"
    }

# --- Pure Workflow APIs ---
app.include_router(workflow_definitions_router)
app.include_router(workflow_tasks_router)
app.include_router(workflow_monitoring_router)
app.include_router(workflow_jobs_router)
app.include_router(workflow_executor_router)
# Dedicated Workflow GET & Inspection APIs
app.include_router(workflows_api_router)

app.include_router(workflow_management_router)
app.include_router(workflow_definition_router)
app.include_router(workflow_studio_router)
app.include_router(workflow_studio_catalog_router)
app.include_router(workflow_connections_router)
app.include_router(client_gateway_router)

# --- Real-Time Workflow WebSocket Gateway ---
from fastapi import WebSocket, WebSocketDisconnect
from app.core.websocket import ws_manager

@app.on_event("startup")
async def on_startup():
    import asyncio
    try:
        ws_manager.set_event_loop(asyncio.get_running_loop())
    except Exception as e:
        logger.warning(f"Could not bind WebSocket event loop on startup: {e}")
    logger.info("Workflow WebSocket Gateway active at /ws/workflow")

@app.websocket("/ws/workflow")
async def workflow_websocket_endpoint(websocket: WebSocket, user_id: str = None):
    await ws_manager.connect(websocket, user_id=user_id)
    try:
        while True:
            text = await websocket.receive_text()
            if text == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# --- Global Exception Handlers ---
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# --- Request / Response Logging Middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_body = await request.body()
    try:
        request_body_text = request_body.decode("utf-8") if request_body else ""
    except UnicodeDecodeError:
        request_body_text = "<binary request>"

    if "password" in request_body_text:
        request_body_text = "HIDDEN"

    logger.info(f"REQUEST | {request.method} {request.url} | BODY: {request_body_text}")

    response = await call_next(request)

    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    try:
        response_body_text = response_body.decode("utf-8")
    except UnicodeDecodeError:
        response_body_text = "<binary request>"

    process_time = time.time() - start_time
    logger.info(
        f"RESPONSE | {request.method} {request.url} | "
        f"STATUS: {response.status_code} | "
        f"TIME: {process_time:.4f}s | "
        f"BODY: {response_body_text}"
    )

    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )