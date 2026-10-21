"""
WSGI config for Book_Store project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

# Add project root and inner directory to sys.path so Vercel runtime can find Book_Store and all local apps
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Book_Store.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application

