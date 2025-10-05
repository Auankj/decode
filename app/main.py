"""
Cookie-Licking Detector - Production FastAPI Application
Enterprise-ready backend with complete authentication, monitoring, and webhook support.
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.monitoring import (
    health_checker, track_request_metrics, get_metrics, 
    CONTENT_TYPE_LATEST
)
from app.core.security import add_security_headers
from app.db.database import get_async_session, create_tables, close_db

# Import all route modules
from app.api.auth_routes import router as auth_router
from app.api.repository_routes import router as repository_router
from app.api.claim_routes import router as claim_router
from app.api.dashboard_routes import router as dashboard_router
from app.api.webhook_routes import router as webhook_router
from app.api.user_routes import router as user_router
from app.api.settings_routes import router as settings_router
from app.websockets.routes import router as websocket_router
# Initialize configuration and logging
settings = get_settings()
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Cookie Licking Detector API")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Create database tables if needed (optional - app can run without DB)
    if settings.ENVIRONMENT in ["development", "testing"]:
        try:
            await create_tables()
            logger.info("Database tables created")
        except Exception as e:
            logger.warning(f"Could not create database tables: {e}")
            logger.info("App will continue without database - some features may be limited")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cookie Licking Detector API")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="Cookie Licking Detector API",
    description="""Enterprise platform for detecting and managing stale issue claims in GitHub repositories.
    
🍪 **Smart Claim Detection**: AI-powered detection of issue claims in comments  
📊 **Real-time Monitoring**: Track claim activity and progress across repositories  
🔔 **Automated Notifications**: Smart nudging system for inactive claims  
⚡ **GitHub Integration**: Seamless webhook integration with GitHub repositories  
🛡️ **Enterprise Security**: JWT authentication, rate limiting, and audit logs  
📈 **Analytics Dashboard**: Comprehensive insights and reporting  

**Authentication**: Most endpoints require JWT tokens. Use `/api/v1/auth/login` to obtain tokens.
**Rate Limiting**: API requests are rate-limited for fair usage.
**Webhooks**: Configure GitHub webhooks to `/api/v1/webhooks/github`.

*Built with FastAPI, PostgreSQL, Redis, and Celery for enterprise reliability.*
    """,
    version="1.0.0",
    docs_url=None,  # We'll create our own docs route
    redoc_url=None,  # We'll create our own ReDoc route
    openapi_url="/openapi.json",
    contact={
        "name": "Cookie Licking Detector Team",
        "email": "support@cookie-detector.com",
        "url": "https://github.com/cookie-licking-detector"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development Server"
        },
        {
            "url": "https://api.cookie-detector.com", 
            "description": "Production Server"
        }
    ],
    tags_metadata=[
        {
            "name": "authentication",
            "description": "User authentication and authorization endpoints"
        },
        {
            "name": "repositories", 
            "description": "Repository management endpoints"
        },
        {
            "name": "claims",
            "description": "Issue claim tracking and management"
        },
        {
            "name": "dashboard",
            "description": "Analytics and reporting endpoints"
        },
        {
            "name": "webhooks",
            "description": "GitHub webhook integration endpoints"
        },
        {
            "name": "system",
            "description": "System health, monitoring, and operational endpoints"
        }
    ],
    lifespan=lifespan,
    swagger_ui_parameters={
        "deepLinking": True,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "operationsSorter": "method",
        "filter": True,
        "showMutatedRequest": True,
        "syntaxHighlight.theme": "tomorrow-night"
    }
)

# Security middleware
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.CORS_ORIGINS
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    return add_security_headers(response)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request metrics."""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    track_request_metrics(request, response, process_time)
    
    return response


# Include all route modules
app.include_router(auth_router, prefix="/api/v1", tags=["authentication"])
app.include_router(user_router, prefix="/api/v1", tags=["users"])
app.include_router(repository_router, prefix="/api/v1", tags=["repositories"])
app.include_router(claim_router, prefix="/api/v1", tags=["claims"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["dashboard"])
app.include_router(webhook_router, prefix="/api/v1", tags=["webhooks"])
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(websocket_router, prefix="/api/v1", tags=["websockets"])


# Static file routes
from fastapi.responses import FileResponse
import os

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve favicon to prevent 404 errors."""
    favicon_path = os.path.join(os.path.dirname(__file__), "..", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    else:
        # Return a 1x1 transparent pixel if favicon doesn't exist
        from fastapi import Response
        return Response(
            content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82',
            media_type="image/png"
        )

@app.get("/apple-touch-icon.png", include_in_schema=False)
@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
async def apple_touch_icon():
    """Serve apple touch icon to prevent 404 errors."""
    # Return a 180x180 transparent PNG for Apple touch icons
    from fastapi import Response
    return Response(
        content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\xb4\x00\x00\x00\xb4\x08\x06\x00\x00\x00\xe8\x05\x08\x8c\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x00\x0bIDATx\x9cc```\x00\x00\x00\x05\x00\x01\r\n0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82',
        media_type="image/png"
    )


@app.get("/redoc.standalone.js", include_in_schema=False)
async def serve_redoc_js():
    """Serve local ReDoc JavaScript file."""
    redoc_js_path = os.path.join(os.path.dirname(__file__), "..", "redoc.standalone.js")
    if os.path.exists(redoc_js_path):
        return FileResponse(redoc_js_path, media_type="application/javascript")
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="ReDoc JavaScript not found")


@app.get("/static/swagger-ui/swagger-ui.css", include_in_schema=False)
async def serve_swagger_css():
    """Serve local Swagger UI CSS file."""
    css_path = os.path.join(os.path.dirname(__file__), "..", "static", "swagger-ui", "swagger-ui.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Swagger UI CSS not found")


@app.get("/static/swagger-ui/swagger-ui-bundle.js", include_in_schema=False)
async def serve_swagger_js():
    """Serve local Swagger UI JavaScript file."""
    js_path = os.path.join(os.path.dirname(__file__), "..", "static", "swagger-ui", "swagger-ui-bundle.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Swagger UI JS not found")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI HTML with local assets."""
    from fastapi.responses import HTMLResponse
    
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <link type="text/css" rel="stylesheet" href="/static/swagger-ui/swagger-ui.css">
    <link rel="shortcut icon" href="/favicon.ico">
    <title>Cookie Licking Detector API - Swagger UI</title>
    <style>
        .swagger-ui .topbar { display: none !important; }
        body { margin: 0; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="/static/swagger-ui/swagger-ui-bundle.js"></script>
    <script>
        const ui = SwaggerUIBundle({
            url: '/openapi.json',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.presets.standalone
            ],
            plugins: [
                SwaggerUIBundle.plugins.DownloadUrl
            ],
            docExpansion: "list",
            operationsSorter: "method",
            filter: true,
            showMutatedRequest: true,
            tryItOutEnabled: true,
            supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
            syntaxHighlight: {
                activated: true,
                theme: "agate"
            }
        });
    </script>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """Simple, reliable ReDoc HTML without complex JavaScript loading."""
    from fastapi.responses import HTMLResponse
    
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Cookie Licking Detector API - Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="shortcut icon" href="/favicon.ico">
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .docs-option {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
        }
        .docs-option h3 {
            color: #343a40;
            margin-top: 0;
        }
        .docs-option a {
            display: inline-block;
            background: #007bff;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            margin: 10px;
        }
        .docs-option a:hover {
            background: #0056b3;
        }
        .swagger-btn {
            background: #85c85c !important;
        }
        .swagger-btn:hover {
            background: #6aa83f !important;
        }
        .redoc-alternative {
            background: #17a2b8;
        }
        .redoc-alternative:hover {
            background: #138496;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍪 Cookie Licking Detector API</h1>
            <h2>Documentation Hub</h2>
            <p>Choose your preferred documentation interface:</p>
        </div>
        
        <div class="docs-option">
            <h3>📋 Swagger UI (Recommended)</h3>
            <p>Interactive API documentation with testing capabilities</p>
            <a href="/docs" class="swagger-btn">Open Swagger UI</a>
        </div>
        
        <div class="docs-option">
            <h3>📖 Alternative ReDoc</h3>
            <p>Try the external ReDoc viewer for a different documentation experience</p>
            <a href="https://redocly.github.io/redoc/?url=http://localhost:8000/openapi.json" target="_blank" class="redoc-alternative">Open External ReDoc</a>
        </div>
        
        <div class="docs-option">
            <h3>📄 OpenAPI Specification</h3>
            <p>Raw OpenAPI JSON specification for developers</p>
            <a href="/openapi.json">View OpenAPI JSON</a>
        </div>
        
        <div class="docs-option">
            <h3>🏥 System Health</h3>
            <p>Check API health and system status</p>
            <a href="/health">Health Check</a>
            <a href="/metrics">Metrics</a>
        </div>
    </div>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)


# Health and system endpoints
@app.get(
    "/",
    tags=["system"],
    summary="API Root Information",
    description="""Returns basic information about the Cookie Licking Detector API including version, status, and available documentation links.
    
    This endpoint is useful for:
    - Health monitoring tools
    - API discovery
    - Version verification
    - Environment identification
    """,
    response_description="API information and status"
)
async def root():
    """Get API root information and status."""
    return {
        "service": "Cookie Licking Detector",
        "version": "1.0.0",
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs_url": "/docs" if settings.DEBUG else "disabled",
        "features": {
            "authentication": "JWT-based authentication",
            "monitoring": "Prometheus metrics" if settings.ENABLE_METRICS else "disabled",
            "webhooks": "GitHub webhook integration",
            "notifications": "Email and GitHub comment notifications",
            "background_tasks": "Celery-based task processing"
        }
    }


@app.get(
    "/health",
    tags=["system"],
    summary="System Health Check",
    description="""Comprehensive health check that validates all critical system components.
    
    **Checks performed:**
    - Database connectivity and performance
    - Redis connection and responsiveness
    - External API availability (GitHub, SendGrid)
    - Background task queue status
    - System resource utilization
    
    **Response codes:**
    - `200 OK`: All systems healthy
    - `503 Service Unavailable`: One or more critical systems unhealthy
    
    This endpoint is designed for:
    - Load balancer health checks
    - Monitoring system integration
    - Automated alerting
    - System diagnostics
    """,
    responses={
        200: {"description": "System is healthy"},
        503: {"description": "System is unhealthy"}
    }
)
async def health_check():
    """Perform comprehensive system health check."""
    health_result = await health_checker.run_all_checks()
    
    status_code = 200 if health_result["status"] == "healthy" else 503
    
    return JSONResponse(
        content=health_result,
        status_code=status_code
    )


@app.get(
    "/metrics",
    tags=["system"],
    summary="Prometheus Metrics",
    description="""Returns Prometheus-formatted metrics for monitoring and observability.
    
    **Metrics included:**
    - HTTP request counts and latency
    - Database connection pool status
    - Background task execution statistics  
    - Business metrics (claims detected, notifications sent)
    - System resource utilization
    
    **Usage:**
    Configure your Prometheus server to scrape this endpoint for comprehensive monitoring.
    
    **Security:** This endpoint may contain sensitive operational data and should be secured appropriately in production.
    """,
    responses={
        200: {"description": "Prometheus metrics data"},
        404: {"description": "Metrics disabled"}
    }
)
async def metrics():
    """Get Prometheus metrics data."""
    if not settings.ENABLE_METRICS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics disabled"
        )
    
    metrics_data = get_metrics()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


@app.get(
    "/version",
    tags=["system"],
    summary="Version Information",
    description="""Returns detailed version and build information about the API.
    
    **Information provided:**
    - Application version and build details
    - Runtime environment information
    - Enabled feature flags
    - Dependency versions
    
    **Use cases:**
    - Deployment verification
    - Debug information gathering
    - Feature availability checking
    - Compatibility verification
    """,
    response_description="Version and build information"
)
async def version_info():
    """Get application version and build information."""
    return {
        "version": "1.0.0",
        "build_date": "2024-01-01",
        "commit": "production",
        "environment": settings.ENVIRONMENT,
        "python_version": "3.13+",
        "api_version": "v1",
        "features": {
            "authentication": True,
            "monitoring": settings.ENABLE_METRICS,
            "webhooks": True,
            "notifications": bool(settings.SENDGRID_API_KEY),
            "github_integration": bool(settings.GITHUB_TOKEN),
            "background_tasks": True,
            "rate_limiting": True,
            "audit_logging": True
        },
        "dependencies": {
            "fastapi": "0.110+",
            "sqlalchemy": "2.0+",
            "celery": "5.3+",
            "redis": "5.0+",
            "postgresql": "13+"
        }
    }


# Global exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Resource not found",
            "message": "The requested resource could not be found",
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Cookie Licking Detector API server")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.RELOAD if settings.ENVIRONMENT == "development" else False,
        workers=1 if settings.ENVIRONMENT == "development" else settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
