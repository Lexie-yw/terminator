# -*- coding: UTF-8 -*-
#
# Copyright 2011, 2013 Leandro Regueiro
#
# This file is part of Terminator.
# 
# Terminator is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
# 
# Terminator is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# Terminator. If not, see <http://www.gnu.org/licenses/>.

import os.path


DEBUG = True

DATABASES = {
    'default': {
        #'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'terminator',                               # Or path to database file if using sqlite3.
        'USER': 'usuario',                                  # Not used with sqlite3.
        'PASSWORD': 'usuario',                              # Not used with sqlite3.
        'HOST' : 'localhost',                               # Set to empty string for localhost. Not used with sqlite3.
        'PORT' : '5432',#'PORT' : '',                                    # Set to empty string for default. Not used with sqlite3.
        #'OPTIONS': {'init_command': 'SET storage_engine=INNODB',}# Only use this for MySQL
    }
}

TIME_ZONE = 'UTC'
USE_TZ = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

LOCALE_PATHS = (
    os.path.join(os.path.dirname(__file__), 'locale').replace('\\', '/'),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'e_d&6)l3hqg+336*+j$id*0s_q5i36webcq@hs4+5uztfuzc)b'


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'compression_middleware.middleware.CompressionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]
ROOT_URLCONF = 'urls'


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
#                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
#                'django.contrib.messages.context_processors.messages',
                'terminator.context_processors.features',
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend', # this is default
    'guardian.backends.ObjectPermissionBackend',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    #'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    #'django.contrib.admindocs',
    'django.contrib.humanize',
    'django_comments',
    'terminator_comments_app',
    'guardian',
    'registration',
    'simple_history',
    'terminator',
)

ACCOUNT_ACTIVATION_DAYS = 7 # One-week activation window; you may, of course, use a different value.

COMMENTS_APP = 'terminator_comments_app'

SEND_NOTIFICATION_EMAILS = True

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
         'require_debug_false': {
              '()': 'django.utils.log.RequireDebugFalse'
         }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

WSGI_APPLICATION = 'wsgi.application'


# Use the following to enable these features
# Also see the settings for Django apps that we use, such as
#  - registration: REGISTRATION_OPEN
FEATURES = {
        'autoterm': True,
        'import_tbx': True,
        'export_tbx': True,
        'proposals': True,
        'subscription': True,
        'collaboration': True,
}


# Get local overrides
try:
    import os.path
    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, "local_settings.py")) as f:
        code = compile(f.read(), "local_settings.py", 'exec')
        exec(code)
except:
    print("Create local_settings.py to provide your configuration options.")
    print("See the Django documentation about settings.\n")
    raise
