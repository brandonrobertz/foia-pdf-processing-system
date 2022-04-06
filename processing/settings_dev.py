import os


DEBUG = True
DEVELOPMENT, PRODUCTION = True, False
DEBUG_TOOLBAR = False

SITE_URL = 'http://localhost:8000'

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'wa_pd_data',
        'USER': 'django',
        'PASSWORD': os.getenv("DJANGO_PASSWORD", "insecure!"),
        'HOST': os.getenv("DB_HOST", "localhost"),
        'PORT': os.getenv("DB_PORT", "5432"),
    }
}
