import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def setup_driver():
    """Set up and return a Chrome WebDriver instance."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Initialize the Chrome WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def is_allowed_domain(url, allowed_domains):
    """Check if the URL's domain is in the allowed domains list."""
    if not allowed_domains:
        return True
    domain = urlparse(url).netloc
    return any(domain.endswith(d) for d in allowed_domains)

def crawl_and_scrape(start_url, max_depth=3, current_depth=0, visited=None, driver=None, allowed_domains=None):
    """
    Crawls a website, scrapes all links that are part of the allowed domains.

    Args:
        start_url: The URL to start crawling from.
        max_depth: The maximum depth to crawl.
        current_depth: The current depth of the crawl (used for recursion).
        visited: A set of visited URLs to avoid duplicates and loops.
        driver: The Selenium WebDriver instance.
        allowed_domains: List of allowed domains to crawl (optional).

    Returns:
        A tuple containing (set of unique URLs, dict of URL to HTML content mappings)
    """
    if visited is None:
        visited = set()

    # Add progress logging
    print(f"\nCrawling: {start_url}")
    print(f"Current depth: {current_depth}/{max_depth}")
    print(f"Total URLs visited so far: {len(visited)}")

    if current_depth > max_depth or start_url in visited:
        return set(), {}

    visited.add(start_url)
    all_links = set()
    content_map = {}

    try:
        print(f"Fetching page content...")
        driver.get(start_url)
        
        # Wait for page load with reduced timeout
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        page_source = driver.page_source
        content_map[start_url] = page_source

        # Parse with BeautifulSoup
        soup = BeautifulSoup(page_source, "html.parser")

        # Find and log number of links
        links = soup.find_all("a")
        print(f"Found {len(links)} links on this page")

        for link in links:
            href = link.get("href")
            if href:
                absolute_url = urljoin(start_url, href)
                parsed_url = urlparse(absolute_url)
                
                # Check if URL is allowed
                if (parsed_url.scheme in ("http", "https") and 
                    is_allowed_domain(absolute_url, allowed_domains)):
                    all_links.add(absolute_url)
                    if current_depth < max_depth:
                        new_links, new_content = crawl_and_scrape(
                            absolute_url, 
                            max_depth, 
                            current_depth + 1, 
                            visited, 
                            driver,
                            allowed_domains
                        )
                        all_links.update(new_links)
                        content_map.update(new_content)
                    
    except Exception as e:
        print(f"Error crawling {start_url}: {e}")

    return all_links, content_map

if __name__ == "__main__":
    start_url = input("Enter the starting URL: ")
    max_depth = int(input("Enter maximum crawl depth (default 3): ") or "3")
    allowed_domains_input = input("Enter allowed domains (comma-separated, press Enter for same domain only): ")
    
    allowed_domains = None
    if allowed_domains_input:
        allowed_domains = [d.strip() for d in allowed_domains_input.split(',')]
    else:
        allowed_domains = [urlparse(start_url).netloc]
    
    output_filename = input("Enter the output filename for links (e.g., links.txt): ")
    content_filename = input("Enter the filename for combined content (e.g., all_content.txt): ")

    try:
        # Initialize the WebDriver
        driver = setup_driver()
        
        scraped_links, content_map = crawl_and_scrape(
            start_url,
            max_depth=max_depth,
            driver=driver,
            allowed_domains=allowed_domains
        )

        # Write the links to the main output file
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("\nScraped Links:\n")
            for link in scraped_links:
                f.write(f"{link}\n")
            f.write(f"\nTotal unique links found: {len(scraped_links)}")

        # Process all HTML content and combine into one text file
        with open(content_filename, "w", encoding="utf-8") as f:
            f.write(f"Combined content from {len(content_map)} pages\n")
            f.write("=" * 80 + "\n\n")
            
            for url, html_content in content_map.items():
                try:
                    # Parse HTML and extract text
                    soup = BeautifulSoup(html_content, "html.parser")
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                        
                    # Get text and clean it up
                    text = soup.get_text()
                    # Break into lines and remove leading/trailing space on each
                    lines = (line.strip() for line in text.splitlines())
                    # Break multi-headlines into a line each
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    # Drop blank lines
                    text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    # Write the URL and content with clear separation
                    f.write(f"URL: {url}\n")
                    f.write("-" * 80 + "\n")
                    f.write(text)
                    f.write("\n\n")
                    f.write("=" * 80 + "\n\n")
                    
                except Exception as e:
                    print(f"Error processing content for {url}: {e}")

        print(f"Links written to: {output_filename}")
        print(f"Combined content written to: {content_filename}")

    except Exception as e:
        print(f"A general error occurred: {e}")
    finally:
        # Make sure to close the browser
        if 'driver' in locals():
            driver.quit()