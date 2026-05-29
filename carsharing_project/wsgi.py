"""
WSGI config for carsharing_project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carsharing_project.settings")

application = get_wsgi_application()
