SECRET_KEY = "test-key"
INSTALLED_APPS = [
    "tests.testapp",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
ROOT_URLCONF = "tests.urls"
USE_TZ = True
MIDDLEWARE = []
ALLOWED_HOSTS = ["*"]
NINJA_JSONAPI = {
    "MAX_INCLUDE_DEPTH": 3,
    "MAX_PAGE_SIZE": 20,
    "ALLOW_DISABLE_PAGINATION": True,
}
