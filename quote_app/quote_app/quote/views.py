# Import and re-export all views from the views package
from .views import (
    home,
    contact,
    about, 
    upload_step,
    results,
    update_material,
    generate_quote,
)

# This allows the views to be imported directly from the app module
__all__ = [
    'home',
    'contact',
    'about',
    'upload_step',
    'results', 
    'update_material',
    'generate_quote',
]