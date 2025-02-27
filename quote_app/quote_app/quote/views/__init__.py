# Import all views to make them available when importing from the views package
from .basic_views import home, contact, about
from .file_views import upload_step
from .result_views import results, update_material
from .quote_views import generate_quote

__all__ = [
    'home',
    'contact',
    'about',
    'upload_step',
    'results',
    'update_material',
    'generate_quote',
]