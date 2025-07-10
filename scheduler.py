"""
Task scheduling and automation system for SEO Scraper
"""
import asyncio
import schedule
import logging
import threading
import time
import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import pickle
import os

from config import config
from database import DatabaseManager
from seo_scraper import SEOScraper
from async_scraper import AsyncContentAnalyzer, AsyncBrowserManager, AsyncKeywordAnalyzer
from utils import PerformanceMonitor

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ScheduledTask:
    """Represents a scheduled task"""
    id: str
    name: str
    function: str
    args: List[Any]
    kwargs: Dict[str, Any]
    schedule_type: str  # 'once', 'daily', 'weekly', 'monthly', 'interval'
    schedule_value: Any  # time, days, seconds, etc.
    priority: TaskPriority
    status: TaskStatus
    created_at: str
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    max_runs: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 3600  # 1 hour default timeout
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TaskScheduler:
    """Advanced task scheduler with persistence and monitoring"""
    
    def __init__(self, db_manager: DatabaseManager, persist_file: str = "tasks.pkl"):
        self.db_manager = db_manager
        self.persist_file = persist_file
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.scheduler_thread = None
        self.is_running = False
        self.performance_monitor = PerformanceMonitor()
        
        # Task function registry
        self.task_functions = {
            'analyze_url': self._analyze_url_task,
            'analyze_keywords': self._analyze_keywords_task,
            'bulk_url_analysis': self._bulk_url_analysis_task,
            'bulk_keyword_analysis': self._bulk_keyword_analysis_task,
            'competitor_analysis': self._competitor_analysis_task,
            'cleanup_old_data': self._cleanup_old_data_task,
            'generate_report': self._generate_report_task
        }
        
        # Load persisted tasks
        self._load_tasks()
        
        logger.info("Task scheduler initialized")
    
    def add_task(self, task: ScheduledTask) -> str:
        """Add a new scheduled task"""
        self.tasks[task.id] = task
        self._save_tasks()
        
        # Schedule the task based on its type
        self._schedule_task(task)
        
        logger.info(f"Added task '{task.name}' (ID: {task.id})")
        return task.id
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task"""
        if task_id in self.tasks:
            # Cancel if running
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
            
            del self.tasks[task_id]
            self._save_tasks()
            logger.info(f"Removed task {task_id}")
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[ScheduledTask]:
        """List all tasks, optionally filtered by status"""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda x: x.priority.value, reverse=True)
    
    def start_scheduler(self):
        """Start the task scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Task scheduler started")
    
    def stop_scheduler(self):
        """Stop the task scheduler"""
        self.is_running = False
        
        # Cancel all running tasks
        for task in self.running_tasks.values():
            task.cancel()
        self.running_tasks.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Task scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(5)
    
    def _schedule_task(self, task: ScheduledTask):
        """Schedule a task based on its schedule type"""
        if task.schedule_type == 'once':
            schedule.every().day.at(task.schedule_value).do(
                self._execute_task_wrapper, task.id
            ).tag(task.id)
        elif task.schedule_type == 'daily':
            schedule.every().day.at(task.schedule_value).do(
                self._execute_task_wrapper, task.id
            ).tag(task.id)
        elif task.schedule_type == 'weekly':
            schedule.every().week.do(
                self._execute_task_wrapper, task.id
            ).tag(task.id)
        elif task.schedule_type == 'interval':
            schedule.every(task.schedule_value).seconds.do(
                self._execute_task_wrapper, task.id
            ).tag(task.id)
        
        # Update next run time
        job = schedule.get_jobs(task.id)
        if job:
            task.next_run = job[0].next_run.isoformat()
            self._save_tasks()
    
    def _execute_task_wrapper(self, task_id: str):
        """Wrapper to execute tasks asynchronously"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        
        # Check if task should run
        if task.max_runs and task.run_count >= task.max_runs:
            task.status = TaskStatus.COMPLETED
            self._save_tasks()
            return
        
        # Create async task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async_task = loop.create_task(self._execute_task(task_id))
            self.running_tasks[task_id] = async_task
            loop.run_until_complete(async_task)
        except Exception as e:
            logger.error(f"Task execution error for {task_id}: {e}")
        finally:
            loop.close()
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _execute_task(self, task_id: str):
        """Execute a single task"""
        task = self.tasks[task_id]
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now().isoformat()
        self._save_tasks()
        
        self.performance_monitor.start_timer(f"task_{task_id}")
        
        try:
            # Get task function
            if task.function not in self.task_functions:
                raise ValueError(f"Unknown task function: {task.function}")
            
            task_func = self.task_functions[task.function]
            
            # Execute with timeout
            result = await asyncio.wait_for(
                task_func(*task.args, **task.kwargs),
                timeout=task.timeout
            )
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.run_count += 1
            task.retry_count = 0  # Reset retry count on success
            
            logger.info(f"Task '{task.name}' completed successfully")
            
        except asyncio.TimeoutError:
            task.error = f"Task timed out after {task.timeout} seconds"
            task.status = TaskStatus.FAILED
            logger.error(f"Task '{task.name}' timed out")
            
        except Exception as e:
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count <= task.max_retries:
                task.status = TaskStatus.PENDING
                logger.warning(f"Task '{task.name}' failed, retry {task.retry_count}/{task.max_retries}: {e}")
            else:
                task.status = TaskStatus.FAILED
                logger.error(f"Task '{task.name}' failed permanently: {e}")
        
        finally:
            self.performance_monitor.end_timer(f"task_{task_id}")
            self._save_tasks()
    
    # Task function implementations
    async def _analyze_url_task(self, url: str, keyword: str = None) -> Dict[str, Any]:
        """Task to analyze a single URL"""
        scraper = SEOScraper(self.db_manager.db_path)
        result = scraper.analyze_comprehensive(url, keyword)
        return {"url": url, "success": result is not None}
    
    async def _analyze_keywords_task(self, keywords: List[str]) -> Dict[str, Any]:
        """Task to analyze multiple keywords"""
        async with AsyncBrowserManager() as browser_manager:
            analyzer = AsyncKeywordAnalyzer(self.db_manager, browser_manager)
            results = await analyzer.analyze_multiple_keywords(keywords)
            return {"keywords_analyzed": len(results), "total_keywords": len(keywords)}
    
    async def _bulk_url_analysis_task(self, urls: List[str], keywords: List[str] = None) -> Dict[str, Any]:
        """Task for bulk URL analysis"""
        analyzer = AsyncContentAnalyzer(self.db_manager)
        results = await analyzer.analyze_multiple_urls(urls, keywords)
        return {"urls_analyzed": len(results), "total_urls": len(urls)}
    
    async def _bulk_keyword_analysis_task(self, keywords: List[str]) -> Dict[str, Any]:
        """Task for bulk keyword analysis"""
        return await self._analyze_keywords_task(keywords)
    
    async def _competitor_analysis_task(self, domain: str) -> Dict[str, Any]:
        """Task to analyze a competitor"""
        from competitor_analyzer import CompetitorAnalyzer
        analyzer = CompetitorAnalyzer(self.db_manager)
        result = analyzer.analyze_competitors(domain)
        return {"domain": domain, "success": result is not None}
    
    async def _cleanup_old_data_task(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """Task to cleanup old data"""
        self.db_manager.cleanup_old_data(days_to_keep)
        return {"days_kept": days_to_keep, "cleanup_completed": True}
    
    async def _generate_report_task(self, report_type: str = "summary") -> Dict[str, Any]:
        """Task to generate reports"""
        # Placeholder for report generation
        return {"report_type": report_type, "generated": True}
    
    def _save_tasks(self):
        """Save tasks to persistent storage"""
        try:
            with open(self.persist_file, 'wb') as f:
                # Convert tasks to serializable format
                serializable_tasks = {}
                for task_id, task in self.tasks.items():
                    task_dict = asdict(task)
                    # Convert enums to strings
                    task_dict['priority'] = task.priority.value
                    task_dict['status'] = task.status.value
                    serializable_tasks[task_id] = task_dict
                
                pickle.dump(serializable_tasks, f)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")
    
    def _load_tasks(self):
        """Load tasks from persistent storage"""
        if not os.path.exists(self.persist_file):
            return
        
        try:
            with open(self.persist_file, 'rb') as f:
                serializable_tasks = pickle.load(f)
                
                for task_id, task_dict in serializable_tasks.items():
                    # Convert strings back to enums
                    task_dict['priority'] = TaskPriority(task_dict['priority'])
                    task_dict['status'] = TaskStatus(task_dict['status'])
                    
                    task = ScheduledTask(**task_dict)
                    self.tasks[task_id] = task
                    
                    # Reschedule if task is pending
                    if task.status == TaskStatus.PENDING:
                        self._schedule_task(task)
            
            logger.info(f"Loaded {len(self.tasks)} tasks from storage")
            
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")

class TaskManager:
    """High-level task management interface"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.scheduler = TaskScheduler(db_manager)
        self.scheduler.start_scheduler()
    
    def schedule_daily_keyword_analysis(self, keywords: List[str], time: str = "09:00") -> str:
        """Schedule daily keyword analysis"""
        task = ScheduledTask(
            id=f"daily_keywords_{int(datetime.now().timestamp())}",
            name="Daily Keyword Analysis",
            function="analyze_keywords",
            args=[keywords],
            kwargs={},
            schedule_type="daily",
            schedule_value=time,
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        return self.scheduler.add_task(task)
    
    def schedule_weekly_competitor_analysis(self, domains: List[str]) -> List[str]:
        """Schedule weekly competitor analysis for multiple domains"""
        task_ids = []
        for domain in domains:
            task = ScheduledTask(
                id=f"weekly_competitor_{domain}_{int(datetime.now().timestamp())}",
                name=f"Weekly Competitor Analysis - {domain}",
                function="competitor_analysis",
                args=[domain],
                kwargs={},
                schedule_type="weekly",
                schedule_value=None,
                priority=TaskPriority.LOW,
                status=TaskStatus.PENDING,
                created_at=datetime.now().isoformat()
            )
            task_ids.append(self.scheduler.add_task(task))
        return task_ids
    
    def schedule_bulk_url_analysis(self, urls: List[str], keywords: List[str] = None, 
                                 delay_hours: int = 0) -> str:
        """Schedule bulk URL analysis"""
        task = ScheduledTask(
            id=f"bulk_urls_{int(datetime.now().timestamp())}",
            name="Bulk URL Analysis",
            function="bulk_url_analysis",
            args=[urls],
            kwargs={"keywords": keywords},
            schedule_type="once" if delay_hours == 0 else "interval",
            schedule_value=datetime.now().strftime("%H:%M") if delay_hours == 0 else delay_hours * 3600,
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            max_runs=1 if delay_hours == 0 else None
        )
        return self.scheduler.add_task(task)
    
    def schedule_data_cleanup(self, days_to_keep: int = 30, interval_days: int = 7) -> str:
        """Schedule regular data cleanup"""
        task = ScheduledTask(
            id=f"cleanup_{int(datetime.now().timestamp())}",
            name="Data Cleanup",
            function="cleanup_old_data",
            args=[days_to_keep],
            kwargs={},
            schedule_type="interval",
            schedule_value=interval_days * 24 * 3600,  # Convert to seconds
            priority=TaskPriority.LOW,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        return self.scheduler.add_task(task)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status and details"""
        task = self.scheduler.get_task(task_id)
        if task:
            return {
                "id": task.id,
                "name": task.name,
                "status": task.status.value,
                "priority": task.priority.value,
                "created_at": task.created_at,
                "last_run": task.last_run,
                "next_run": task.next_run,
                "run_count": task.run_count,
                "max_runs": task.max_runs,
                "result": task.result,
                "error": task.error
            }
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        return self.scheduler.remove_task(task_id)
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks with their status"""
        tasks = self.scheduler.list_tasks()
        return [self.get_task_status(task.id) for task in tasks]
    
    def shutdown(self):
        """Shutdown the task manager"""
        self.scheduler.stop_scheduler()

# Example usage and testing
def example_task_scheduling():
    """Example of how to use the task scheduling system"""
    from database import DatabaseManager
    
    # Initialize
    db_manager = DatabaseManager("scheduler_test.db")
    task_manager = TaskManager(db_manager)
    
    # Schedule various tasks
    keywords = ["python programming", "web scraping", "seo tools"]
    task_id1 = task_manager.schedule_daily_keyword_analysis(keywords, "10:00")
    print(f"Scheduled daily keyword analysis: {task_id1}")
    
    domains = ["example.com", "competitor.com"]
    task_ids2 = task_manager.schedule_weekly_competitor_analysis(domains)
    print(f"Scheduled weekly competitor analysis: {task_ids2}")
    
    urls = ["https://example.com", "https://test.com"]
    task_id3 = task_manager.schedule_bulk_url_analysis(urls, keywords)
    print(f"Scheduled bulk URL analysis: {task_id3}")
    
    # Schedule cleanup
    task_id4 = task_manager.schedule_data_cleanup(30, 7)
    print(f"Scheduled data cleanup: {task_id4}")
    
    # Check status
    print("\nAll tasks:")
    for task in task_manager.get_all_tasks():
        print(f"- {task['name']}: {task['status']}")
    
    # Let it run for a bit
    time.sleep(10)
    
    # Shutdown
    task_manager.shutdown()

if __name__ == "__main__":
    example_task_scheduling()
