"""
Data models for SEO Scraper
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class KeywordData:
    """Data structure for keyword research results"""
    keyword: str
    search_volume: str
    competition: str
    difficulty_score: int
    related_keywords: List[str]
    people_also_ask: List[str]
    featured_snippet: str
    local_pack: List[str]
    timestamp: str

@dataclass
class ContentData:
    """Data structure for content analysis results"""
    title: str
    url: str
    meta_description: str
    h1_tags: List[str]
    h2_tags: List[str]
    h3_tags: List[str]
    word_count: int
    keyword_density: Dict[str, float]
    reading_score: float
    internal_links: List[str]
    external_links: List[str]
    images: List[Dict[str, str]]
    schema_markup: List[str]
    page_speed_score: float
    mobile_friendly: bool
    timestamp: str

@dataclass
class CompetitorData:
    """Data structure for competitor analysis results"""
    domain: str
    top_pages: List[Dict[str, Any]]
    meta_titles: List[str]
    common_keywords: List[str]
    content_gaps: List[str]
    backlink_count: int
    domain_authority: int
    avg_word_count: int
    content_types: Dict[str, int]
    timestamp: str

@dataclass
class TechnicalSEOData:
    """Data structure for technical SEO audit results"""
    url: str
    page_title: str
    meta_description: str
    canonical_url: str
    robots_meta: str
    h1_count: int
    h2_count: int
    internal_links_count: int
    external_links_count: int
    images_without_alt: int
    page_load_time: float
    mobile_friendly: bool
    ssl_certificate: bool
    structured_data: List[str]
    timestamp: str

@dataclass
class BacklinkData:
    """Data structure for backlink analysis results"""
    source_url: str
    anchor_text: str
    link_type: str
    domain_authority: int
    page_authority: int
    timestamp: str

@dataclass
class SERPData:
    """Data structure for SERP tracking results"""
    keyword: str
    url: str
    position: int
    title: str
    description: str
    timestamp: str
