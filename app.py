# A more robust web reverse proxy service using Flask.

from flask import Flask, render_template, request, Response, redirect, url_for
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re # NEW: Import regex for advanced rewriting

app = Flask(__name__)

# --- Configuration ---
NOTICE_BANNER_HTML = """
<div style="background-color: #ffc107; color: #333; padding: 12px; text-align: center; font-family: sans-serif; font-size: 16px; border-bottom: 2px solid #e0a800; z-index: 999999; position: sticky; top: 0;">
    <b>Notice:</b> This page is intended for educational and research purposes only. This connection is relayed by a proxy server, which can view or modify traffic. Avoid submitting passwords, financial details, or any sensitive personal data.
</div>
"""

# --- Helper Function for Rewriting URLs in Text/CSS ---
def rewrite_css_urls(content, base_url):
    """
    NEW: A helper function to rewrite url() paths in CSS or style blocks.
    Uses regex to find all occurrences of url(...) and rewrites the inner path.
    """
    def replacer(match):
        original_url = match.group(1).strip("'\"")
        absolute_url = urljoin(base_url, original_url)
        proxied_url = url_for('proxy_path', target_url=absolute_url)
        return f"url('{proxied_url}')"

    # This regex finds url(...) patterns, capturing the content inside the parentheses.
    return re.sub(r'url\((.*?)\)', replacer, content)

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

    # MODIFIED: Better scheme handling. Default to https for a modern web.
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url

    return redirect(url_for('proxy_path', target_url=target_url))

# MODIFIED: Now accepts both GET and POST requests
@app.route('/proxy/<path:target_url>', methods=['GET', 'POST'])
def proxy_path(target_url):
    """
    The main proxy logic. Fetches a URL passed as part of the path.
    Now handles GET, POST, cookies, and more robust content rewriting.
    """
    query_params = request.query_string.decode('utf-8')
    if query_params:
        full_target_url = f"{target_url}?{query_params}"
    else:
        full_target_url = target_url

    try:
        headers = {
            'User-Agent': request.headers.get('User-Agent', 'Mozilla/5.0'), # Forward user's agent
            'Referer': request.headers.get('Referer', ''),
            'Accept-Language': request.headers.get('Accept-Language', ''),
            'Host': urlparse(target_url).netloc
        }

        # NEW: Handle POST requests by forwarding form data
        if request.method == 'POST':
            # Forward form data and files
            resp = requests.post(
                full_target_url,
                headers=headers,
                data=request.form,
                files=request.files,
                cookies=request.cookies, # NEW: Forward cookies from the client
                stream=True,
                allow_redirects=False
            )
        else: # GET request
            resp = requests.get(
                full_target_url,
                headers=headers,
                cookies=request.cookies, # NEW: Forward cookies from the client
                stream=True,
                allow_redirects=False
            )

        content_type = resp.headers.get('Content-Type', '').lower()

        if 300 <= resp.status_code < 400 and 'Location' in resp.headers:
            new_location = urljoin(full_target_url, resp.headers['Location'])
            return redirect(url_for('proxy_path', target_url=new_location))

        # --- Content Rewriting ---
        if 'text/html' in content_type:
            # Use .content to avoid decoding issues, BeautifulSoup will handle it.
            soup = BeautifulSoup(resp.content, 'html.parser', from_encoding=resp.encoding)

            # MODIFIED: Expanded list of tags and attributes to rewrite
            tags_to_rewrite = {
                'a': 'href', 'link': 'href', 'script': 'src', 'img': ['src', 'srcset'],
                'form': 'action', 'iframe': 'src', 'meta': 'content'
            }
            for tag_name, attrs in tags_to_rewrite.items():
                if not isinstance(attrs, list): attrs = [attrs] # Ensure attrs is a list
                for attr in attrs:
                    for tag in soup.find_all(tag_name, **{attr: True}):
                        # Special handling for meta refresh URLs
                        if tag_name == 'meta' and 'url=' in tag.get(attr, ''):
                            content_val = tag[attr]
                            original_url = content_val.split('url=')[-1]
                            absolute_url = urljoin(full_target_url, original_url)
                            tag[attr] = f"{content_val.split('url=')[0]}url={url_for('proxy_path', target_url=absolute_url)}"
                        else:
                            original_url = tag[attr]
                            # Special handling for srcset which has multiple URLs
                            if attr == 'srcset':
                                rewritten_srcset = []
                                for part in original_url.split(','):
                                    part = part.strip()
                                    url_part, *desc_part = part.split(' ', 1)
                                    absolute_url = urljoin(full_target_url, url_part)
                                    proxied_url = url_for('proxy_path', target_url=absolute_url)
                                    rewritten_srcset.append(f"{proxied_url} {' '.join(desc_part)}")
                                tag[attr] = ', '.join(rewritten_srcset)
                            else:
                                absolute_url = urljoin(full_target_url, original_url)
                                tag[attr] = url_for('proxy_path', target_url=absolute_url)

            # NEW: Rewrite URLs inside <style> tags
            for style_tag in soup.find_all('style'):
                style_tag.string = rewrite_css_urls(style_tag.get_text(), full_target_url)

            # NEW: Rewrite URLs inside inline style attributes
            for tag in soup.find_all(style=True):
                tag['style'] = rewrite_css_urls(tag['style'], full_target_url)

            # Banner Injection
            body = soup.find('body')
            if body:
                banner_soup = BeautifulSoup(NOTICE_BANNER_HTML, 'html.parser')
                body.insert(0, banner_soup)

            # NEW: Create a Flask response to set cookies
            final_response = Response(str(soup))
            # Forward cookies from the target server to the client
            for name, value in resp.cookies.items():
                final_response.set_cookie(name, value)
            return final_response

        # NEW: Handle CSS content rewriting
        elif 'text/css' in content_type:
            css_content = resp.text
            rewritten_css = rewrite_css_urls(css_content, full_target_url)
            return Response(rewritten_css, content_type=content_type, status=resp.status_code)

        else: # For non-HTML/CSS content, stream it directly.
            def generate():
                for chunk in resp.iter_content(chunk_size=8192):
                    yield chunk
            
            final_response = Response(generate(), content_type=content_type, status=resp.status_code)
            # Forward cookies for non-HTML content too (e.g., API calls setting a cookie)
            for name, value in resp.cookies.items():
                final_response.set_cookie(name, value)
            return final_response

    except requests.exceptions.RequestException as e:
        return f"Error: Could not fetch the URL. {e}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)