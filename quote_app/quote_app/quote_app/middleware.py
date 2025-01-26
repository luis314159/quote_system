from django.shortcuts import redirect
from django.urls import resolve
from django.conf import settings
from django.shortcuts import redirect
from django.urls import resolve

class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # URLs que serán accesibles sin autenticación
        self.public_urls = [
            'quote',           # URL principal de cotización
            '/quote/about/',     # About page
            'login',           # Login page
            'register',        # Register page
        ]

    def __call__(self, request):
        # Obtener el nombre de la URL actual
        try:
            current_url_name = resolve(request.path).url_name
            
            # Verificar si el usuario no está autenticado y la URL no es pública
            if not request.user.is_authenticated and current_url_name not in self.public_urls:
                # Redireccionar al login
                return redirect('session:login')
                
        except:
            # Si hay algún error al resolver la URL, redirigir al login
            if not request.user.is_authenticated:
                return redirect('session:login')

        response = self.get_response(request)
        return response