"""AgriSmart Production Gunicorn WSGI Configuration.

Optimized for:
- TensorFlow model memory efficiency (preload_app=True shares model across workers)
- High throughput behind Nginx reverse proxy
- Graceful worker timeouts during ML image inference
"""

import multiprocessing
import os

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5000")
backlog = 2048

# Worker processes
# For ML inference on CPU, (CPU cores * 1) + 1 is optimal to avoid CPU thrashing
cpu_count = multiprocessing.cpu_count()
workers = int(os.getenv("GUNICORN_WORKERS", max(2, min(4, cpu_count))))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", 2))
worker_connections = 1000
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))
keepalive = 5

# CRITICAL FOR TENSORFLOW:
# Preload application in master process before forking workers.
# This shares the 10 MB plant disease model weights via copy-on-write memory,
# preventing memory multiplication across workers.
preload_app = True

# Process naming
proc_name = "agrismart-backend"

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" (%(D)s µs)'

# Security & limits
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

def on_starting(server):
    server.log.info("Starting AgriSmart WSGI Server with Gunicorn...")

def post_fork(server, worker):
    server.log.info(f"Spawned AgriSmart worker process (PID: {worker.pid})")
