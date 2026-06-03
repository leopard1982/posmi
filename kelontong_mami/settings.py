from pathlib import Path
import os
from .readenv import readEnv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = readEnv('SECRET_KEY')


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = readEnv('DEBUG')



# MIDTRANS_SETTINGS 
MIDTRANS_CLIENT = readEnv('MIDTRANS_CLIENT')
MIDTRANS_SERVER = readEnv('MIDTRANS_SERVER')
MIDTRANS_PRODUCTION = readEnv('MIDTRANS_PRODUCTION')

ALLOWED_HOSTS = ['192.168.1.50','localhost','127.0.0.1']
CSRF_TRUSTED_ORIGINS=['http://localhost:8000','http://127.0.0.1:8000','http://192.168.1.50']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'pos',
    'stock',
    'payment',
    'promo',
    'cara',
    'cms',
    'resep',
    'management',
    'owner',
    'api',
]



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# dipakai untuk setting supaya tidak ada error ketika akses django admin
# akan diganti disesuaikan dengan alamat staging site
# untuk setting.py nya

INTERNAL_IPS = [
'127.0.0.1',
]

ROOT_URLCONF = 'kelontong_mami.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR,'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'kelontong_mami.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': readEnv('DB_ENGINE') or 'django.db.backends.postgresql',
        'NAME': readEnv('DB_NAME'),
        'USER': readEnv('DB_USER'),
        'PASSWORD': readEnv('DB_PASSWORD'),
        'HOST': readEnv('DB_HOST'),
        'PORT': readEnv('DB_PORT'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'id-ID'

TIME_ZONE = 'Asia/Jakarta'

USE_I18N = True

USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS= [os.path.join(BASE_DIR,'static')]
MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR,'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = readEnv('EMAIL_HOST')
EMAIL_USE_TLS = readEnv('EMAIL_USE_TLS')
EMAIL_PORT = int(readEnv('EMAIL_PORT') or 587)
EMAIL_HOST_USER = readEnv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = readEnv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = readEnv('DEFAULT_FROM_EMAIL')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
