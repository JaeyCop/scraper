"""
Main application for SEO Scraper - Orchestrates all components
"""
import argparse
import sys
import time
import logging
from typing import List, Dict, Any
import json

from config import config
from database import DatabaseManager
from seo_scraper import SEOScraper
from scheduler import TaskManager
from monitoring import init_monitoring, setup_logging
from async_scraper import AsyncContentAnalyzer, AsyncBrowserManager, AsyncKeywordAnalyzer

logger = logging.getLogger(__name__)

class SEOScraperApp:
    """Main SEO Scraper application"""
    
    def __init__(self):
        # Initialize logging first
        setup_logging()
        
        # Initialize core components
        self.db_manager = DatabaseManager(config.db_path)
        self.scraper = SEOScraper(config.db_path)
        self.task_manager = TaskManager(self.db_manager)
        
        # Initialize monitoring
        self.metrics_collector, self.alert_manager, self.health_checker = init_monitoring()
        
        # Configure email alerts if needed
        # self.alert_manager.configure_email_alerts(
        #     smtp_server="smtp.gmail.com",
        #     smtp_port=587,
        #     username="your-email@gmail.com",
        #     password="your-password",
        #     recipients=["admin@yourcompany.com"]
        # )
        
        logger.info("SEO Scraper application initialized")
    
    def analyze_url(self, url: str, keyword: str = None) -> Dict[str, Any]:
        """Analyze a single URL"""
        logger.info(f"Analyzing URL: {url}")
        
        start_time = time.time()
        try:
            result = self.scraper.analyze_comprehensive(url, keyword)
            response_time = time.time() - start_time
            
            if result:
                self.metrics_collector.record_url_processed(response_time)
                logger.info(f"Successfully analyzed {url} in {response_time:.2f}s")
                return {"success": True, "data": result, "response_time": response_time}
            else:
                self.metrics_collector.record_error()
                logger.error(f"Failed to analyze {url}")
                return {"success": False, "error": "Analysis failed"}
                
        except Exception as e:
            self.metrics_collector.record_error()
            logger.error(f"Error analyzing {url}: {e}")
            return {"success": False, "error": str(e)}
    
    async def analyze_urls_bulk(self, urls: List[str], keywords: List[str] = None) -> Dict[str, Any]:
        """Analyze multiple URLs concurrently"""
        logger.info(f"Starting bulk analysis of {len(urls)} URLs")
        
        start_time = time.time()
        try:
            analyzer = AsyncContentAnalyzer(self.db_manager)
            results = await analyzer.analyze_multiple_urls(urls, keywords)
            response_time = time.time() - start_time
            
            # Record metrics
            for _ in results:
                self.metrics_collector.record_url_processed(response_time / len(results))
            
            logger.info(f"Bulk analysis completed: {len(results)}/{len(urls)} URLs processed in {response_time:.2f}s")
            
            return {
                "success": True,
                "urls_processed": len(results),
                "total_urls": len(urls),
                "response_time": response_time,
                "results": results
            }
            
        except Exception as e:
            self.metrics_collector.record_error()
            logger.error(f"Error in bulk URL analysis: {e}")
            return {"success": False, "error": str(e)}
    
    async def analyze_keywords_bulk(self, keywords: List[str]) -> Dict[str, Any]:
        """Analyze multiple keywords concurrently"""
        logger.info(f"Starting bulk keyword analysis for {len(keywords)} keywords")
        
        start_time = time.time()
        try:
            async with AsyncBrowserManager() as browser_manager:
                analyzer = AsyncKeywordAnalyzer(self.db_manager, browser_manager)
                results = await analyzer.analyze_multiple_keywords(keywords)
                response_time = time.time() - start_time
                
                # Record metrics
                for _ in results:
                    self.metrics_collector.record_keyword_analyzed(response_time / len(results))
                
                logger.info(f"Bulk keyword analysis completed: {len(results)}/{len(keywords)} keywords processed in {response_time:.2f}s")
                
                return {
                    "success": True,
                    "keywords_processed": len(results),
                    "total_keywords": len(keywords),
                    "response_time": response_time,
                    "results": results
                }
                
        except Exception as e:
            self.metrics_collector.record_error()
            logger.error(f"Error in bulk keyword analysis: {e}")
            return {"success": False, "error": str(e)}
    
    def schedule_daily_analysis(self, keywords: List[str], time: str = "09:00") -> str:
        """Schedule daily keyword analysis"""
        task_id = self.task_manager.schedule_daily_keyword_analysis(keywords, time)
        logger.info(f"Scheduled daily keyword analysis for {len(keywords)} keywords at {time}")
        return task_id
    
    def schedule_competitor_monitoring(self, domains: List[str]) -> List[str]:
        """Schedule weekly competitor monitoring"""
        task_ids = self.task_manager.schedule_weekly_competitor_analysis(domains)
        logger.info(f"Scheduled weekly competitor analysis for {len(domains)} domains")
        return task_ids
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        health = self.health_checker.check_health()
        active_alerts = self.alert_manager.get_active_alerts()
        tasks = self.task_manager.get_all_tasks()
        
        return {
            "timestamp": health["timestamp"],
            "health": health,
            "active_alerts": len(active_alerts),
            "alerts": [{"level": a.level, "message": a.message} for a in active_alerts[:5]],
            "active_tasks": len([t for t in tasks if t["status"] == "running"]),
            "total_tasks": len(tasks)
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data"""
        logger.info(f"Cleaning up data older than {days_to_keep} days")
        self.db_manager.cleanup_old_data(days_to_keep)
        logger.info("Data cleanup completed")
    
    def shutdown(self):
        """Gracefully shutdown the application"""
        logger.info("Shutting down SEO Scraper application")
        
        try:
            self.task_manager.shutdown()
            self.metrics_collector.stop_collection()
            self.alert_manager.stop_monitoring()
            logger.info("Application shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

def create_cli():
    """Create command line interface"""
    parser = argparse.ArgumentParser(description="SEO Scraper - Advanced web scraping and analysis tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze URL command
    url_parser = subparsers.add_parser("analyze-url", help="Analyze a single URL")
    url_parser.add_argument("url", help="URL to analyze")
    url_parser.add_argument("--keyword", help="Target keyword for analysis")
    
    # Bulk URL analysis command
    bulk_url_parser = subparsers.add_parser("analyze-urls", help="Analyze multiple URLs")
    bulk_url_parser.add_argument("urls", nargs="+", help="URLs to analyze")
    bulk_url_parser.add_argument("--keywords", nargs="*", help="Target keywords")
    
    # Bulk keyword analysis command
    bulk_keyword_parser = subparsers.add_parser("analyze-keywords", help="Analyze multiple keywords")
    bulk_keyword_parser.add_argument("keywords", nargs="+", help="Keywords to analyze")
    
    # Schedule commands
    schedule_parser = subparsers.add_parser("schedule", help="Schedule tasks")
    schedule_subparsers = schedule_parser.add_subparsers(dest="schedule_type")
    
    # Schedule daily analysis
    daily_parser = schedule_subparsers.add_parser("daily", help="Schedule daily keyword analysis")
    daily_parser.add_argument("keywords", nargs="+", help="Keywords to analyze daily")
    daily_parser.add_argument("--time", default="09:00", help="Time to run (HH:MM)")
    
    # Schedule competitor monitoring
    competitor_parser = schedule_subparsers.add_parser("competitors", help="Schedule competitor monitoring")
    competitor_parser.add_argument("domains", nargs="+", help="Competitor domains to monitor")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get system status")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old data")
    cleanup_parser.add_argument("--days", type=int, default=30, help="Days of data to keep")
    
    # Server mode
    server_parser = subparsers.add_parser("server", help="Run in server mode")
    server_parser.add_argument("--port", type=int, default=8000, help="Server port")
    
    return parser

async def main():
    """Main application entry point"""
    parser = create_cli()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    app = SEOScraperApp()
    
    try:
        if args.command == "analyze-url":
            result = app.analyze_url(args.url, args.keyword)
            print(json.dumps(result, indent=2, default=str))
            
        elif args.command == "analyze-urls":
            result = await app.analyze_urls_bulk(args.urls, args.keywords)
            print(json.dumps(result, indent=2, default=str))
            
        elif args.command == "analyze-keywords":
            result = await app.analyze_keywords_bulk(args.keywords)
            print(json.dumps(result, indent=2, default=str))
            
        elif args.command == "schedule":
            if args.schedule_type == "daily":
                task_id = app.schedule_daily_analysis(args.keywords, args.time)
                print(f"Scheduled daily analysis task: {task_id}")
                
            elif args.schedule_type == "competitors":
                task_ids = app.schedule_competitor_monitoring(args.domains)
                print(f"Scheduled competitor monitoring tasks: {task_ids}")
            
        elif args.command == "status":
            status = app.get_system_status()
            print(json.dumps(status, indent=2, default=str))
            
        elif args.command == "cleanup":
            app.cleanup_old_data(args.days)
            print(f"Cleaned up data older than {args.days} days")
            
        elif args.command == "server":
            print(f"Starting server mode on port {args.port}")
            print("Server mode not implemented yet - use the CLI commands for now")
            print("Press Ctrl+C to stop monitoring...")
            
            try:
                while True:
                    status = app.get_system_status()
                    print(f"System Status: {status['health']['overall_status']} - "
                          f"Active Tasks: {status['active_tasks']} - "
                          f"Alerts: {status['active_alerts']}")
                    time.sleep(60)
            except KeyboardInterrupt:
                print("\nStopping server mode...")
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
    finally:
        app.shutdown()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
