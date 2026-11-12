from django.apps import AppConfig
from pathlib import Path


class ScreeningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'screening'

    def ready(self):
        from .dmcore import validate_configuration
        validate_configuration()
        from django.conf import settings
        media_root = Path(getattr(settings, 'INTERVIEW_MEDIA_ROOT', settings.BASE_DIR / 'interview_media'))
        print(f"[Screening] INTERVIEW_MEDIA_ROOT: {media_root.resolve()}")
