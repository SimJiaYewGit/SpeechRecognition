"""Single-model Linux serving configuration for the backend container."""

import os

bind = f"0.0.0.0:{int(os.environ.get('PORT', '5000'))}"
workers = 1
worker_class = "gthread"
threads = 4
# Other threads can answer health/list requests while the inference lock is held.
# This is worker liveness tolerance, not a hard per-request deadline for gthread.
timeout = 600
graceful_timeout = 600
keepalive = 5
preload_app = False
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
# Omit query strings/filenames and response bodies from routine access logs.
access_log_format = '%(h)s %(m)s %(U)s %(s)s %(L)s'
