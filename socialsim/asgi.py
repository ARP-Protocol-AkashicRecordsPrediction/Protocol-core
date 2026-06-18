"""ASGI config for Social Prediction Simulator."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "socialsim.settings")

application = get_asgi_application()

