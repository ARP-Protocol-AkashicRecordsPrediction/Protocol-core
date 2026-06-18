"""Celery app for asynchronous prediction runs."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "socialsim.settings")

app = Celery("socialsim")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

