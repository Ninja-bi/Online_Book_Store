"""
WSGI config for Book_Store project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os
import sys
import traceback
from pathlib import Path

# Add project root and inner directory to sys.path so Vercel runtime can find Book_Store and all local apps
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Book_Store.settings')

try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception as _e:
    _err_msg = traceback.format_exc()
    print("CRITICAL: Failed to initialize Django WSGI application:\n", _err_msg, file=sys.stderr)

    def application(environ, start_response):
        status = '500 Internal Server Error'
        body = f"Django Startup Error:\n\n{_err_msg}".encode('utf-8')
        response_headers = [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Length', str(len(body)))
        ]
        start_response(status, response_headers)
        return [body]

app = application

