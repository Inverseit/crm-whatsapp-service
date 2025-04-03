import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.api import router
from app.db.base import Base, engine

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# API metadata
API_TITLE = "Beauty Salon Booking API"
API_DESCRIPTION = """
## Beauty Salon Booking API

This API powers a beauty salon booking system with GPT-powered conversations.

### Features

* Multi-platform messaging integration (WhatsApp, Telegram)
* Conversational booking flow
* Booking management
* Conversation history

### Authentication

Some endpoints may require authentication. Use the appropriate headers as specified in the endpoint documentation.
"""
API_VERSION = "1.0.0"

# Create FastAPI app with docs always enabled
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    # Always enable docs regardless of debug mode
    docs_url=None,  # We'll define a custom handler
    redoc_url=None,  # We'll define a custom handler
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Custom OpenAPI schema definition
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        routes=app.routes,
    )
    
    # Add security schemes if needed
    # openapi_schema["components"]["securitySchemes"] = {
    #     "APIKeyHeader": {
    #         "type": "apiKey",
    #         "in": "header",
    #         "name": "X-API-Key"
    #     }
    # }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Set custom OpenAPI function
app.openapi = custom_openapi

# Custom documentation endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{API_TITLE} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{API_TITLE} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.on_event("startup")
async def startup_event():
    """Initialize database connection and messaging webhooks on startup."""
    logger.info("Starting up the application")
    
    # Check if Telegram token is configured and set up webhook
    if settings.telegram_api_token:
        try:
            from app.services.messaging.factory import MessagingFactory
            
            # Use the BACKEND_URL from settings if available
            base_url = settings.SELF_BACKEND_URL
            if base_url:
                # Remove trailing slash if present
                base_url = base_url.rstrip('/')
                
                # Set up Telegram webhook
                telegram_transport = MessagingFactory.get_transport("telegram")
                if telegram_transport and hasattr(telegram_transport, "set_webhook"):
                    webhook_url = f"{base_url}/api/webhooks/telegram"
                    success = await telegram_transport.set_webhook(webhook_url)
                    if success:
                        logger.info(f"Successfully set up Telegram webhook at {webhook_url}")
                    else:
                        logger.warning("Failed to set up Telegram webhook")
                else:
                    logger.warning("Telegram transport not available or doesn't support set_webhook")
            else:
                logger.warning("BACKEND_URL not set, skipping Telegram webhook setup")
        except Exception as e:
            logger.error(f"Error setting up Telegram webhook: {e}", exc_info=True)
    else:
        logger.info("Telegram API token not configured, skipping Telegram webhook setup")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection and clean up messaging resources on shutdown."""
    logger.info("Shutting down the application")
    
    # Clean up Telegram webhook if configured
    if settings.telegram_api_token:
        try:
            from app.services.messaging.factory import MessagingFactory
            
            # Clean up Telegram webhook
            telegram_transport = MessagingFactory.get_transport("telegram")
            if telegram_transport and hasattr(telegram_transport, "delete_webhook"):
                if await telegram_transport.delete_webhook():
                    logger.info("Successfully deleted Telegram webhook")
                else:
                    logger.warning("Failed to delete Telegram webhook")
        except Exception as e:
            logger.error(f"Error cleaning up Telegram webhook: {e}", exc_info=True)

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint for health check."""
    return {"status": "ok", "message": "Beauty Salon Booking API"}

@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "db_connected": True}

if __name__ == "__main__":
    import uvicorn
    from fastapi.openapi.utils import get_openapi
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )