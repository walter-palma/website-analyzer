import openai
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def preprocess_content(text):
    """
    Preprocess and clean the content to reduce size and improve relevance.
    """
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove common boilerplate text
    text = re.sub(r'(Accept\s+cookies?|Privacy Policy|Terms of Use|Copyright © \d{4}|All rights reserved)', '', text, flags=re.IGNORECASE)
    
    # Limit to first 8000 characters (approximately 2000 tokens)
    return text[:8000]

def extract_key_sections(content):
    """
    Extract the most relevant sections from the content.
    """
    important_sections = []
    
    # Look for about section
    about_match = re.search(r'(?i)(about\s+us|about\s+company|who\s+we\s+are).*?(?=\n\n|\Z)', content, re.DOTALL)
    if about_match:
        important_sections.append(about_match.group(0))
    
    # Look for product/service descriptions
    product_match = re.search(r'(?i)(our\s+products|our\s+services|what\s+we\s+offer).*?(?=\n\n|\Z)', content, re.DOTALL)
    if product_match:
        important_sections.append(product_match.group(0))
    
    # Look for team information
    team_match = re.search(r'(?i)(our\s+team|leadership|management\s+team).*?(?=\n\n|\Z)', content, re.DOTALL)
    if team_match:
        important_sections.append(team_match.group(0))
    
    # Look for contact/location information
    contact_match = re.search(r'(?i)(contact\s+us|location|headquarters).*?(?=\n\n|\Z)', content, re.DOTALL)
    if contact_match:
        important_sections.append(contact_match.group(0))
    
    return '\n\n'.join(important_sections)

def analyze_website_content(content, about_page_content=None):
    """
    Analyze website content using GPT-4 and generate a structured analysis.
    
    Args:
        content (str): The main website content
        about_page_content (str, optional): Content from the About page if available
    
    Returns:
        dict: Structured analysis of the website
    """
    try:
        # Preprocess main content
        processed_content = preprocess_content(content)
        key_sections = extract_key_sections(processed_content)
        
        # Preprocess about page content if available
        if about_page_content:
            processed_about = preprocess_content(about_page_content)
            about_sections = extract_key_sections(processed_about)
            final_content = f"{key_sections}\n\nABOUT PAGE CONTENT:\n{about_sections}"
        else:
            final_content = key_sections

        # Prepare the prompt for GPT-4
        prompt = f"""Analyze the following website content and provide a structured analysis with these specific sections:

1. Company/Website Description (1 paragraph)
2. Key Offerings and Features
3. Market Positioning & Differentiators
4. Target Sectors & Use Cases
5. Team Members (if available)
6. Company Location


Website Content:
{final_content}

Please provide a structured analysis with clear section headers. If information for any section is not available, indicate "Information not available" for that section.
"""

        # Call GPT-4 API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a business analyst expert at analyzing company websites and providing structured insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )

        # Return the analysis
        return {
            'success': True,
            'analysis': response.choices[0].message.content
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def format_analysis_for_download(analysis):
    """
    Format the analysis for downloading as a text file.
    
    Args:
        analysis (str): The raw analysis text
    
    Returns:
        str: Formatted analysis with clear section breaks
    """
    return f"""WEBSITE ANALYSIS REPORT
{'='* 50}

{analysis}

{'='* 50}
Generated using AI-powered analysis
""" 