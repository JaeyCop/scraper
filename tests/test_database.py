"""
Tests for database operations
"""
import pytest
from datetime import datetime, timedelta
import json

from database import DatabaseManager
from models import KeywordData, ContentData, TechnicalSEOData, SERPData


class TestDatabaseManager:
    """Test class for database operations"""
    
    def test_database_initialization(self, db_manager):
        """Test database initialization"""
        # Check if tables are created
        conn = db_manager.db_manager.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Check if all required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'keywords', 'content', 'competitors', 'technical_seo', 
            'backlinks', 'serp_tracking'
        ]
        
        for table in expected_tables:
            assert table in tables
        
        conn.close()
    
    def test_save_and_retrieve_keyword_data(self, db_manager, sample_keyword_data):
        """Test saving and retrieving keyword data"""
        # Save keyword data
        db_manager.save_keyword_data(sample_keyword_data)
        
        # Retrieve keyword data
        retrieved_data = db_manager.get_cached_keyword_data(sample_keyword_data.keyword)
        
        assert retrieved_data is not None
        assert retrieved_data.keyword == sample_keyword_data.keyword
        assert retrieved_data.search_volume == sample_keyword_data.search_volume
        assert retrieved_data.competition == sample_keyword_data.competition
        assert retrieved_data.difficulty_score == sample_keyword_data.difficulty_score
        assert retrieved_data.related_keywords == sample_keyword_data.related_keywords
        assert retrieved_data.people_also_ask == sample_keyword_data.people_also_ask
    
    def test_keyword_data_expiration(self, db_manager, sample_keyword_data):
        """Test keyword data expiration"""
        # Modify timestamp to be older than max_age
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
        sample_keyword_data.timestamp = old_timestamp
        
        db_manager.save_keyword_data(sample_keyword_data)
        
        # Should return None for expired data
        retrieved_data = db_manager.get_cached_keyword_data(
            sample_keyword_data.keyword, max_age_days=7
        )
        
        assert retrieved_data is None
    
    def test_save_and_retrieve_content_data(self, db_manager, sample_content_data):
        """Test saving and retrieving content data"""
        # Save content data
        db_manager.save_content_data(sample_content_data)
        
        # Retrieve content data
        retrieved_data = db_manager.get_cached_content_data(sample_content_data.url)
        
        assert retrieved_data is not None
        assert retrieved_data.url == sample_content_data.url
        assert retrieved_data.title == sample_content_data.title
        assert retrieved_data.meta_description == sample_content_data.meta_description
        assert retrieved_data.word_count == sample_content_data.word_count
        assert retrieved_data.keyword_density == sample_content_data.keyword_density
        assert retrieved_data.mobile_friendly == sample_content_data.mobile_friendly
    
    def test_content_data_expiration(self, db_manager, sample_content_data):
        """Test content data expiration"""
        # Modify timestamp to be older than max_age
        old_timestamp = (datetime.now() - timedelta(days=2)).isoformat()
        sample_content_data.timestamp = old_timestamp
        
        db_manager.save_content_data(sample_content_data)
        
        # Should return None for expired data
        retrieved_data = db_manager.get_cached_content_data(
            sample_content_data.url, max_age_days=1
        )
        
        assert retrieved_data is None
    
    def test_save_technical_seo_data(self, db_manager, sample_technical_seo_data):
        """Test saving technical SEO data"""
        # Save technical SEO data
        db_manager.save_technical_seo_data(sample_technical_seo_data)
        
        # Verify data was saved by checking database directly
        import sqlite3
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM technical_seo WHERE url = ?", (sample_technical_seo_data.url,))
        row = cursor.fetchone()
        
        assert row is not None
        assert row[1] == sample_technical_seo_data.url
        assert row[2] == sample_technical_seo_data.page_title
        assert row[7] == sample_technical_seo_data.h1_count
        assert row[8] == sample_technical_seo_data.h2_count
        
        conn.close()
    
    def test_save_serp_data(self, db_manager):
        """Test saving SERP tracking data"""
        serp_data = SERPData(
            keyword="test keyword",
            url="https://example.com",
            position=1,
            title="Test Result",
            description="Test description",
            timestamp=datetime.now().isoformat()
        )
        
        db_manager.save_serp_data(serp_data)
        
        # Verify data was saved
        import sqlite3
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM serp_tracking WHERE keyword = ?", (serp_data.keyword,))
        row = cursor.fetchone()
        
        assert row is not None
        assert row[1] == serp_data.keyword
        assert row[2] == serp_data.url
        assert row[3] == serp_data.position
        
        conn.close()
    
    def test_get_recent_serp_data(self, db_manager):
        """Test retrieving recent SERP data"""
        keyword = "test keyword"
        
        # Save some SERP data
        serp_data1 = SERPData(
            keyword=keyword,
            url="https://example1.com",
            position=1,
            title="Result 1",
            description="Description 1",
            timestamp=datetime.now().isoformat()
        )
        
        serp_data2 = SERPData(
            keyword=keyword,
            url="https://example2.com",
            position=2,
            title="Result 2",
            description="Description 2",
            timestamp=datetime.now().isoformat()
        )
        
        db_manager.save_serp_data(serp_data1)
        db_manager.save_serp_data(serp_data2)
        
        # Retrieve recent data
        recent_data = db_manager.get_recent_serp_data(keyword, max_age_hours=1)
        
        assert len(recent_data) == 2
        assert recent_data[0].position == 1  # Should be ordered by position
        assert recent_data[1].position == 2
    
    def test_cleanup_old_data(self, db_manager, sample_keyword_data, sample_content_data):
        """Test cleanup of old data"""
        # Save some data
        db_manager.save_keyword_data(sample_keyword_data)
        db_manager.save_content_data(sample_content_data)
        
        # Create old data by modifying timestamps
        old_timestamp = (datetime.now() - timedelta(days=40)).isoformat()
        
        import sqlite3
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Insert old data
        cursor.execute("""
            INSERT INTO keywords (keyword, search_volume, competition, difficulty_score, 
                                related_keywords, people_also_ask, featured_snippet, 
                                local_pack, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "old_keyword", "1000", "Low", 20, "[]", "[]", "", "[]", old_timestamp
        ))
        
        cursor.execute("""
            INSERT INTO content (url, title, meta_description, h1_tags, h2_tags, h3_tags,
                               word_count, keyword_density, reading_score, internal_links,
                               external_links, images, schema_markup, page_speed_score,
                               mobile_friendly, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "https://old-example.com", "Old Page", "Old description", "[]", "[]", "[]",
            100, "{}", 50.0, "[]", "[]", "[]", "[]", 70.0, True, old_timestamp
        ))
        
        conn.commit()
        conn.close()
        
        # Verify data exists before cleanup
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM keywords")
        keywords_count_before = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM content")
        content_count_before = cursor.fetchone()[0]
        conn.close()
        
        assert keywords_count_before == 2
        assert content_count_before == 2
        
        # Cleanup old data (keep 30 days)
        db_manager.cleanup_old_data(days_to_keep=30)
        
        # Verify old data was removed
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM keywords")
        keywords_count_after = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM content")
        content_count_after = cursor.fetchone()[0]
        conn.close()
        
        assert keywords_count_after == 1  # Only recent data should remain
        assert content_count_after == 1
    
    def test_duplicate_keyword_handling(self, db_manager, sample_keyword_data):
        """Test handling of duplicate keyword entries"""
        # Save the same keyword data twice
        db_manager.save_keyword_data(sample_keyword_data)
        
        # Modify some data and save again
        sample_keyword_data.search_volume = "10,000-100,000"
        sample_keyword_data.difficulty_score = 80
        db_manager.save_keyword_data(sample_keyword_data)
        
        # Should only have one entry (updated)
        retrieved_data = db_manager.get_cached_keyword_data(sample_keyword_data.keyword)
        
        assert retrieved_data is not None
        assert retrieved_data.search_volume == "10,000-100,000"
        assert retrieved_data.difficulty_score == 80
        
        # Verify only one entry exists in database
        import sqlite3
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM keywords WHERE keyword = ?", (sample_keyword_data.keyword,))
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1
    
    def test_json_serialization_deserialization(self, db_manager):
        """Test JSON serialization/deserialization of complex data"""
        keyword_data = KeywordData(
            keyword="test",
            search_volume="1000",
            competition="Medium",
            difficulty_score=50,
            related_keywords=["keyword1", "keyword2", "keyword3"],
            people_also_ask=["Question 1?", "Question 2?"],
            featured_snippet="Test snippet",
            local_pack=["Business A", "Business B"],
            timestamp=datetime.now().isoformat()
        )
        
        db_manager.save_keyword_data(keyword_data)
        retrieved_data = db_manager.get_cached_keyword_data("test")
        
        assert retrieved_data.related_keywords == ["keyword1", "keyword2", "keyword3"]
        assert retrieved_data.people_also_ask == ["Question 1?", "Question 2?"]
        assert retrieved_data.local_pack == ["Business A", "Business B"]
    
    def test_database_connection_error_handling(self, temp_db):
        """Test handling of database connection errors"""
        # Try to create database manager with invalid path
        import os
        os.chmod(temp_db, 0o000)  # Remove all permissions
        
        try:
            db_manager = DatabaseManager(temp_db)
            # This should handle the error gracefully
            assert True
        except Exception as e:
            # If exception is raised, it should be handled properly
            assert "permission" in str(e).lower() or "access" in str(e).lower()
        finally:
            os.chmod(temp_db, 0o644)  # Restore permissions
