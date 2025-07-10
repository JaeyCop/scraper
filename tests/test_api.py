"""
Tests for FastAPI endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from datetime import datetime

from api import app


class TestAPIEndpoints:
    """Test class for API endpoints"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "SEO Scraper API"
        assert data["version"] == "1.0.0"
        assert "/docs" in data["docs"]
    
    @patch('api.get_scraper_app')
    def test_health_check_healthy(self, mock_get_app):
        """Test health check endpoint when system is healthy"""
        mock_app = Mock()
        mock_app.get_system_status.return_value = {
            "health": {
                "overall_status": "healthy",
                "components": {
                    "database": {"status": "healthy"},
                    "scraping": {"status": "healthy"}
                }
            },
            "active_alerts": 0,
            "active_tasks": 2
        }
        mock_get_app.return_value = mock_app
        
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["active_alerts"] == 0
        assert data["active_tasks"] == 2
    
    @patch('api.get_scraper_app')
    def test_analyze_url_success(self, mock_get_app):
        """Test successful URL analysis"""
        mock_app = Mock()
        mock_app.analyze_url.return_value = {
            "success": True,
            "data": {
                "title": "Test Page",
                "word_count": 500,
                "meta_description": "Test description"
            },
            "response_time": 2.5
        }
        mock_get_app.return_value = mock_app
        
        response = self.client.post(
            "/analyze/url",
            json={"url": "https://example.com", "keyword": "test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "URL analysis completed"
        assert "data" in data
    
    @patch('api.get_scraper_app')
    def test_analyze_url_failure(self, mock_get_app):
        """Test failed URL analysis"""
        mock_app = Mock()
        mock_app.analyze_url.return_value = {
            "success": False,
            "error": "Failed to fetch URL"
        }
        mock_get_app.return_value = mock_app
        
        response = self.client.post(
            "/analyze/url",
            json={"url": "https://invalid-url.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "URL analysis failed"
    
    def test_analyze_url_invalid_input(self):
        """Test URL analysis with invalid input"""
        response = self.client.post(
            "/analyze/url",
            json={"url": "invalid-url"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('api.get_scraper_app')
    async def test_bulk_url_analysis(self, mock_get_app):
        """Test bulk URL analysis"""
        mock_app = Mock()
        mock_app.analyze_urls_bulk.return_value = {
            "success": True,
            "urls_processed": 2,
            "total_urls": 2,
            "response_time": 5.0
        }
        mock_get_app.return_value = mock_app
        
        response = self.client.post(
            "/analyze/urls/bulk",
            json={
                "urls": ["https://example1.com", "https://example2.com"],
                "keywords": ["test", "keyword"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Bulk analysis completed" in data["message"]
    
    def test_bulk_url_analysis_empty_urls(self):
        """Test bulk URL analysis with empty URLs list"""
        response = self.client.post(
            "/analyze/urls/bulk",
            json={"urls": []}
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('api.get_scraper_app')
    async def test_bulk_keyword_analysis(self, mock_get_app):
        """Test bulk keyword analysis"""
        mock_app = Mock()
        mock_app.analyze_keywords_bulk.return_value = {
            "success": True,
            "keywords_processed": 3,
            "total_keywords": 3,
            "response_time": 10.0
        }
        mock_get_app.return_value = mock_app
        
        response = self.client.post(
            "/analyze/keywords/bulk",
            json={"keywords": ["seo", "scraping", "python"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "keywords processed" in data["message"]
    
    @patch('api.get_scraper_app')
    def test_schedule_daily_analysis(self, mock_get_app):
        """Test scheduling daily analysis"""
        mock_app = Mock()
        mock_app.schedule_daily_analysis.return_value = "task_123"
        mock_get_app.return_value = mock_app
        
        response = self.client.post(
            "/schedule/daily",
            json={"keywords": ["seo", "tools"], "time": "09:00"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["task_id"] == "task_123"
    
    @patch('api.get_scraper_app')
    def test_schedule_competitor_monitoring(self, mock_get_app):
        """Test scheduling competitor monitoring"""
        mock_app = Mock()
        mock_app.schedule_competitor_monitoring.return_value = ["task_456", "task_789"]
        mock_get_app.return_value = mock_app
        
        response = self.client.post(
            "/schedule/competitors",
            json={"domains": ["competitor1.com", "competitor2.com"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["task_ids"]) == 2
    
    @patch('api.get_scraper_app')
    def test_get_tasks(self, mock_get_app):
        """Test getting all tasks"""
        mock_app = Mock()
        mock_app.task_manager.get_all_tasks.return_value = [
            {"id": "task_1", "status": "pending", "name": "Test Task 1"},
            {"id": "task_2", "status": "running", "name": "Test Task 2"}
        ]
        mock_get_app.return_value = mock_app
        
        response = self.client.get("/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["tasks"]) == 2
    
    @patch('api.get_scraper_app')
    def test_get_tasks_filtered(self, mock_get_app):
        """Test getting tasks with status filter"""
        mock_app = Mock()
        mock_app.task_manager.get_all_tasks.return_value = [
            {"id": "task_1", "status": "pending", "name": "Test Task 1"},
            {"id": "task_2", "status": "running", "name": "Test Task 2"},
            {"id": "task_3", "status": "pending", "name": "Test Task 3"}
        ]
        mock_get_app.return_value = mock_app
        
        response = self.client.get("/tasks?status=pending")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should return 2 pending tasks
        assert len([t for t in data["data"]["tasks"] if t["status"] == "pending"]) == 2
    
    @patch('api.get_scraper_app')
    def test_cancel_task_success(self, mock_get_app):
        """Test successfully canceling a task"""
        mock_app = Mock()
        mock_app.task_manager.cancel_task.return_value = True
        mock_get_app.return_value = mock_app
        
        response = self.client.delete("/tasks/task_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cancelled successfully" in data["message"]
    
    @patch('api.get_scraper_app')
    def test_cancel_task_not_found(self, mock_get_app):
        """Test canceling a non-existent task"""
        mock_app = Mock()
        mock_app.task_manager.cancel_task.return_value = False
        mock_get_app.return_value = mock_app
        
        response = self.client.delete("/tasks/nonexistent_task")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    @patch('api.get_scraper_app')
    def test_get_metrics(self, mock_get_app):
        """Test getting system metrics"""
        mock_app = Mock()
        mock_app.metrics_collector.get_metrics.return_value = {
            "cpu_usage": 45.2,
            "memory_usage": 62.1,
            "requests_processed": 150
        }
        mock_get_app.return_value = mock_app
        
        response = self.client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "metrics" in data["data"]
    
    @patch('api.get_scraper_app')
    def test_get_alerts(self, mock_get_app):
        """Test getting system alerts"""
        mock_alert = Mock()
        mock_alert.id = "alert_1"
        mock_alert.timestamp = datetime.now().isoformat()
        mock_alert.level = "warning"
        mock_alert.category = "system"
        mock_alert.message = "High CPU usage"
        mock_alert.source = "monitor"
        mock_alert.resolved = False
        
        mock_app = Mock()
        mock_app.alert_manager.get_active_alerts.return_value = [mock_alert]
        mock_get_app.return_value = mock_app
        
        response = self.client.get("/alerts")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["alerts"]) == 1
        assert data["data"]["alerts"][0]["level"] == "warning"
    
    @patch('api.get_scraper_app')
    def test_cleanup_data(self, mock_get_app):
        """Test data cleanup endpoint"""
        mock_app = Mock()
        mock_app.cleanup_old_data.return_value = None
        mock_get_app.return_value = mock_app
        
        response = self.client.post("/cleanup?days_to_keep=30")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cleanup completed" in data["message"]
        assert data["data"]["days_kept"] == 30
    
    @patch('api.get_scraper_app')
    def test_api_exception_handling(self, mock_get_app):
        """Test API exception handling"""
        mock_app = Mock()
        mock_app.analyze_url.side_effect = Exception("Test error")
        mock_get_app.return_value = mock_app
        
        response = self.client.post(
            "/analyze/url",
            json={"url": "https://example.com"}
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "Test error" in data["detail"]
    
    def test_app_not_initialized(self):
        """Test behavior when scraper app is not initialized"""
        with patch('api.scraper_app', None):
            response = self.client.get("/health")
            assert response.status_code == 500
            data = response.json()
            assert "not initialized" in data["detail"]

