#!/usr/bin/env python3
import http.server
import socketserver
import os
import subprocess
import re
import urllib.parse
from pathlib import Path

PORT = 9090
MODEL_DIR = "/opt/llama.cpp/Models"
SERVICE_FILE = "/etc/systemd/system/llama.service"

rpcEPS = "10.0.1.27:4000,10.0.1.76:4000,10.0.1.24:4000,10.0.1.206:4000"

def get_service_status():
    try:
        result = subprocess.run(["systemctl", "status", "llama.service", "--no-pager"], capture_output=True, text=True)
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)

def get_current_config():
    try:
        with open(SERVICE_FILE, "r") as f:
            content = f.read()
        # Extract ExecStart line
        execstart_match = re.search(r'ExecStart=(.+)', content)
        if not execstart_match:
            return None

        cmd = execstart_match.group(1).strip()
        # Parse args
        parts = cmd.split()
        config = {
            "model": "",
            "threads": 6,
            "context": 60000,
            "rpc": False
        }
        # Extract model path
        model_path = None
        for i, p in enumerate(parts):
            if p == "-m" and i + 1 < len(parts):
                model_path = parts[i+1]
                break
        if model_path:
            config["model"] = os.path.basename(model_path)
        # Extract threads
        try:
            t_idx = parts.index("-t")
            config["threads"] = int(parts[t_idx+1])
        except:
            pass
        # Extract context
        try:
            c_idx = parts.index("-c")
            config["context"] = int(parts[c_idx+1])
        except:
            pass
        # rpc?
        config["rpc"] = "--rpc" in parts

        return config
    except Exception as e:
        return {"error": str(e)}

def list_models():
    models = []
    if os.path.isdir(MODEL_DIR):
        for f in Path(MODEL_DIR).glob("*.gguf"):
            models.append(f.name)
    return sorted(models)

def update_service(config):
    threads = config.get("threads", 6)
    context = config.get("context", 60000)
    model = config.get("model", "")
    use_rpc = config.get("rpc", False)

    if not model:
        return False, "No model selected"

    base = f"/opt/llama.cpp/llama-server -m /opt/llama.cpp/Models/{model} --n-gpu-layers 200 --host 0.0.0.0 --port 8080 -c {context} -t {threads}"
    if use_rpc:
        base += f" --rpc {rpcEPS}"

    service_content = f"""[Unit]
Description=llama Service
After=network.target

[Service]
User=root
WorkingDirectory=/opt/llama.cpp
ExecStart={base}
Restart=always

[Install]
WantedBy=multi-user.target
"""
    try:
        with open(SERVICE_FILE, "w") as f:
            f.write(service_content)
        # Reload systemd and restart service
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "restart", "llama.service"], check=True)
        return True, "Service updated and restarted"
    except Exception as e:
        return False, f"Error: {str(e)}"

def start_service():
    try:
        subprocess.run(["systemctl", "start", "llama.service"], check=True)
        return True, "Service started"
    except Exception as e:
        return False, f"Error starting service: {str(e)}"

def stop_service():
    try:
        subprocess.run(["systemctl", "stop", "llama.service"], check=True)
        return True, "Service stopped"
    except Exception as e:
        return False, f"Error stopping service: {str(e)}"

# HTML template
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Llama Control Panel</title>
    <meta charset="utf-8">
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f9f9f9; }
        h1 { color: #333; }
        .status { padding: 10px; border: 1px solid #ccc; background: #fff; margin-bottom: 20px; }
        .form { background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        label { display: block; margin: 10px 0 5px; font-weight: bold; }
        select, input[type=number], input[type=checkbox] { padding: 5px; border: 1px solid #ccc; width: 100%; max-width: 300px; }
        input[type="checkbox"] { width: auto; margin-right: 5px; vertical-align: middle; }
        button { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; cursor: pointer; font-size: 16px; margin-top: 10px; }
        button:hover { opacity: 0.9; }
        .service-controls button { background-color: #2196F3; }
        .refresh-btn { background-color: #9C27B0; font-size: 14px; padding: 8px 16px; }
        .error { color: red; font-weight: bold; }
        .success { color: green; font-weight: bold; }
        pre { white-space: pre-wrap; background: #f0f0f0; padding: 10px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <h1>Llama Model Control</h1>

    <h2>Current Status</h2>
    <div class="status" id="status-section">
        <p><strong>Service Running:</strong> <span id="status-ok">{{status_ok}}</span></p>
        <p><strong>Config:</strong></p>
        <pre id="current-config">{{current_config}}</pre>
        <p><strong>Service Output (truncated):</strong></p>
        <pre id="service-output">{{service_output}}</pre>
        <div class="service-controls">
            <form method="POST" style="display: inline;">
                <input type="hidden" name="action" value="start">
                <button type="submit">Start Service</button>
            </form>
            <form method="POST" style="display: inline;">
                <input type="hidden" name="action" value="stop">
                <button type="submit">Stop Service</button>
            </form>
            <form method="POST" style="display: inline;">
                <input type="hidden" name="action" value="refresh_status">
                <button type="submit" class="refresh-btn">🔄 Refresh Status</button>
            </form>
        </div>
    </div>

    <h2>Update Configuration</h2>
    <div class="form">
        <form method="POST">
            <input type="hidden" name="action" value="update">
            <label for="model">Model (from {{model_dir}})</label>
            <select name="model" id="model">
                {{models_options}}
            </select>

            <label for="threads">Threads (default 6)</label>
            <input type="number" name="threads" id="threads" value="{{threads}}" min="1">

            <label for="context">Context Length (default 60000)</label>
            <input type="number" name="context" id="context" value="{{context}}" min="1024">

            <label>
                <input type="checkbox" name="rpc" {{rpc_checked}}>
                Enable rpc Mode
            </label>

            <button type="submit">Update & Restart</button>
        </form>
        <p class="{{msg_type}}">{{msg}}</p>
    </div>

    <script>
        document.querySelector('form[action="refresh_status"]').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData();
            formData.append('action', 'refresh_status');

            fetch('', {
                method: 'POST',
                body: formData
            })
            .then(response => response.text())
            .then(html => {
                // Create a temporary DOM to parse the response
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newStatusSection = doc.querySelector('#status-section');
                
                // If found, replace the content of our current status section
                if (newStatusSection) {
                    const currentStatusSection = document.getElementById('status-section');
                    currentStatusSection.innerHTML = newStatusSection.innerHTML;
                }
            })
            .catch(err => {
                console.error('Refresh failed:', err);
            });
        });
    </script>
</body>
</html>
"""

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.handle_page()

    def do_POST(self):
        self.handle_page(is_post=True)

    def handle_page(self, is_post=False):
        # Decode request
        if is_post:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode()
            form = urllib.parse.parse_qs(post_data)
        else:
            form = {}

        # Extract and sanitize inputs
        model = form.get("model", [None])[0]
        action = form.get("action", [None])[0]
        threads = 6
        context = 60000
        rpc = False
        try:
            if "threads" in form:
                threads = int(form["threads"][0])
        except:
            pass
        try:
            if "context" in form:
                context = int(form["context"][0])
        except:
            pass
        rpc = "rpc" in form

        # Default to current model if none selected (only for GET)
        if not is_post or not model:
            cfg = get_current_config()
            if cfg and "model" in cfg:
                model = cfg["model"]
                threads = cfg.get("threads", 6)
                context = cfg.get("context", 60000)
                rpc = cfg.get("rpc", False)

        # Handle service actions
        status_msg = ""
        msg_type = ""
        
        if is_post and action == "start":
            ok, msg = start_service()
            if ok:
                status_msg = "✅ " + msg
                msg_type = "success"
            else:
                status_msg = "❌ " + msg
                msg_type = "error"
        elif is_post and action == "stop":
            ok, msg = stop_service()
            if ok:
                status_msg = "✅ " + msg
                msg_type = "success"
            else:
                status_msg = "❌ " + msg
                msg_type = "error"
        elif is_post and action == "refresh_status":
            # For refresh, we'll just re-render with current values (no UI changes needed)
            pass
        elif is_post and action == "update" and model:
            ok, msg = update_service({
                "model": model or "",
                "threads": threads,
                "context": context,
                "rpc": rpc
            })
            if ok:
                status_msg = "✅ " + msg
                msg_type = "success"
            else:
                status_msg = "❌ " + msg
                msg_type = "error"

        # Gather status info (always needed for refresh_status)
        svc_ok, svc_out = get_service_status()
        svc_out_trunc = svc_out[:1000] + "..." if len(svc_out) > 1000 else svc_out
        cfg = get_current_config()
        cfg_str = str(cfg) if cfg else "(could not read)"

        # For all actions, generate the full page (including form)
        # List models for the dropdown
        models = list_models()
        models_options = "".join([f'<option value="{m}" {"selected" if m == model else ""}>{m}</option>' for m in models]) or '<option value="">No .gguf files found</option>'

        # Render HTML with full form
        html = HTML.replace("{{status_ok}}", "✅ Yes" if svc_ok else "❌ No")
        html = html.replace("{{current_config}}", cfg_str.replace("<", "&lt;"))
        html = html.replace("{{service_output}}", svc_out_trunc.replace("<", "&lt;"))
        html = html.replace("{{msg}}", status_msg)
        html = html.replace("{{msg_type}}", msg_type)
        html = html.replace("{{model_dir}}", MODEL_DIR)
        html = html.replace("{{models_options}}", models_options)
        html = html.replace("{{threads}}", str(threads))
        html = html.replace("{{context}}", str(context))
        html = html.replace("{{rpc_checked}}", "checked" if rpc else "")

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

# Run server
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"🚀 Llama Control Panel running at http://0.0.0.0:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Stopping server")
        httpd.shutdown()

