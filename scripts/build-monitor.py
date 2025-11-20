#!/usr/bin/env python3
"""Build Monitor - Real-time deployment and container monitoring.

Streams cloud-init progress, docker logs, and detects issues throughout
the entire deployment lifecycle.

Phases:
  1. Cloud-Init: Stream /var/log/cloud-init-output.log
  2. Container Startup: Stream docker logs during first boot
  3. Runtime: Continue streaming logs and detect issues
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse


# Configuration
LOG_DIR = Path("/var/log/build-monitor")
CLOUD_INIT_LOG = Path("/var/log/cloud-init-output.log")
HTTP_PORT = 9090
MAX_LOG_LINES = 1000


class DeploymentPhase:
    """Deployment phase constants."""
    CLOUD_INIT = "cloud_init"
    CONTAINER_STARTUP = "container_startup"
    RUNTIME = "runtime"


class LogStreamer(threading.Thread):
    """Streams logs from various sources based on deployment phase."""
    
    def __init__(self, container_name: str = "app"):
        super().__init__(daemon=True)
        self.running = True
        self.phase = DeploymentPhase.CLOUD_INIT
        self.log_buffer = deque(maxlen=MAX_LOG_LINES)
        self.lock = threading.Lock()
        self.cloud_init_complete = False
        self.container_started = False
        self.container_name = container_name
        self.deployment_id = os.environ.get("BUILD_DEPLOYMENT_ID", "unknown")
        self.app_name = os.environ.get("BUILD_APP_NAME", "unknown")
        
    def run(self):
        """Main streaming loop - adapts based on phase."""
        self.log_line("🚀 Build Monitor started", "info")
        self.log_line(f"📦 Deployment: {self.app_name} ({self.deployment_id})", "info")
        
        # Phase 1: Stream cloud-init
        self.stream_cloud_init()
        
        # Phase 2: Wait for container and stream startup
        self.stream_container_startup()
        
        # Phase 3: Stream runtime logs
        self.stream_runtime_logs()
    
    def stream_cloud_init(self):
        """Stream cloud-init output log."""
        self.log_line("📋 Monitoring cloud-init progress...", "info")
        
        # Wait for cloud-init log to exist
        timeout = 120
        waited = 0
        while self.running and not CLOUD_INIT_LOG.exists() and waited < timeout:
            time.sleep(1)
            waited += 1
        
        if not CLOUD_INIT_LOG.exists():
            self.log_line("⚠️  Cloud-init log not found, skipping to container startup", "warning")
            self.cloud_init_complete = True
            self.phase = DeploymentPhase.CONTAINER_STARTUP
            return
        
        # Tail cloud-init log
        try:
            process = subprocess.Popen(
                ['tail', '-f', '-n', '0', str(CLOUD_INIT_LOG)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            for line in iter(process.stdout.readline, ''):
                if not self.running:
                    process.terminate()
                    break
                
                line = line.rstrip()
                if line:
                    # Parse and format cloud-init output
                    formatted = self.format_cloud_init_line(line)
                    if formatted:
                        self.log_line(formatted, "cloud-init")
                    
                    # Detect cloud-init completion
                    if "Cloud-init" in line and "finished" in line:
                        self.cloud_init_complete = True
                        self.log_line("✓ Cloud-init complete", "success")
                        process.terminate()
                        break
            
            process.wait(timeout=5)
            
        except Exception as e:
            self.log_line(f"Error streaming cloud-init: {e}", "error")
        
        self.phase = DeploymentPhase.CONTAINER_STARTUP
    
    def format_cloud_init_line(self, line: str) -> Optional[str]:
        """Format cloud-init log lines with icons and colors."""
        line = line.strip()
        
        # Filter out very noisy lines
        noise_patterns = [
            "dpkg-preconfigure",
            "update-alternatives",
            "ldconfig deferred processing",
            "Processing triggers",
            "Setting up man-db"
        ]
        if any(pattern in line for pattern in noise_patterns):
            return None
        
        # Docker pull progress - extract percentage if possible
        if "Pulling" in line or "Downloading" in line:
            return f"📥 {line}"
        
        if "Pull complete" in line or "Download complete" in line:
            return f"✓ {line}"
        
        # Package installation
        if "Setting up" in line or "Unpacking" in line:
            # Extract package name
            match = re.search(r'(Setting up|Unpacking) ([^\s]+)', line)
            if match:
                package = match.group(2)
                return f"📦 Installing {package}"
            return f"📦 {line}"
        
        # Docker setup
        if "docker" in line.lower() and ("start" in line.lower() or "enable" in line.lower()):
            return f"🐳 {line}"
        
        # GPU setup
        if any(keyword in line.lower() for keyword in ["nvidia", "gpu", "cuda"]):
            if "nvidia-smi" in line:
                return f"🎮 GPU drivers verified"
            return f"🎮 {line}"
        
        # BuildWatch/Build Monitor setup
        if "build-monitor" in line.lower() or "buildwatch" in line.lower():
            return f"📊 {line}"
        
        # Systemd services
        if "systemctl" in line and ("enable" in line or "start" in line):
            return f"⚙️  {line}"
        
        # Errors
        if "error" in line.lower() or "failed" in line.lower():
            return f"❌ {line}"
        
        # Warnings
        if "warn" in line.lower():
            return f"⚠️  {line}"
        
        # Success/Complete
        if "success" in line.lower() or "complete" in line.lower() or "✓" in line:
            return f"✓ {line}"
        
        # Important messages that should be shown
        important_keywords = [
            "install", "download", "pull", "start", "complete", 
            "error", "warn", "fail", "success", "docker", "gpu",
            "building", "running", "configured", "enabled"
        ]
        
        if any(k in line.lower() for k in important_keywords):
            return f"   {line}"
        
        return None
    
    def stream_container_startup(self):
        """Wait for container to start and stream its logs."""
        self.log_line("🐋 Waiting for container to start...", "info")
        
        # Wait for Docker to be ready
        if not self._wait_for_docker():
            self.log_line("⚠️  Docker not available", "warning")
            return
        
        # Wait for container to exist
        timeout = 300  # 5 minutes
        waited = 0
        while self.running and waited < timeout:
            try:
                result = subprocess.run(
                    ['docker', 'ps', '-a', '--filter', f'name={self.container_name}', 
                     '--format', '{{.Names}}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and self.container_name in result.stdout:
                    self.container_started = True
                    self.log_line(f"✓ Container '{self.container_name}' detected", "success")
                    break
                
            except Exception:
                pass
            
            if waited == 0:
                self.log_line("   Waiting for container creation...", "info")
            time.sleep(3)
            waited += 3
        
        if waited >= timeout:
            self.log_line("⚠️  Container did not start within timeout", "warning")
            return
        
        self.phase = DeploymentPhase.RUNTIME
        
        # Stream container logs
        self.log_line("📜 Streaming container logs...", "info")
        self.stream_container_logs()
    
    def _wait_for_docker(self, max_wait: int = 60) -> bool:
        """Wait for Docker to be available."""
        waited = 0
        while self.running and waited < max_wait:
            try:
                result = subprocess.run(
                    ['docker', 'info'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return True
            except Exception:
                pass
            
            if waited == 0:
                self.log_line("   Waiting for Docker to be ready...", "info")
            time.sleep(2)
            waited += 2
        
        return False
    
    def stream_runtime_logs(self):
        """Stream container logs during runtime (handled by stream_container_logs)."""
        pass
    
    def stream_container_logs(self):
        """Stream logs from Docker container."""
        try:
            # Get existing logs first (last 50 lines)
            result = subprocess.run(
                ['docker', 'logs', '--tail', '50', self.container_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Output existing logs
                for line in result.stdout.split('\n'):
                    if line.strip():
                        formatted = self.format_container_log_line(line)
                        self.log_line(formatted, "container")
                
                # Also check stderr
                for line in result.stderr.split('\n'):
                    if line.strip():
                        formatted = self.format_container_log_line(line)
                        self.log_line(formatted, "container")
            
            # Now follow logs in real-time
            process = subprocess.Popen(
                ['docker', 'logs', '-f', '--tail', '0', self.container_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr and stdout
                text=True,
                bufsize=1
            )
            
            for line in iter(process.stdout.readline, ''):
                if not self.running:
                    process.terminate()
                    break
                
                line = line.rstrip()
                if line:
                    formatted = self.format_container_log_line(line)
                    self.log_line(formatted, "container")
            
            process.wait(timeout=5)
            
        except subprocess.TimeoutExpired:
            self.log_line("Container logs timed out", "warning")
        except Exception as e:
            self.log_line(f"Error streaming container logs: {e}", "error")
    
    def format_container_log_line(self, line: str) -> str:
        """Format container log lines."""
        line = line.strip()
        
        # Detect log level from common patterns
        if re.match(r'^\[?\d{4}-\d{2}-\d{2}', line):
            # Has timestamp, likely structured log
            if "ERROR" in line or " E " in line:
                return f"❌ {line}"
            elif "WARN" in line or " W " in line:
                return f"⚠️  {line}"
            elif "INFO" in line or " I " in line:
                return f"ℹ️  {line}"
            elif "DEBUG" in line or " D " in line:
                return f"🐛 {line}"
        
        # Check for common error patterns
        line_lower = line.lower()
        if "error" in line_lower or "exception" in line_lower or "failed" in line_lower:
            return f"❌ {line}"
        elif "warn" in line_lower or "warning" in line_lower:
            return f"⚠️  {line}"
        elif "success" in line_lower or "started" in line_lower or "ready" in line_lower:
            return f"✓ {line}"
        
        # Default - just show the line
        return f"   {line}"
    
    def log_line(self, message: str, category: str = "info"):
        """Add line to buffer and output."""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        formatted_line = f"[{timestamp}] {message}"
        
        with self.lock:
            self.log_buffer.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": message,
                "category": category,
                "formatted": formatted_line
            })
        
        # Output to stdout
        print(formatted_line, flush=True)
        
        # Also write to file
        log_to_file(LOG_DIR / "build-monitor.log", formatted_line)
    
    def get_recent_logs(self, lines: int = 100) -> List[Dict[str, Any]]:
        """Get recent log lines."""
        with self.lock:
            logs_list = list(self.log_buffer)
        return logs_list[-lines:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "phase": self.phase,
            "cloud_init_complete": self.cloud_init_complete,
            "container_started": self.container_started,
            "container_name": self.container_name,
            "deployment_id": self.deployment_id,
            "app_name": self.app_name,
            "log_count": len(self.log_buffer)
        }
    
    def stop(self):
        """Stop the streamer."""
        self.running = False


class IssueDetector:
    """Detects issues from log patterns and Docker events."""
    
    def __init__(self, log_streamer: LogStreamer):
        self.log_streamer = log_streamer
        self.issues = deque(maxlen=100)
        self.lock = threading.Lock()
        self.running = True
        
    def check_logs_for_issues(self):
        """Periodically check logs for issues."""
        while self.running:
            try:
                logs = self.log_streamer.get_recent_logs(50)
                
                for log_entry in logs:
                    message = log_entry.get("message", "")
                    self.check_log_line(message)
                
                time.sleep(5)
            except Exception as e:
                print(f"Error checking logs: {e}", file=sys.stderr)
                time.sleep(5)
    
    def check_log_line(self, line: str):
        """Check a log line for issues."""
        line_lower = line.lower()
        
        # OOM detection
        if "out of memory" in line_lower or "oom" in line_lower or "137" in line:
            self.log_issue({
                "type": "oom",
                "severity": "critical",
                "message": "Out of memory detected",
                "recommendation": "Increase instance memory or optimize application",
                "line": line[:200]
            })
        
        # Crash detection
        if "crash" in line_lower or "segfault" in line_lower or "core dump" in line_lower:
            self.log_issue({
                "type": "crash",
                "severity": "critical",
                "message": "Application crash detected",
                "recommendation": "Check application logs for crash cause",
                "line": line[:200]
            })
        
        # Port conflict
        if "address already in use" in line_lower or "bind: address already in use" in line_lower:
            self.log_issue({
                "type": "port_conflict",
                "severity": "error",
                "message": "Port conflict detected",
                "recommendation": "Check if another service is using the same port",
                "line": line[:200]
            })
        
        # Permission errors
        if "permission denied" in line_lower:
            self.log_issue({
                "type": "permission",
                "severity": "error",
                "message": "Permission error detected",
                "recommendation": "Check file/directory permissions",
                "line": line[:200]
            })
        
        # Connection errors
        if "connection refused" in line_lower or "cannot connect" in line_lower:
            self.log_issue({
                "type": "connection",
                "severity": "warning",
                "message": "Connection error detected",
                "recommendation": "Check if dependent services are running",
                "line": line[:200]
            })
    
    def log_issue(self, issue: Dict[str, Any]):
        """Log a detected issue."""
        timestamp = datetime.now(timezone.utc).isoformat()
        issue['timestamp'] = timestamp
        issue['resolved'] = False
        
        # Check if we already have this issue recently (debounce)
        with self.lock:
            recent_issues = list(self.issues)[-10:]
            for recent in recent_issues:
                if recent.get('type') == issue['type'] and recent.get('line') == issue.get('line'):
                    return  # Skip duplicate
            
            self.issues.append(issue)
        
        # Output to console with icon
        severity_icon = "🚨" if issue["severity"] == "critical" else "⚠️"
        self.log_streamer.log_line(
            f"{severity_icon} {issue['severity'].upper()}: {issue['message']}", 
            "issue"
        )
        if issue.get('recommendation'):
            self.log_streamer.log_line(
                f"   → {issue['recommendation']}", 
                "issue"
            )
    
    def get_issues(self, unresolved_only: bool = False) -> List[Dict[str, Any]]:
        """Get detected issues."""
        with self.lock:
            issues_list = list(self.issues)
        
        if unresolved_only:
            issues_list = [i for i in issues_list if not i.get('resolved', False)]
        
        return list(reversed(issues_list))
    
    def stop(self):
        """Stop the issue detector."""
        self.running = False


class BuildMonitorHandler(BaseHTTPRequestHandler):
    """HTTP API for Build Monitor."""
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            query_params = parse_qs(parsed.query)
            
            if path == '/health':
                self.handle_health()
            elif path == '/logs':
                lines = int(query_params.get('lines', ['100'])[0])
                self.handle_logs(lines)
            elif path == '/status':
                self.handle_status()
            elif path == '/issues':
                self.handle_issues()
            elif path == '/stream':
                self.handle_stream()
            else:
                self.send_error(404, "Not found")
        
        except Exception as e:
            print(f"Error handling request: {e}", file=sys.stderr)
            self.send_error(500, str(e))
    
    def handle_health(self):
        """Health check endpoint."""
        response = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "build-monitor"
        }
        self.send_json_response(response)
    
    def handle_logs(self, lines: int):
        """Get recent logs."""
        logs = self.server.log_streamer.get_recent_logs(lines)
        response = {
            "logs": logs,
            "count": len(logs)
        }
        self.send_json_response(response)
    
    def handle_status(self):
        """Get current status."""
        status = self.server.log_streamer.get_status()
        issues = self.server.issue_detector.get_issues(unresolved_only=True)
        status['issues'] = issues
        self.send_json_response(status)
    
    def handle_issues(self):
        """Get detected issues."""
        issues = self.server.issue_detector.get_issues()
        response = {
            "issues": issues,
            "count": len(issues)
        }
        self.send_json_response(response)
    
    def handle_stream(self):
        """Stream logs via Server-Sent Events."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        
        try:
            last_count = 0
            while True:
                logs = self.server.log_streamer.get_recent_logs()
                new_logs = logs[last_count:]
                
                for log in new_logs:
                    data = f"data: {json.dumps(log)}\n\n"
                    self.wfile.write(data.encode())
                    self.wfile.flush()
                
                last_count = len(logs)
                time.sleep(0.5)
                
        except (BrokenPipeError, ConnectionResetError):
            pass
    
    def send_json_response(self, data: Any):
        """Send JSON response."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


def log_to_file(filepath: Path, line: str):
    """Append line to log file."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def main():
    """Main entry point."""
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get container name from environment or use default
    container_name = os.environ.get("BUILD_CONTAINER_NAME", "app")
    
    # Initialize components
    log_streamer = LogStreamer(container_name=container_name)
    issue_detector = IssueDetector(log_streamer)
    
    # Start log streaming
    log_streamer.start()
    
    # Start issue detection in background
    detector_thread = threading.Thread(
        target=issue_detector.check_logs_for_issues,
        daemon=True
    )
    detector_thread.start()
    
    # Start HTTP API
    server = HTTPServer(('0.0.0.0', HTTP_PORT), BuildMonitorHandler)
    server.log_streamer = log_streamer
    server.issue_detector = issue_detector
    
    log_streamer.log_line(f"Build Monitor API listening on port {HTTP_PORT}", "info")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log_streamer.log_line("Shutting down...", "info")
        log_streamer.stop()
        issue_detector.stop()
        server.shutdown()


if __name__ == '__main__':
    main()
