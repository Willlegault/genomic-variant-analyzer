"""Gunicorn settings, loaded automatically when gunicorn starts in backend/.

One process keeps the NCBI throttle in clinvar.py accurate (it is per process);
a few threads let a quick request through while another waits on ClinVar.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1
worker_class = "gthread"
threads = 4

# An analysis spends at most ~20 s on ClinVar (CLINVAR_TIME_BUDGET in app.py);
# leave headroom over that instead of gunicorn's 30 s default.
timeout = 60

accesslog = "-"
