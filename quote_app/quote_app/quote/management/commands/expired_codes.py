from django.core.management.base import BaseCommand
from app.models import RegistrationCode
from django.utils import timezone


class Command(BaseCommand):
    help = 'Eliminar códigos de registro expirados'

    def handle(self, *args, **kwargs):
        expired_codes = RegistrationCode.objects.filter(
            expires_at__lt=timezone.now(),
            is_used=False
        )
        count = expired_codes.count()
        expired_codes.delete()
        self.stdout.write(self.style.SUCCESS(f'Se eliminaron {count} códigos expirados.'))
