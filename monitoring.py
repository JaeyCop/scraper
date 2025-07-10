"""
Advanced monitoring and logging system for SEO Scraper
"""
import logging
import time
import os
import json
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from threading import Lock
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import config
from utils import PerformanceMonitor

# Configure logging with multiple handlers
def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """Setup comprehensive logging system"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.FileHandler(
        os.path.join(log_dir, 'scraper.log'),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Error log handler
    error_handler = logging.FileHandler(
        os.path.join(log_dir, 'errors.log'),
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Performance log handler
    perf_handler = logging.FileHandler(
        os.path.join(log_dir, 'performance.log'),
        encoding='utf-8'
    )
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(simple_formatter)
    
    # Create performance logger
    perf_logger = logging.getLogger('performance')
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)
    perf_logger.propagate = False
    
    return root_logger

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    active_tasks: int
    database_size: float

@dataclass
class ScrapingMetrics:
    """Scraping-specific metrics"""
    timestamp: str
    urls_processed: int
    keywords_analyzed: int
    errors_count: int
    success_rate: float
    avg_response_time: float
    cache_hit_rate: float

@dataclass
class Alert:
    """System alert"""
    id: str
    timestamp: str
    level: str  # 'info', 'warning', 'error', 'critical'
    category: str  # 'system', 'scraping', 'task', 'security'
    message: str
    source: str
    resolved: bool = False
    resolved_at: Optional[str] = None

class MetricsCollector:
    """Collects and stores system and application metrics"""
    
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        self.metrics_lock = Lock()
        self.system_metrics: List[SystemMetrics] = []
        self.scraping_metrics: List[ScrapingMetrics] = []
        self.performance_monitor = PerformanceMonitor()
        self.collection_interval = 60  # seconds
        self.is_collecting = False
        self.collection_thread = None
        
        # Metrics counters
        self.urls_processed = 0
        self.keywords_analyzed = 0
        self.errors_count = 0
        self.response_times: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
        
        self.setup_metrics_storage()
    
    def setup_metrics_storage(self):
        """Initialize metrics storage"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # System metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                network_io TEXT,
                active_tasks INTEGER,
                database_size REAL
            )
        ''')
        
        # Scraping metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_metrics (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                urls_processed INTEGER,
                keywords_analyzed INTEGER,
                errors_count INTEGER,
                success_rate REAL,
                avg_response_time REAL,
                cache_hit_rate REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_collection(self):
        """Start metrics collection"""
        if self.is_collecting:
            return
        
        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collect_metrics_loop, daemon=True)
        self.collection_thread.start()
        logging.info("Metrics collection started")
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logging.info("Metrics collection stopped")
    
    def _collect_metrics_loop(self):
        """Main metrics collection loop"""
        while self.is_collecting:
            try:
                self._collect_system_metrics()
                self._collect_scraping_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logging.error(f"Error collecting metrics: {e}")
                time.sleep(5)
    
    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv
            }
            
            # Database size
            database_size = 0
            if os.path.exists(config.db_path):
                database_size = os.path.getsize(config.db_path) / (1024 * 1024)  # MB
            
            metrics = SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                active_tasks=threading.active_count(),
                database_size=database_size
            )
            
            with self.metrics_lock:
                self.system_metrics.append(metrics)
                # Keep only last 100 entries in memory
                if len(self.system_metrics) > 100:
                    self.system_metrics.pop(0)
            
            self._save_system_metrics(metrics)
            
        except Exception as e:
            logging.error(f"Error collecting system metrics: {e}")
    
    def _collect_scraping_metrics(self):
        """Collect scraping performance metrics"""
        try:
            with self.metrics_lock:
                # Calculate success rate
                total_requests = self.urls_processed + self.keywords_analyzed
                success_rate = ((total_requests - self.errors_count) / total_requests * 100) if total_requests > 0 else 100
                
                # Calculate average response time
                avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
                
                # Calculate cache hit rate
                total_cache_requests = self.cache_hits + self.cache_misses
                cache_hit_rate = (self.cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0
                
                metrics = ScrapingMetrics(
                    timestamp=datetime.now().isoformat(),
                    urls_processed=self.urls_processed,
                    keywords_analyzed=self.keywords_analyzed,
                    errors_count=self.errors_count,
                    success_rate=success_rate,
                    avg_response_time=avg_response_time,
                    cache_hit_rate=cache_hit_rate
                )
                
                self.scraping_metrics.append(metrics)
                # Keep only last 100 entries in memory
                if len(self.scraping_metrics) > 100:
                    self.scraping_metrics.pop(0)
                
                # Reset counters (keep running totals in database)
                self.response_times.clear()
            
            self._save_scraping_metrics(metrics)
            
        except Exception as e:
            logging.error(f"Error collecting scraping metrics: {e}")
    
    def _save_system_metrics(self, metrics: SystemMetrics):
        """Save system metrics to database"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_metrics 
                (timestamp, cpu_usage, memory_usage, disk_usage, network_io, active_tasks, database_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp,
                metrics.cpu_usage,
                metrics.memory_usage,
                metrics.disk_usage,
                json.dumps(metrics.network_io),
                metrics.active_tasks,
                metrics.database_size
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error saving system metrics: {e}")
    
    def _save_scraping_metrics(self, metrics: ScrapingMetrics):
        """Save scraping metrics to database"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO scraping_metrics 
                (timestamp, urls_processed, keywords_analyzed, errors_count, success_rate, avg_response_time, cache_hit_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp,
                metrics.urls_processed,
                metrics.keywords_analyzed,
                metrics.errors_count,
                metrics.success_rate,
                metrics.avg_response_time,
                metrics.cache_hit_rate
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error saving scraping metrics: {e}")
    
    # Methods to record events
    def record_url_processed(self, response_time: float):
        """Record a URL processing event"""
        with self.metrics_lock:
            self.urls_processed += 1
            self.response_times.append(response_time)
    
    def record_keyword_analyzed(self, response_time: float):
        """Record a keyword analysis event"""
        with self.metrics_lock:
            self.keywords_analyzed += 1
            self.response_times.append(response_time)
    
    def record_error(self):
        """Record an error event"""
        with self.metrics_lock:
            self.errors_count += 1
    
    def record_cache_hit(self):
        """Record a cache hit"""
        with self.metrics_lock:
            self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss"""
        with self.metrics_lock:
            self.cache_misses += 1

class AlertManager:
    """Manages system alerts and notifications"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alerts: List[Alert] = []
        self.alert_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'error_rate': 10.0,  # percentage
            'success_rate_low': 90.0  # below this is bad
        }
        self.is_monitoring = False
        self.monitoring_thread = None
        self.email_config = None
    
    def configure_email_alerts(self, smtp_server: str, smtp_port: int, 
                             username: str, password: str, recipients: List[str]):
        """Configure email notifications"""
        self.email_config = {
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password,
            'recipients': recipients
        }
    
    def start_monitoring(self):
        """Start alert monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitor_alerts, daemon=True)
        self.monitoring_thread.start()
        logging.info("Alert monitoring started")
    
    def stop_monitoring(self):
        """Stop alert monitoring"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logging.info("Alert monitoring stopped")
    
    def _monitor_alerts(self):
        """Main alert monitoring loop"""
        while self.is_monitoring:
            try:
                self._check_system_alerts()
                self._check_scraping_alerts()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logging.error(f"Error in alert monitoring: {e}")
                time.sleep(5)
    
    def _check_system_alerts(self):
        """Check for system-related alerts"""
        if not self.metrics_collector.system_metrics:
            return
        
        latest_metrics = self.metrics_collector.system_metrics[-1]
        
        # Check CPU usage
        if latest_metrics.cpu_usage > self.alert_thresholds['cpu_usage']:
            self._create_alert(
                'warning',
                'system',
                f"High CPU usage: {latest_metrics.cpu_usage:.1f}%",
                'metrics_collector'
            )
        
        # Check memory usage
        if latest_metrics.memory_usage > self.alert_thresholds['memory_usage']:
            self._create_alert(
                'warning',
                'system',
                f"High memory usage: {latest_metrics.memory_usage:.1f}%",
                'metrics_collector'
            )
        
        # Check disk usage
        if latest_metrics.disk_usage > self.alert_thresholds['disk_usage']:
            self._create_alert(
                'critical',
                'system',
                f"High disk usage: {latest_metrics.disk_usage:.1f}%",
                'metrics_collector'
            )
    
    def _check_scraping_alerts(self):
        """Check for scraping-related alerts"""
        if not self.metrics_collector.scraping_metrics:
            return
        
        latest_metrics = self.metrics_collector.scraping_metrics[-1]
        
        # Check success rate
        if latest_metrics.success_rate < self.alert_thresholds['success_rate_low']:
            self._create_alert(
                'error',
                'scraping',
                f"Low success rate: {latest_metrics.success_rate:.1f}%",
                'metrics_collector'
            )
        
        # Check error rate
        total_requests = latest_metrics.urls_processed + latest_metrics.keywords_analyzed
        if total_requests > 0:
            error_rate = (latest_metrics.errors_count / total_requests) * 100
            if error_rate > self.alert_thresholds['error_rate']:
                self._create_alert(
                    'error',
                    'scraping',
                    f"High error rate: {error_rate:.1f}%",
                    'metrics_collector'
                )
    
    def _create_alert(self, level: str, category: str, message: str, source: str):
        """Create a new alert"""
        # Check if similar alert already exists and is unresolved
        for alert in self.alerts:
            if (alert.category == category and 
                alert.message == message and 
                not alert.resolved):
                return  # Don't create duplicate alerts
        
        alert = Alert(
            id=f"alert_{int(time.time())}_{len(self.alerts)}",
            timestamp=datetime.now().isoformat(),
            level=level,
            category=category,
            message=message,
            source=source
        )
        
        self.alerts.append(alert)
        
        # Log the alert
        log_level = getattr(logging, level.upper(), logging.INFO)
        logging.log(log_level, f"ALERT [{category}]: {message}")
        
        # Send email notification if configured
        if self.email_config and level in ['error', 'critical']:
            self._send_email_alert(alert)
    
    def _send_email_alert(self, alert: Alert):
        """Send email notification for alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['username']
            msg['To'] = ', '.join(self.email_config['recipients'])
            msg['Subject'] = f"SEO Scraper Alert - {alert.level.upper()}"
            
            body = f"""
            Alert Details:
            - Level: {alert.level.upper()}
            - Category: {alert.category}
            - Message: {alert.message}
            - Source: {alert.source}
            - Timestamp: {alert.timestamp}
            
            Please check the scraper system.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            text = msg.as_string()
            server.sendmail(self.email_config['username'], self.email_config['recipients'], text)
            server.quit()
            
            logging.info(f"Email alert sent for: {alert.message}")
            
        except Exception as e:
            logging.error(f"Failed to send email alert: {e}")
    
    def resolve_alert(self, alert_id: str):
        """Mark an alert as resolved"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now().isoformat()
                logging.info(f"Alert resolved: {alert.message}")
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all unresolved alerts"""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def get_all_alerts(self) -> List[Alert]:
        """Get all alerts"""
        return self.alerts.copy()

class HealthChecker:
    """System health checker"""
    
    def __init__(self, metrics_collector: MetricsCollector, alert_manager: AlertManager):
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
    
    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {}
        }
        
        # Check system resources
        system_health = self._check_system_health()
        health_status['components']['system'] = system_health
        
        # Check scraping performance
        scraping_health = self._check_scraping_health()
        health_status['components']['scraping'] = scraping_health
        
        # Check database
        database_health = self._check_database_health()
        health_status['components']['database'] = database_health
        
        # Check alerts
        alerts_health = self._check_alerts_health()
        health_status['components']['alerts'] = alerts_health
        
        # Determine overall status
        component_statuses = [comp['status'] for comp in health_status['components'].values()]
        if 'critical' in component_statuses:
            health_status['overall_status'] = 'critical'
        elif 'warning' in component_statuses:
            health_status['overall_status'] = 'warning'
        
        return health_status
    
    def _check_system_health(self) -> Dict[str, Any]:
        """Check system resource health"""
        if not self.metrics_collector.system_metrics:
            return {'status': 'unknown', 'message': 'No metrics available'}
        
        latest = self.metrics_collector.system_metrics[-1]
        
        status = 'healthy'
        issues = []
        
        if latest.cpu_usage > 90:
            status = 'critical'
            issues.append(f"CPU usage critical: {latest.cpu_usage:.1f}%")
        elif latest.cpu_usage > 80:
            status = 'warning'
            issues.append(f"CPU usage high: {latest.cpu_usage:.1f}%")
        
        if latest.memory_usage > 95:
            status = 'critical'
            issues.append(f"Memory usage critical: {latest.memory_usage:.1f}%")
        elif latest.memory_usage > 85:
            if status != 'critical':
                status = 'warning'
            issues.append(f"Memory usage high: {latest.memory_usage:.1f}%")
        
        return {
            'status': status,
            'cpu_usage': latest.cpu_usage,
            'memory_usage': latest.memory_usage,
            'disk_usage': latest.disk_usage,
            'issues': issues
        }
    
    def _check_scraping_health(self) -> Dict[str, Any]:
        """Check scraping performance health"""
        if not self.metrics_collector.scraping_metrics:
            return {'status': 'unknown', 'message': 'No metrics available'}
        
        latest = self.metrics_collector.scraping_metrics[-1]
        
        status = 'healthy'
        issues = []
        
        if latest.success_rate < 80:
            status = 'critical'
            issues.append(f"Success rate critical: {latest.success_rate:.1f}%")
        elif latest.success_rate < 90:
            status = 'warning'
            issues.append(f"Success rate low: {latest.success_rate:.1f}%")
        
        if latest.avg_response_time > 10:
            if status != 'critical':
                status = 'warning'
            issues.append(f"Slow response time: {latest.avg_response_time:.1f}s")
        
        return {
            'status': status,
            'success_rate': latest.success_rate,
            'avg_response_time': latest.avg_response_time,
            'cache_hit_rate': latest.cache_hit_rate,
            'issues': issues
        }
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            import sqlite3
            
            # Test database connection
            conn = sqlite3.connect(config.db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            
            # Check database size
            db_size = os.path.getsize(config.db_path) / (1024 * 1024)  # MB
            
            status = 'healthy'
            issues = []
            
            if db_size > 1000:  # 1GB
                status = 'warning'
                issues.append(f"Database size large: {db_size:.1f}MB")
            
            return {
                'status': status,
                'size_mb': db_size,
                'issues': issues
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'issues': [f"Database error: {str(e)}"]
            }
    
    def _check_alerts_health(self) -> Dict[str, Any]:
        """Check alerts health"""
        active_alerts = self.alert_manager.get_active_alerts()
        
        critical_alerts = [a for a in active_alerts if a.level == 'critical']
        error_alerts = [a for a in active_alerts if a.level == 'error']
        
        status = 'healthy'
        if critical_alerts:
            status = 'critical'
        elif error_alerts:
            status = 'warning'
        
        return {
            'status': status,
            'active_alerts': len(active_alerts),
            'critical_alerts': len(critical_alerts),
            'error_alerts': len(error_alerts)
        }

# Initialize monitoring system
def init_monitoring():
    """Initialize the complete monitoring system"""
    setup_logging()
    
    metrics_collector = MetricsCollector()
    alert_manager = AlertManager(metrics_collector)
    health_checker = HealthChecker(metrics_collector, alert_manager)
    
    # Start monitoring
    metrics_collector.start_collection()
    alert_manager.start_monitoring()
    
    logging.info("Monitoring system initialized and started")
    
    return metrics_collector, alert_manager, health_checker

if __name__ == "__main__":
    # Example usage
    metrics_collector, alert_manager, health_checker = init_monitoring()
    
    try:
        # Simulate some activity
        for i in range(10):
            metrics_collector.record_url_processed(1.5)
            metrics_collector.record_keyword_analyzed(2.0)
            time.sleep(2)
        
        # Check health
        health = health_checker.check_health()
        print(f"System health: {health['overall_status']}")
        
        # Wait a bit more
        time.sleep(30)
        
    finally:
        metrics_collector.stop_collection()
        alert_manager.stop_monitoring()
