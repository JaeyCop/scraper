"""
Database utilities for SEO Scraper
"""
import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from models import KeywordData, ContentData, CompetitorData, TechnicalSEOData, BacklinkData, SERPData

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations for SEO data"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Initialize SQLite database with complete schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Keywords table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY,
                keyword TEXT UNIQUE,
                search_volume TEXT,
                competition TEXT,
                difficulty_score INTEGER,
                related_keywords TEXT,
                people_also_ask TEXT,
                featured_snippet TEXT,
                local_pack TEXT,
                timestamp TEXT
            )
        ''')
        
        # Content analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE,
                title TEXT,
                meta_description TEXT,
                h1_tags TEXT,
                h2_tags TEXT,
                h3_tags TEXT,
                word_count INTEGER,
                keyword_density TEXT,
                reading_score REAL,
                internal_links TEXT,
                external_links TEXT,
                images TEXT,
                schema_markup TEXT,
                page_speed_score REAL,
                mobile_friendly BOOLEAN,
                timestamp TEXT
            )
        ''')
        
        # Competitors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitors (
                id INTEGER PRIMARY KEY,
                domain TEXT UNIQUE,
                top_pages TEXT,
                meta_titles TEXT,
                common_keywords TEXT,
                content_gaps TEXT,
                backlink_count INTEGER,
                domain_authority INTEGER,
                avg_word_count INTEGER,
                content_types TEXT,
                timestamp TEXT
            )
        ''')
        
        # Technical SEO table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS technical_seo (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE,
                page_title TEXT,
                meta_description TEXT,
                canonical_url TEXT,
                robots_meta TEXT,
                h1_count INTEGER,
                h2_count INTEGER,
                internal_links_count INTEGER,
                external_links_count INTEGER,
                images_without_alt INTEGER,
                page_load_time REAL,
                mobile_friendly BOOLEAN,
                ssl_certificate BOOLEAN,
                structured_data TEXT,
                timestamp TEXT
            )
        ''')
        
        # Backlinks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backlinks (
                id INTEGER PRIMARY KEY,
                target_url TEXT,
                source_url TEXT,
                anchor_text TEXT,
                link_type TEXT,
                domain_authority INTEGER,
                page_authority INTEGER,
                timestamp TEXT
            )
        ''')
        
        # SERP tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS serp_tracking (
                id INTEGER PRIMARY KEY,
                keyword TEXT,
                url TEXT,
                position INTEGER,
                title TEXT,
                description TEXT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database schema initialized successfully")
    
    def get_cached_keyword_data(self, keyword: str, max_age_days: int = 7) -> Optional[KeywordData]:
        """Retrieve cached keyword data if available and fresh"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM keywords WHERE keyword = ?", (keyword,))
            cached = cursor.fetchone()
            
            if cached and (datetime.now() - datetime.fromisoformat(cached[9])).days < max_age_days:
                return KeywordData(
                    keyword=cached[1],
                    search_volume=cached[2],
                    competition=cached[3],
                    difficulty_score=cached[4],
                    related_keywords=json.loads(cached[5]),
                    people_also_ask=json.loads(cached[6]),
                    featured_snippet=cached[7],
                    local_pack=json.loads(cached[8]),
                    timestamp=cached[9]
                )
        finally:
            conn.close()
        
        return None
    
    def save_keyword_data(self, keyword_data: KeywordData):
        """Save keyword research data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO keywords 
                (keyword, search_volume, competition, difficulty_score, related_keywords, 
                 people_also_ask, featured_snippet, local_pack, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                keyword_data.keyword,
                keyword_data.search_volume,
                keyword_data.competition,
                keyword_data.difficulty_score,
                json.dumps(keyword_data.related_keywords),
                json.dumps(keyword_data.people_also_ask),
                keyword_data.featured_snippet,
                json.dumps(keyword_data.local_pack),
                keyword_data.timestamp
            ))
            conn.commit()
            logger.info(f"Saved keyword data for: {keyword_data.keyword}")
        finally:
            conn.close()
    
    def get_cached_content_data(self, url: str, max_age_days: int = 1) -> Optional[ContentData]:
        """Retrieve cached content data if available and fresh"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM content WHERE url = ?", (url,))
            cached = cursor.fetchone()
            
            if cached and (datetime.now() - datetime.fromisoformat(cached[16])).days < max_age_days:
                return ContentData(
                    title=cached[2],
                    url=cached[1],
                    meta_description=cached[3],
                    h1_tags=json.loads(cached[4]),
                    h2_tags=json.loads(cached[5]),
                    h3_tags=json.loads(cached[6]),
                    word_count=cached[7],
                    keyword_density=json.loads(cached[8]),
                    reading_score=cached[9],
                    internal_links=json.loads(cached[10]),
                    external_links=json.loads(cached[11]),
                    images=json.loads(cached[12]),
                    schema_markup=json.loads(cached[13]),
                    page_speed_score=cached[14],
                    mobile_friendly=cached[15],
                    timestamp=cached[16]
                )
        finally:
            conn.close()
        
        return None
    
    def save_content_data(self, content_data: ContentData):
        """Save content analysis data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO content 
                (url, title, meta_description, h1_tags, h2_tags, h3_tags, word_count, 
                 keyword_density, reading_score, internal_links, external_links, images, 
                 schema_markup, page_speed_score, mobile_friendly, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_data.url, content_data.title, content_data.meta_description,
                json.dumps(content_data.h1_tags), json.dumps(content_data.h2_tags),
                json.dumps(content_data.h3_tags), content_data.word_count,
                json.dumps(content_data.keyword_density), content_data.reading_score,
                json.dumps(content_data.internal_links), json.dumps(content_data.external_links),
                json.dumps(content_data.images), json.dumps(content_data.schema_markup),
                content_data.page_speed_score, content_data.mobile_friendly,
                content_data.timestamp
            ))
            conn.commit()
            logger.info(f"Saved content data for: {content_data.url}")
        finally:
            conn.close()
    
    def save_competitor_data(self, competitor_data: CompetitorData):
        """Save competitor analysis data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO competitors
                (domain, top_pages, meta_titles, common_keywords, content_gaps,
                 backlink_count, domain_authority, avg_word_count, content_types, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                competitor_data.domain,
                json.dumps(competitor_data.top_pages),
                json.dumps(competitor_data.meta_titles),
                json.dumps(competitor_data.common_keywords),
                json.dumps(competitor_data.content_gaps),
                competitor_data.backlink_count,
                competitor_data.domain_authority,
                competitor_data.avg_word_count,
                json.dumps(competitor_data.content_types),
                competitor_data.timestamp
            ))
            conn.commit()
            logger.info(f"Saved competitor data for: {competitor_data.domain}")
        finally:
            conn.close()
    
    def save_technical_seo_data(self, technical_data: TechnicalSEOData):
        """Save technical SEO audit data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO technical_seo
                (url, page_title, meta_description, canonical_url, robots_meta,
                 h1_count, h2_count, internal_links_count, external_links_count,
                 images_without_alt, page_load_time, mobile_friendly, ssl_certificate,
                 structured_data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                technical_data.url, technical_data.page_title, technical_data.meta_description,
                technical_data.canonical_url, technical_data.robots_meta,
                technical_data.h1_count, technical_data.h2_count,
                technical_data.internal_links_count, technical_data.external_links_count,
                technical_data.images_without_alt, technical_data.page_load_time,
                technical_data.mobile_friendly, technical_data.ssl_certificate,
                json.dumps(technical_data.structured_data), technical_data.timestamp
            ))
            conn.commit()
            logger.info(f"Saved technical SEO data for: {technical_data.url}")
        finally:
            conn.close()
    
    def save_serp_data(self, serp_data: SERPData):
        """Save SERP tracking data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO serp_tracking
                (keyword, url, position, title, description, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                serp_data.keyword, serp_data.url, serp_data.position,
                serp_data.title, serp_data.description, serp_data.timestamp
            ))
            conn.commit()
            logger.info(f"Saved SERP data for keyword: {serp_data.keyword}")
        finally:
            conn.close()
    
    def get_recent_serp_data(self, keyword: str, max_age_hours: int = 24) -> List[SERPData]:
        """Get recent SERP tracking data for a keyword"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM serp_tracking
                WHERE keyword = ? AND timestamp >= datetime('now', '-{} hours')
                ORDER BY position ASC
            """.format(max_age_hours), (keyword,))
            
            results = cursor.fetchall()
            return [
                SERPData(
                    keyword=row[1],
                    url=row[2],
                    position=row[3],
                    title=row[4],
                    description=row[5],
                    timestamp=row[6]
                ) for row in results
            ]
        finally:
            conn.close()
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Remove old data from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            tables = ['keywords', 'content', 'competitors', 'technical_seo', 'serp_tracking']
            for table in tables:
                cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_date,))
            
            conn.commit()
            logger.info(f"Cleaned up data older than {days_to_keep} days")
        finally:
            conn.close()
