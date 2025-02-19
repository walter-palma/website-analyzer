# AI-Powered Website Analyzer

A powerful web crawler and analyzer that uses GPT-4 to provide detailed insights about websites. This tool crawls websites and generates comprehensive analysis reports including company information, offerings, market positioning, and more.

## Features

- Web crawling with configurable depth and domain restrictions
- AI-powered analysis using GPT-4
- Structured insights including:
  - Company/Website Description
  - Key Offerings and Features
  - Market Positioning & Differentiators
  - Target Sectors & Use Cases
  - Team Members
  - Company Location
- Downloadable reports for:
  - AI Analysis
  - Crawled Links
  - Website Content
- Clean, modern web interface
- Real-time crawling progress updates

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/website-analyzer.git
cd website-analyzer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to `http://127.0.0.1:5001`

3. Enter a website URL and configure crawling options:
   - Maximum crawling depth
   - Allowed domains
   - Content filters

4. Click "Start Crawling" and wait for the analysis to complete

5. View the AI-generated analysis and download reports

## Requirements

- Python 3.7+
- OpenAI API key
- Chrome/Chromium browser (for Selenium)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 