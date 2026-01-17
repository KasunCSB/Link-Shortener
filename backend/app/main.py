from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
import logging
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database import engine, Base, get_db
from .routes import router as api_router, get_client_ip
from .services import LinkService
from .redis_client import RedisService
from .models import Link

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Link Shortener API...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    # Sync codes from database to Redis
    try:
        db = next(get_db())
        codes = [link.short_code for link in db.query(Link.short_code).filter(Link.is_active == True).all()]
        RedisService.sync_codes_from_db(codes)
        logger.info(f"Synced {len(codes)} codes to Redis")
        db.close()
    except Exception as e:
        logger.error(f"Failed to sync codes to Redis: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Link Shortener API...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A fast, modern link shortening service",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api", tags=["API"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = True
    redis_healthy = RedisService.health_check()
    
    try:
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_healthy = False
    
    status = "healthy" if (db_healthy and redis_healthy) else "degraded"
    
    return {
        "status": status,
        "database": db_healthy,
        "redis": redis_healthy,
        "version": settings.APP_VERSION
    }


@app.get("/{code}")
async def redirect_to_url(
    code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Redirect short code to original URL."""
    # Skip static files and API routes
    if code in ["favicon.ico", "robots.txt", "sitemap.xml"]:
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    
    code_lower = code.lower()
    
    # Get original URL
    url = LinkService.get_original_url(db, code_lower)
    
    if not url:
        # Return 404 JSON for API clients, redirect for browsers
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url=f"/?error=notfound&code={code}", status_code=302)
        return JSONResponse(status_code=404, content={"error": "Link not found or expired"})
    
    # Record click asynchronously (non-blocking)
    link = LinkService.get_link_by_code(db, code_lower)
    if link:
        try:
            LinkService.record_click(
                db=db,
                link=link,
                ip=get_client_ip(request),
                country=request.headers.get("CF-IPCountry"),
                referer=request.headers.get("Referer"),
                user_agent=request.headers.get("User-Agent")
            )
        except Exception as e:
            logger.error(f"Failed to record click: {e}")
    
    # 301 for permanent redirect (better for SEO), 302 for temporary
    return RedirectResponse(url=url, status_code=301)


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Handle 404 specially, otherwise return JSON using the exception's status code
    if getattr(exc, "status_code", None) == 404:
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/?error=notfound", status_code=302)
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return JSONResponse(status_code=exc.status_code or 500, content={"detail": exc.detail or "HTTP error"})


@app.exception_handler(Exception)
async def server_error_handler(request: Request, exc: Exception):
    logger.error(f"Server error: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
