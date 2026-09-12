import http.server
import os
import socketserver
import sys
import tempfile
from datetime import date
from pathlib import Path

from .export import export_history_to_html
from .reports import get_daily_history_matrix, parse_date_range


class DynamicDashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            today_str = date.today().isoformat()
            start_date, end_date, label = parse_date_range(scope="unsettled")
            history_data = get_daily_history_matrix(start_date, end_date)

            temp_html = Path(tempfile.gettempdir()) / "tiffin_live.html"
            export_history_to_html(history_data, temp_html)

            with open(temp_html, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as err:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Server Error: {err}".encode("utf-8"))

    def do_POST(self):
        if self.path == "/api/sync":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")

                expected_token = os.environ.get("TIFFIN_SYNC_KEY")
                received_token = self.headers.get("X-Tiffin-Token")
                if expected_token and received_token != expected_token:
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b"Unauthorized")
                    return

                import json
                data = json.loads(body)
                from .backup import restore_db_from_dict
                restore_db_from_dict(data)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success", "message": "Database synchronized"}')
            except Exception as err:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f'{{"error": "{err}"}}'.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress noisy HTTP GET logging to keep CLI quiet
        pass


import socket


def get_local_ip() -> str:
    """Get primary LAN IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_systemd_service(port: int = 8765) -> str:
    python_path = sys.executable

    content = f"""[Unit]
Description=🍱 Tiffin Live Web Dashboard Server
After=network.target

[Service]
Type=simple
User={os.environ.get('USER', 'root')}
ExecStart={python_path} -m tiffin serve --port {port}
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
    return content


def generate_nginx_config(domain: str = "tiffin.parikar.in", port: int = 8765) -> str:
    content = f"""# Nginx Reverse Proxy Configuration for {domain}
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    return content


def run_server(host: str = "0.0.0.0", port: int = 8765, background: bool = False) -> None:
    """Run lightweight HTTP server hosting live Tiffin transparency dashboard."""
    local_ip = get_local_ip()

    if background:
        import subprocess
        cmd = [sys.executable, "-m", "tiffin", "serve", "--port", str(port)]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✓ Tiffin live server launched in background!")
        print(f"  • Local link:   http://localhost:{port}")
        print(f"  • Friends link: http://{local_ip}:{port}")
        return

    handler = DynamicDashboardHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((host, port), handler) as httpd:
        print(f"\n🍱 Tiffin Live Web Dashboard is running!")
        print(f"  • Local access:     http://localhost:{port}")
        print(f"  • Friends on Wi-Fi: http://{local_ip}:{port}")
        print(f"  • Friends on VPS:   http://<YOUR_VPS_IP>:{port}")
        print("\nPress Ctrl+C to stop.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
