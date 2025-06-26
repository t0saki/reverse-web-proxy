# Web Reverse Proxy

A simple but robust web reverse proxy built with Flask. This application allows you to access web pages through a proxy server, which can be useful for academic research, bypassing network restrictions, or analyzing web traffic.

> **Note**: This project is intended for educational and research purposes only. Use it responsibly and in compliance with applicable laws and regulations.

## Features

- **URL Rewriting**: Rewrites URLs in HTML, CSS, and JavaScript to ensure all resources are loaded through the proxy.
- **GET & POST Support**: Handles both GET and POST requests, allowing for form submissions.
- **Cookie Forwarding**: Forwards cookies between the client and the target server.
- **Dockerized**: Comes with a `Dockerfile` for easy containerization and deployment.
- **CI/CD with GitHub Actions**: Automatically builds and pushes a Docker image to the GitHub Container Registry (`ghcr.io`) on every push to the `main` branch.

### Setup

```bash
docker run -p 8000:8000 ghcr.io/t0saki/reverse-web-proxy
```

Open your web browser and navigate to `http://localhost:8000`.

## How to Use

1.  Enter the URL of the website you want to visit in the input field (e.g., `example.com`).
2.  Click the "Access Securely" button.
3.  The application will proxy your request to the target website and display the content. A notice banner will be displayed at the top of the page to remind you that the connection is being proxied.