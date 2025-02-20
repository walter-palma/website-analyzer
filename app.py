from flask import Flask, render_template, request, send_file, jsonify
from bs4 import BeautifulSoup
from MyCrawler import setup_driver, crawl_and_scrape
import os
import threading
from werkzeug.utils import secure_filename
import time
from urllib.parse import urlparse
import re
from ai_analyzer import analyze_website_content, format_analysis_for_download

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'downloads'

# Ensure the downloads directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Store crawling status
crawl_status = {}

def get_safe_filename(url):
    """Extract domain name from URL and create a safe filename."""
    domain = urlparse(url).netloc
    domain = re.sub(r'^www\.', '', domain)
    base_name = domain.split('.')[0]
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', base_name)
    timestamp = str(int(time.time()))
    return safe_name, f"{safe_name}_{timestamp}"

def get_allowed_tags(filters):
    tags = []
    if 'p' in filters:
        tags.extend(['p'])
    if 'h' in filters:
        tags.extend(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    if 'l' in filters:
        tags.extend(['ul', 'ol', 'li'])
    return tags if tags else None

def extract_filtered_content(soup, allowed_tags=None):
    if allowed_tags:
        # Extract only specified tags
        elements = []
        for tag in allowed_tags:
            elements.extend(soup.find_all(tag))
        return '\n'.join(elem.get_text().strip() for elem in elements if elem.get_text().strip())
    else:
        # Extract all text if no tags specified
        return soup.get_text()

def perform_crawl(url, output_filename, content_filename, task_id, max_depth=3, allowed_domains=None, filters=None):
    try:
        crawl_status[task_id] = {
            'status': 'running',
            'progress': 0,
            'message': 'Initializing crawler...'
        }
        
        driver = setup_driver()
        
        try:
            print(f"Starting crawl for URL: {url}")
            
            if allowed_domains:
                allowed_domains = [d.strip() for d in allowed_domains.split(',')]
            else:
                allowed_domains = [urlparse(url).netloc]
            
            crawl_status[task_id]['message'] = 'Starting crawl...'
            
            scraped_links, content_map = crawl_and_scrape(
                url, 
                max_depth=int(max_depth),
                current_depth=0,
                visited=None,
                driver=driver,
                allowed_domains=allowed_domains
            )
            
            print(f"Crawl completed. Found {len(scraped_links)} links and {len(content_map)} pages")
            
            # Save links
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\nScraped Links:\n")
                for link in scraped_links:
                    f.write(f"{link}\n")
                f.write(f"\nTotal unique links found: {len(scraped_links)}")
            
            print(f"Links saved to {output_path}")
            crawl_status[task_id]['message'] = 'Processing content and generating analysis...'

            # Process content and generate AI analysis
            main_content = []
            about_page_content = None
            
            print(f"Processing {len(content_map)} pages for analysis...")
            
            for page_url, html_content in content_map.items():
                print(f"Processing page: {page_url}")
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Remove unwanted elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content based on filters
                if filters:
                    allowed_tags = get_allowed_tags(filters.split(','))
                    text = extract_filtered_content(soup, allowed_tags)
                else:
                    text = soup.get_text()
                
                # Clean up the text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                if text.strip():  # Only add non-empty content
                    print(f"Found {len(text)} characters of content")
                    # Check if this is an about page
                    if 'about' in page_url.lower():
                        print("Found about page content")
                        about_page_content = text
                    else:
                        main_content.append(text)
                else:
                    print("No content found in page")

            # Combine all main content
            combined_content = '\n\n'.join(main_content)
            print(f"Total content length: {len(combined_content)} characters")
            print(f"About page content length: {len(about_page_content) if about_page_content else 0} characters")

            if not combined_content.strip():
                print("Warning: No content found to analyze!")
                analysis_text = "Error: No content was found to analyze. The crawler may have been blocked or the page may be empty."
                analysis_filename = None
            else:
                # Generate AI analysis
                print("Sending content to AI analyzer...")
                analysis_result = analyze_website_content(combined_content, about_page_content)
                
                if analysis_result['success']:
                    analysis_text = analysis_result['analysis']
                    print("AI analysis completed successfully")
                    
                    # Save analysis to file
                    analysis_filename = f"{task_id}_analysis.txt"
                    analysis_path = os.path.join(app.config['UPLOAD_FOLDER'], analysis_filename)
                    with open(analysis_path, "w", encoding="utf-8") as f:
                        f.write(format_analysis_for_download(analysis_text))
                else:
                    error_msg = analysis_result.get('error', 'Unknown error')
                    print(f"AI analysis failed: {error_msg}")
                    analysis_text = f"Error generating analysis: {error_msg}"
                    analysis_filename = None

            # Save content
            content_path = os.path.join(app.config['UPLOAD_FOLDER'], content_filename)
            with open(content_path, "w", encoding="utf-8") as f:
                f.write(f"Combined content from {len(content_map)} pages\n")
                f.write("=" * 80 + "\n\n")
                
                for page_url, html_content in content_map.items():
                    try:
                        soup = BeautifulSoup(html_content, "html.parser")
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        if filters:
                            allowed_tags = get_allowed_tags(filters.split(','))
                            text = extract_filtered_content(soup, allowed_tags)
                        else:
                            text = soup.get_text()
                            
                        # Clean up the text
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                        
                        f.write(f"URL: {page_url}\n")
                        f.write("-" * 80 + "\n")
                        f.write(text)
                        f.write("\n\n")
                        f.write("=" * 80 + "\n\n")
                    except Exception as e:
                        print(f"Error processing content for {page_url}: {str(e)}")
            
            # Update status with completion and analysis
            crawl_status[task_id] = {
                'status': 'completed',
                'progress': 100,
                'links_file': output_filename,
                'content_file': content_filename,
                'analysis_file': analysis_filename,
                'analysis': analysis_text
            }
            
        except Exception as e:
            print(f"Error during crawl: {str(e)}")
            crawl_status[task_id] = {'status': 'error', 'error': str(e)}
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"Error in perform_crawl: {str(e)}")
        crawl_status[task_id] = {'status': 'error', 'error': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/crawl', methods=['POST'])
def start_crawl():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    max_depth = request.form.get('maxDepth', '3')
    allowed_domains = request.form.get('allowedDomains', '')
    filters = request.form.get('filters', '')

    base_name, unique_id = get_safe_filename(url)
    output_filename = f"{base_name}_links.txt"
    content_filename = f"{base_name}_content.txt"

    thread = threading.Thread(
        target=perform_crawl,
        args=(url, output_filename, content_filename, unique_id),
        kwargs={
            'max_depth': max_depth,
            'allowed_domains': allowed_domains,
            'filters': filters
        }
    )
    thread.start()

    return jsonify({
        'task_id': unique_id,
        'message': 'Crawling started'
    })

@app.route('/status/<task_id>')
def get_status(task_id):
    status = crawl_status.get(task_id, {'status': 'not_found'})
    return jsonify(status)

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(
            os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename)),
            as_attachment=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False) 