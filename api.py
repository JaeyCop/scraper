"""
FastAPI web application for SEO Scraper
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, validator
from typing import List, Dict, Any, Optional
import asyncio
import logging
from datetime import datetime
import uvicorn

from app import SEOScraperApp
from models import KeywordData, ContentData, TechnicalSEOData, CompetitorData
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API requests
class URLAnalysisRequest(BaseModel):
    url: HttpUrl
    keyword: Optional[str] = None

class BulkURLAnalysisRequest(BaseModel):
    urls: List[HttpUrl]
    keywords: Optional[List[str]] = None
    
    @validator('urls')
    def urls_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('URLs list cannot be empty')
        return v

class BulkKeywordAnalysisRequest(BaseModel):
    keywords: List[str]
    
    @validator('keywords')
    def keywords_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('Keywords list cannot be empty')
        return v

class ScheduleTaskRequest(BaseModel):
    keywords: List[str]
    time: str = "09:00"

class CompetitorAnalysisRequest(BaseModel):
    domains: List[str]

# Response models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    components: Dict[str, Any]
    active_alerts: int
    active_tasks: int

# Initialize FastAPI app
app = FastAPI(
    title="SEO Scraper API",
    description="Advanced SEO analysis and web scraping API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global scraper app instance
scraper_app = None

@app.on_event("startup")
async def startup_event():
    """Initialize the scraper app on startup"""
    global scraper_app
    try:
        scraper_app = SEOScraperApp()
        logger.info("SEO Scraper API started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize scraper app: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global scraper_app
    if scraper_app:
        scraper_app.shutdown()
        logger.info("SEO Scraper API shut down successfully")

def get_scraper_app():
    """Dependency to get the scraper app instance"""
    if scraper_app is None:
        raise HTTPException(status_code=500, detail="Scraper app not initialized")
    return scraper_app

# API Endpoints

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "SEO Scraper API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(app: SEOScraperApp = Depends(get_scraper_app)):
    """Health check endpoint"""
    try:
        status = app.get_system_status()
        return HealthResponse(
            status=status["health"]["overall_status"],
            timestamp=datetime.now(),
            components=status["health"]["components"],
            active_alerts=status["active_alerts"],
            active_tasks=status["active_tasks"]
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/url", response_model=APIResponse)
async def analyze_url(
    request: URLAnalysisRequest,
    app: SEOScraperApp = Depends(get_scraper_app)
):
    """Analyze a single URL"""
    try:
        logger.info(f"Analyzing URL: {request.url}")
        result = app.analyze_url(str(request.url), request.keyword)
        
        return APIResponse(
            success=result.get("success", False),
            message="URL analysis completed" if result.get("success") else "URL analysis failed",
            data=result,
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error analyzing URL {request.url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/urls/bulk", response_model=APIResponse)
async def analyze_urls_bulk(
    request: BulkURLAnalysisRequest,
    background_tasks: BackgroundTasks,
    app: SEOScraperApp = Depends(get_scraper_app)
):
    """Analyze multiple URLs concurrently"""
    try:
        logger.info(f"Starting bulk analysis for {len(request.urls)} URLs")
        
        # Convert HttpUrl objects to strings
        urls = [str(url) for url in request.urls]
        
        # Run analysis
        result = await app.analyze_urls_bulk(urls, request.keywords)
        
        return APIResponse(
            success=result.get("success", False),
            message=f"Bulk analysis completed: {result.get('urls_processed', 0)}/{len(urls)} URLs processed",
            data=result,
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error in bulk URL analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/keywords/bulk", response_model=APIResponse)
async def analyze_keywords_bulk(
    request: BulkKeywordAnalysisRequest,
    app: SEOScraperApp = Depends(get_scraper_app)
):
    """Analyze multiple keywords concurrently"""
    try:
        logger.info(f"Starting bulk keyword analysis for {len(request.keywords)} keywords")
        
        result = await app.analyze_keywords_bulk(request.keywords)
        
        return APIResponse(
            success=result.get("success", False),
            message=f"Bulk keyword analysis completed: {result.get('keywords_processed', 0)}/{len(request.keywords)} keywords processed",
            data=result,
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error in bulk keyword analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedule/daily", response_model=APIResponse)
async def schedule_daily_analysis(
    request: ScheduleTaskRequest,
    app: SEOScraperApp = Depends(get_scraper_app)
):
    """Schedule daily keyword analysis"""
    try:
        task_id = app.schedule_daily_analysis(request.keywords, request.time)
        
        return APIResponse(
            success=True,
            message=f"Daily analysis scheduled successfully",
            data={"task_id": task_id, "keywords": request.keywords, "time": request.time},
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error scheduling daily analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedule/competitors", response_model=APIResponse)
async def schedule_competitor_monitoring(
    request: CompetitorAnalysisRequest,
    app: SEOScraperApp = Depends(get_scraper_app)
):
    """Schedule weekly competitor monitoring"""
    try:
        task_ids = app.schedule_competitor_monitoring(request.domains)
        
        return APIResponse(
            success=True,
            message=f"Competitor monitoring scheduled for {len(request.domains)} domains",
            data={"task_ids": task_ids, "domains": request.domains},
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error scheduling competitor monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks", response_model=APIResponse)
async def get_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    app: SEOScraperApp = Depends(get_scraper_app)
):
    """Get all scheduled tasks"""
    try:
        tasks = app.task_manager.get_all_tasks()
        
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(tasks)} tasks",
            data={"tasks": tasks, "total": len(tasks)},
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error retrieving tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/tasks/{task_id}", response_model=APIResponse)
async def cancel_task(
    task_id: str,
    app: SEOScraperApp = Depends(get_scraper_app)
):
    """Cancel a scheduled task"""
    try:
        success = app.task_manager.cancel_task(task_id)
        
        if success:
            return APIResponse(
                success=True,
                message=f"Task {task_id} cancelled successfully",
                data={"task_id": task_id},
                timestamp=datetime.now()
            )
        else:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics", response_model=APIResponse)
async def get_metrics(app: SEOScraperApp = Depends(get_scraper_app)):
    """Get system metrics and performance data"""
    try:
        metrics = app.metrics_collector.get_metrics()
        
        return APIResponse(
            success=True,
            message="Metrics retrieved successfully",
            data={"metrics": metrics},
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts", response_model=APIResponse)
async def get_alerts(
    active_only: bool = Query(True, description="Get only active alerts"),
    app: SEOScraperApp = Depends(get_scraper_app)
):
    """Get system alerts"""
    try:
        if active_only:
            alerts = app.alert_manager.get_active_alerts()
        else:
            alerts = app.alert_manager.get_all_alerts()
        
        # Convert alerts to dict format
        alert_data = [
            {
                "id": alert.id,
                "timestamp": alert.timestamp,
                "level": alert.level,
                "category": alert.category,
                "message": alert.message,
                "source": alert.source,
                "resolved": alert.resolved
            }
            for alert in alerts
        ]
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(alert_data)} alerts",
            data={"alerts": alert_data, "total": len(alert_data)},
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup", response_model=APIResponse)
async def cleanup_data(
    days_to_keep: int = Query(30, description="Number of days of data to keep"),
    app: SEOScraperApp = Depends(get_scraper_app)
):
    """Clean up old data"""
    try:
        app.cleanup_old_data(days_to_keep)
        
        return APIResponse(
            success=True,
            message=f"Data cleanup completed, kept last {days_to_keep} days",
            data={"days_kept": days_to_keep},
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error cleaning up data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Custom exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    # Run the FastAPI app
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
