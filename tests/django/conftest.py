import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.django_settings")

django.setup()
