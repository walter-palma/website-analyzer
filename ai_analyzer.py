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
    
    # Remove common boilerplate text and navigation elements
    patterns_to_remove = [
        r'Accept\s+cookies?',
        r'Privacy Policy',
        r'Terms of Use',
        r'Copyright © \d{4}',
        r'All rights reserved',
        r'MENU\s*MENU',
        r'Select Page',
        r'VER INVESTIMENTOS',
        r'Mapa do Site',
        r'Avisos Legais',
        r'Proteção de Dados',
        r'RGPD',
        r'Termos de Uso',
        r'Política de Cookies'
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Remove duplicate sections (often found in navigation and content)
    lines = text.split('\n')
    unique_lines = []
    seen = set()
    for line in lines:
        line_lower = line.lower().strip()
        if line_lower and line_lower not in seen:
            seen.add(line_lower)
            unique_lines.append(line)
    text = ' '.join(unique_lines)
    
    # Limit to first 4000 characters (approximately 1000 tokens)
    # This ensures we have room for the prompt and response
    return text[:4000]

def extract_key_sections(content):
    """
    Extract the most relevant sections from the content.
    """
    important_sections = []
    
    # Look for about/who we are sections (including Portuguese)
    about_patterns = [
        r'(?i)(about\s+us|about\s+company|who\s+we\s+are|quem\s+somos|sobre\s+nós).*?(?=\n\n|\Z)',
        r'(?i)(A\s+Caixa\s+Capital\s+é).*?(?=\n\n|\Z)',
        r'(?i)(Fazemos\s+acontecer).*?(?=\n\n|\Z)'
    ]
    
    for pattern in about_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            important_sections.append(match.group(0))
    
    # Look for product/service descriptions (including Portuguese)
    product_patterns = [
        r'(?i)(our\s+products|our\s+services|what\s+we\s+offer|nossos\s+produtos|nossos\s+serviços).*?(?=\n\n|\Z)',
        r'(?i)(Private\s+Equity|Venture\s+Capital|Fundo\s+de\s+Fundos).*?(?=\n\n|\Z)',
        r'(?i)(Investimento\s+Direto|Investimento\s+Indireto).*?(?=\n\n|\Z)'
    ]
    
    for pattern in product_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            important_sections.append(match.group(0))
    
    # Look for team information (including Portuguese)
    team_patterns = [
        r'(?i)(our\s+team|leadership|management\s+team|equipa|liderança).*?(?=\n\n|\Z)'
    ]
    
    for pattern in team_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            important_sections.append(match.group(0))
    
    # Look for contact/location information (including Portuguese)
    contact_patterns = [
        r'(?i)(contact\s+us|location|headquarters|contactos|localização|sede).*?(?=\n\n|\Z)',
        r'(?i)(Avenida.*?Lisboa).*?(?=\n\n|\Z)'
    ]
    
    for pattern in contact_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            important_sections.append(match.group(0))
    
    # If no sections were found, return the first 8000 characters of the content
    if not important_sections:
        return content[:8000]
    
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
        print("\nStarting AI analysis...")
        if not content or not content.strip():
            print("Error: Empty content provided for analysis")
            return {
                'success': False,
                'error': 'No content provided for analysis'
            }

        print(f"Processing main content ({len(content)} characters)...")
        # Preprocess main content
        processed_content = preprocess_content(content)
        print(f"Preprocessed content length: {len(processed_content)} characters")
        
        key_sections = extract_key_sections(processed_content)
        print(f"Extracted key sections length: {len(key_sections)} characters")
        
        # Preprocess about page content if available
        if about_page_content:
            print(f"Processing about page content ({len(about_page_content)} characters)...")
            processed_about = preprocess_content(about_page_content)
            about_sections = extract_key_sections(processed_about)
            # Combine but ensure we don't exceed length limits
            combined_length = len(key_sections) + len(about_sections)
            if combined_length > 6000:  # Leave room for prompt and response
                # Prioritize main content but keep some about content
                about_sections = about_sections[:2000]
                key_sections = key_sections[:4000]
            final_content = f"{key_sections}\n\nABOUT PAGE CONTENT:\n{about_sections}"
        else:
            print("No about page content available")
            final_content = key_sections[:6000]  # Ensure we don't exceed limits

        print(f"Final content for analysis: {len(final_content)} characters")
        if not final_content.strip():
            print("Error: No content remained after processing")
            return {
                'success': False,
                'error': 'No meaningful content found after processing'
            }

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

        print("Calling GPT-4 API...")
        # Call GPT-4 API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a business analyst expert at analyzing company websites and providing structured insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000  # Reduced from 1500 to ensure we stay within limits
        )

        print("GPT-4 API call successful")
        # Return the analysis
        return {
            'success': True,
            'analysis': response.choices[0].message.content
        }
    except Exception as e:
        print(f"Error in AI analysis: {str(e)}")
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