# app.py
# A simple web reverse proxy service using Flask.
#
# To run this application:
# 1. Install dependencies:
#    pip install Flask requests beautifulsoup4
# 2. Save this file as `app.py`.
# 3. Create a directory named `templates` in the same folder.
# 4. Save the HTML file as `index.html` inside the `templates` directory.
# 5. Run the server from your terminal:
#    flask run
# 6. Open your web browser and navigate to http://127.0.0.1:5000

from flask import Flask, render_template, request, Response, redirect, url_for
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

# --- Configuration ---
NOTICE_BANNER_HTML = """
<div style="background-color: #ffc107; color: #333; padding: 12px; text-align: center; font-family: sans-serif; font-size: 16px; border-bottom: 2px solid #e0a800; z-index: 999999; position: sticky; top: 0;">
    <b>Notice:</b> This page is for academic research purposes only. This connection is relayed by a proxy server, which can view or modify traffic. Avoid submitting passwords, financial details, or any sensitive personal data.
</div>
"""

@app.route('/')
def index():
    """Renders the main page with a URL input form."""
    return render_template('index.html')

@app.route('/proxy', methods=['GET'])
def proxy_redirect():
    """
    Handles the initial form submission.
    Redirects from /proxy?url=example.com to the robust /proxy/http://example.com URL structure.
    """
    target_url = request.args.get('url')
    if not target_url:
        return "Error: No URL provided in the 'url' parameter.", 400

    # Ensure the URL has a scheme (e.g., http, https)
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'http://' + target_url
    
    # Redirect to the path-based URL structure
    return redirect(url_for('proxy_path', target_url=target_url))


@app.route('/proxy/<path:target_url>')
def proxy_path(target_url):
    """
    The main proxy logic. Fetches a URL passed as part of the path.
    """
    # Re-append the original query string from the user's request
    # This is crucial for searches, e.g., ?q=hello
    query_params = request.query_string.decode('utf-8')
    if query_params:
        full_target_url = f"{target_url}?{query_params}"
    else:
        full_target_url = target_url

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            # IMPORTANT: Forward the Host header of the target, not our proxy's host
            'Host': urlparse(target_url).netloc
        }
        
        resp = requests.get(full_target_url, headers=headers, stream=True, allow_redirects=False)

        content_type = resp.headers.get('Content-Type', '').lower()
        
        # Handle redirects manually to rewrite the Location header
        if 300 <= resp.status_code < 400 and 'Location' in resp.headers:
            new_location = urljoin(full_target_url, resp.headers['Location'])
            # Redirect the user's browser to the new proxied location
            return redirect(url_for('proxy_path', target_url=new_location))

        if 'text/html' in content_type:
            html_content = resp.content # Use .content to handle encoding better
            soup = BeautifulSoup(html_content, 'html.parser', from_encoding=resp.encoding)

            # URL Rewriting for the new path-based structure
            tags_to_rewrite = {
                'a': 'href', 'link': 'href', 'script': 'src', 'img': 'src', 'form': 'action'
            }
            for tag_name, attr in tags_to_rewrite.items():
                for tag in soup.find_all(tag_name, **{attr: True}):
                    original_url = tag[attr]
                    absolute_url = urljoin(full_target_url, original_url)
                    # Rewrite the attribute to point back to our new proxy structure
                    tag[attr] = url_for('proxy_path', target_url=absolute_url)

            # Banner Injection
            body = soup.find('body')
            if body:
                banner_soup = BeautifulSoup(NOTICE_BANNER_HTML, 'html.parser')
                body.insert(0, banner_soup)
            
            return str(soup)
        else:
            # For non-HTML content, stream it directly.
            def generate():
                for chunk in resp.iter_content(chunk_size=1024):
                    yield chunk
            
            return Response(generate(), content_type=content_type, status=resp.status_code)

    except requests.exceptions.RequestException as e:
        return f"Error: Could not fetch the URL. {e}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
