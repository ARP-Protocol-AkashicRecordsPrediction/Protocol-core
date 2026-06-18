"""WSGI config for Social Prediction Simulator."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "socialsim.settings")

application = get_wsgi_application()

