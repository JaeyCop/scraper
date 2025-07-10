# SEO Scraper - Advanced Web Scraping and Analysis Tool

A comprehensive, modular SEO analysis and web scraping tool built with Python, featuring async processing, task scheduling, monitoring, and a FastAPI web interface.

## 🚀 Features

### Core Functionality
- **URL Content Analysis**: Extract and analyze page content, meta tags, headings, links, and more
- **Keyword Research**: Google SERP analysis, related keywords, People Also Ask questions
- **Competitor Analysis**: Analyze competitor websites and identify opportunities
- **Technical SEO Audits**: Check page speed, mobile-friendliness, structured data, etc.

### Advanced Features
- **Async Processing**: Concurrent analysis of multiple URLs and keywords
- **Task Scheduling**: Automated daily/weekly analysis with cron-like scheduling
- **Real-time Monitoring**: System health, performance metrics, and alerts
- **Caching System**: Intelligent caching to avoid redundant requests
- **Rate Limiting**: Respectful scraping with configurable delays
- **FastAPI Interface**: RESTful API with automatic documentation

### Architecture
- **Modular Design**: Separate modules for different functionalities
- **Error Handling**: Comprehensive retry mechanisms and error recovery
- **Data Persistence**: SQLite database with optional PostgreSQL support
- **Containerized**: Docker support for easy deployment

## 📁 Project Structure

```
scraper/
├── api.py                 # FastAPI web application
├── app.py                 # Main application orchestrator
├── main.py                # CLI entry point
├── config.py              # Configuration management
├── models.py              # Data models and schemas
├── database.py            # Database operations
├── utils.py               # Utility functions and decorators
├── browser_utils.py       # Browser management utilities
├── keyword_scraper.py     # Keyword analysis module
├── content_analyzer.py    # Content analysis module
├── competitor_analyzer.py # Competitor analysis module
├── async_scraper.py       # Async scraping utilities
├── scheduler.py           # Task scheduling system
├── monitoring.py          # Monitoring and alerting
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Development setup
└── README.md             # This file
```

## 🛠️ Installation

### Option 1: Local Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd scraper
```

2. **Create virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Install Playwright browsers:**
```bash
playwright install chromium
```

### Option 2: Docker Installation

1. **Using Docker Compose (Recommended):**
```bash
docker-compose up -d
```

2. **Using Docker directly:**
```bash
docker build -t seo-scraper .
docker run -p 8000:8000 seo-scraper
```

## 🚀 Usage

### FastAPI Web Interface

Start the web server:
```bash
python api.py
# or
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Access the API:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Command Line Interface

```bash
# Analyze a single URL
python app.py analyze-url https://example.com --keyword "target keyword"

# Bulk URL analysis
python app.py analyze-urls https://site1.com https://site2.com --keywords "keyword1" "keyword2"

# Bulk keyword analysis
python app.py analyze-keywords "seo tools" "web scraping" "python"

# Schedule daily analysis
python app.py schedule daily "keyword1" "keyword2" --time "09:00"

# Schedule competitor monitoring
python app.py schedule competitors competitor1.com competitor2.com

# Check system status
python app.py status

# Clean up old data
python app.py cleanup --days 30

# Run in server mode (monitoring)
python app.py server --port 8000
```

### Python API

```python
from app import SEOScraperApp
import asyncio

# Initialize the scraper
scraper = SEOScraperApp()

# Analyze a single URL
result = scraper.analyze_url("https://example.com", "target keyword")

# Bulk analysis (async)
urls = ["https://site1.com", "https://site2.com"]
keywords = ["keyword1", "keyword2"]
result = asyncio.run(scraper.analyze_urls_bulk(urls, keywords))

# Schedule tasks
task_id = scraper.schedule_daily_analysis(["keyword1", "keyword2"], "09:00")

# Check system status
status = scraper.get_system_status()

# Cleanup
scraper.shutdown()
```

## 📊 API Endpoints

### Analysis Endpoints
- `POST /analyze/url` - Analyze single URL
- `POST /analyze/urls/bulk` - Bulk URL analysis
- `POST /analyze/keywords/bulk` - Bulk keyword analysis

### Scheduling Endpoints
- `POST /schedule/daily` - Schedule daily keyword analysis
- `POST /schedule/competitors` - Schedule competitor monitoring
- `GET /tasks` - Get all scheduled tasks
- `DELETE /tasks/{task_id}` - Cancel a task

### Monitoring Endpoints
- `GET /health` - System health check
- `GET /metrics` - Performance metrics
- `GET /alerts` - System alerts

### Utility Endpoints
- `POST /cleanup` - Clean up old data

## 🔧 Configuration

### Environment Variables
```bash
# Database
DB_PATH=advanced_seo_data.db

# Browser settings
HEADLESS=true
TIMEOUT=15

# Rate limiting
MIN_DELAY=1.0
MAX_DELAY=3.0

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# Reports
REPORT_DIR=seo_reports
```

### Configuration File
Edit `config.py` to customize:
- Database settings
- Browser configuration
- Rate limiting parameters
- User agent rotation
- Logging preferences

## 📈 Monitoring and Alerts

The system includes comprehensive monitoring:

### Metrics Collected
- **System Metrics**: CPU, memory, disk usage
- **Scraping Metrics**: Success rates, response times, cache hit rates
- **Task Metrics**: Active tasks, completion rates

### Alert Conditions
- High CPU/memory usage
- Low success rates
- High error rates
- System failures

### Email Notifications
Configure email alerts in the application:
```python
scraper_app.alert_manager.configure_email_alerts(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    username="your-email@gmail.com",
    password="your-password",
    recipients=["admin@yourcompany.com"]
)
```

## 🗄️ Database Schema

The application uses SQLite by default with the following tables:
- `keywords` - Keyword research data
- `content` - Content analysis results
- `competitors` - Competitor analysis data
- `technical_seo` - Technical SEO audit results
- `serp_tracking` - SERP position tracking
- `system_metrics` - System performance data
- `scraping_metrics` - Scraping performance data

## 🚦 Rate Limiting and Ethics

The scraper implements responsible scraping practices:
- Configurable delays between requests
- Respect for robots.txt (when implemented)
- User agent rotation
- Request throttling
- Cache-first approach to minimize requests

## 🔒 Security Considerations

- Input validation on all API endpoints
- SQL injection prevention
- XSS protection in API responses
- Configurable CORS settings
- Rate limiting on API endpoints

## 🐛 Troubleshooting

### Common Issues

1. **Playwright Installation Issues:**
```bash
playwright install --force chromium
```

2. **Permission Errors:**
```bash
chmod +x /path/to/scraper
```

3. **Database Lock Errors:**
- Ensure only one instance is running
- Check file permissions

4. **Memory Issues:**
- Reduce batch sizes
- Increase system memory
- Monitor with `/metrics` endpoint

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

Check system health:
```bash
curl http://localhost:8000/health
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Format code
black .

# Lint code
flake8 .
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is designed for legitimate SEO analysis and research purposes. Users are responsible for ensuring compliance with websites' terms of service and applicable laws. Always respect robots.txt files and implement appropriate rate limiting.

## 🤝 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the API documentation at `/docs`
- Review the monitoring dashboard at `/health`

---

**Happy Scraping! 🕷️**
