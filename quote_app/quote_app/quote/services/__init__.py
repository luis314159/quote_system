# Import all services to make them available when importing from the services package
from .quote_generator import QuoteGenerator
from .email_service import send_quote_email

__all__ = [
    'QuoteGenerator',
    'send_quote_email',
]