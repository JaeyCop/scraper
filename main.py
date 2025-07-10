"""
Clean main entry point for SEO Scraper
"""
import asyncio
import sys

from app import SEOScraperApp


async def main():
    """Main function to run the SEO Scraper"""
    print("SEO Scraper - Starting...")
    
    scraper_app = SEOScraperApp()

    try:
        # Example usage: analyze a single URL
        print("\n1. Analyzing single URL...")
        result = scraper_app.analyze_url("https://example.com", "example keyword")
        print(f"Result: {result.get('success', False)}")

        # Example batch processing - asynchronously
        print("\n2. Running batch analysis...")
        urls = ["https://httpbin.org/html", "https://httpbin.org/json"]
        keywords = ["example keyword", "test keyword"]
        
        batch_result = await scraper_app.analyze_urls_bulk(urls, keywords)
        print(f"Batch result: {batch_result.get('success', False)}")
        
        # Show system status
        print("\n3. System status:")
        status = scraper_app.get_system_status()
        print(f"Health: {status['health']['overall_status']}")
        print(f"Active tasks: {status['active_tasks']}")
        print(f"Alerts: {status['active_alerts']}")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("\nShutting down...")
        scraper_app.shutdown()
        print("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
