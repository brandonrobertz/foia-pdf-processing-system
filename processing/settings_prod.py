import os

print("PROD!")


DEBUG = True
DEVELOPMENT, PRODUCTION = True, False
DEBUG_TOOLBAR = False

ALLOWED_HOSTS = ['wa-pd-records.bxroberts.org']

SITE_URL = 'https://wa-pd-records.bxroberts.org'
MEDIA_ROOT = "/app/data"

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'wa_pd_data',
        'USER': 'django',
        'PASSWORD': os.getenv("DJANGO_PASSWORD", "insecure!"),
        'HOST': 'db',
        'PORT': '5432',
    }
}
