import os
from flask import Flask, render_template, request, send_file , jsonify
import requests
from bs4 import BeautifulSoup
import re
from pdf2docx import Converter
# import threading
import time
# import uuid
import tempfile

app = Flask(__name__)

def fetch_website_info(url, user_input):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else 'No title found'

        # First, check for the PDF link in the div with id 'PDFF'
        pdf_div = soup.find('div', id='PDFF')
        if pdf_div:
            source_link = pdf_div.get('source')
            if source_link:
                return title, source_link, "PDF found and ready to download."
            else:
                return title, None, "No 'source' attribute found."
        else:
            # Check if user input contains the specific substring
            if ".com/advance-pdf-viewer" in user_input:
                # Search through all <script> tags for the PDF link
                script_tags = soup.find_all('script')
                for script in script_tags:
                    if script.string:  # Check if the script tag has content
                        found_url = extract_url_from_js(script.string)
                        if found_url:
                            return title, found_url, "PDF found in JavaScript content."
            return title, None, "No <div> found with id 'PDFF' and no valid URL found in JavaScript content."

    except requests.exceptions.RequestException as e:
        return None, None, f"An error occurred: {e}"

def extract_url_from_js(js_content):
    # Regular expression to find the specific URL pattern and ignore any fragment identifiers
    pattern = r'https://www\.selfstudys\.com/[^\s\'"#]*'
    match = re.search(pattern, js_content)
    return match.group(0) if match else None

def extract_and_format_url(user_input):
    # Remove unwanted suffixes like 'google_vignette' or any other specified suffixes
    unwanted_suffixes = ["#google_vignette", "#another_suffix"]  # Add any other unwanted suffixes here
    for suffix in unwanted_suffixes:
        if suffix in user_input:
            user_input = user_input.split(suffix)[0]  # Remove the unwanted suffix

    keyword = "selfstudys.com/"
    start_index = user_input.find(keyword)

    if start_index != -1:
        extracted_path = user_input[start_index + len(keyword):].strip()
        full_url = f"https://www.selfstudys.com/{extracted_path}"
        return full_url
    else:
        return None








# Global variable to track progress
progress = {}

def reset_progress():
    global progress
    progress = {}








def get_webpage_title(url):
    """Fetch the title of the webpage from the given URL."""
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title.string if soup.title else "Document"
        return title.strip()
    return "Document"


@app.route('/download_word', methods=['GET'])
def download_word():
    global progress
    pdf_url = request.args.get('pdf_url')
    if not pdf_url:
        return "No PDF URL provided", 400

    # Reset progress for this download
    reset_progress()
    
    # Get the title of the webpage to use as the filename
    title = get_webpage_title(pdf_url)
    sanitized_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
    word_filename = f"{sanitized_title}.docx"

    # Download the PDF file
    pdf_response = requests.get(pdf_url)
    if pdf_response.status_code != 200:
        return "Failed to download PDF", 400

    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf_file:
        temp_pdf_file.write(pdf_response.content)
        temp_pdf_path = temp_pdf_file.name

    # Convert PDF to Word
    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_word_file:
        word_path = temp_word_file.name
        cv = Converter(temp_pdf_path)

        # Simulate progress
        total_steps = 100  # Assume 100 steps for progress
        for step in range(total_steps):
            time.sleep(0.1)  # Simulate processing time
            progress[word_filename] = step + 1  # Update progress

        cv.convert(word_path, start=0, end=None)
        cv.close()

    os.remove(temp_pdf_path)

    # Send the Word file back to the client
    response = send_file(word_path, as_attachment=True, download_name=word_filename)

    def cleanup():
        os.remove(word_path)

    @response.call_on_close
    def on_close():
        cleanup()

    return response

@app.route('/progress/<filename>', methods=['GET'])
def get_progress(filename):
    global progress
    return jsonify(progress.get(filename, 0))

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/', methods=['GET', 'POST'])
def home():
    user_input = ""
    formatted_url = ""
    title = ""
    pdf_link = None  # Initialize as None
    message = "Welcome! Please enter a URL from selfstudys.com to fetch the PDF."

    if request.method == 'POST':
        user_input = request.form['url']
        formatted_url = extract_and_format_url(user_input)
        
        if formatted_url:
            title, pdf_link, message = fetch_website_info(formatted_url, user_input)
        else:
            message = "No valid URL found."

    return render_template('index.html', user_input=user_input, formatted_url=formatted_url,
                           title=title, pdf_link=pdf_link, message=message)

if __name__ == "__main__":
    app.run(debug=True)

    # 1