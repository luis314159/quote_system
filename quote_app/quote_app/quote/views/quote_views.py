import json
import logging
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

# Importar los servicios necesarios
from ..services.excel_quote_generator import ExcelQuoteGenerator
from ..services.email_service import send_excel_quote_email

# Configure logging
logger = logging.getLogger(__name__)

@require_http_methods(["POST"])
def generate_quote(request: HttpRequest):
    try:
        logger.info("=" * 80)
        logger.info("STARTING QUOTE GENERATION (EXCEL FORMAT)")
        logger.info("=" * 80)
        
        if not request.user.is_authenticated:
            logger.warning("User not authenticated")
            return redirect('login')
            
        if not request.user.company:
            logger.warning("User not associated with any company")
            return render(request, 'quote/error.html', {
                'error': 'Usuario no asociado a una empresa'
            })

        # Log request data for debugging
        logger.info("POST data received:")
        logger.info(f"Project name: {request.POST.get('project_name')}")
        logger.info(f"Project finish: {request.POST.get('project_finish')}")
        logger.info(f"Components: {request.POST.getlist('components[]')}")
        logger.info(f"Materials: {request.POST.getlist('materials[]')}")
        logger.info(f"Quantities: {request.POST.getlist('quantities[]')}")
        logger.info(f"Volumes: {request.POST.getlist('volumes[]')}")

        # Validate received data
        if not all([
            request.POST.getlist('components[]'),
            request.POST.getlist('materials[]'),
            request.POST.getlist('quantities[]'),
            request.POST.getlist('volumes[]')
        ]):
            logger.error("❌ Missing required form data")
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required form data'
            }, status=400)

        # Collect project data
        project_data = {
            'project_name': request.POST.get('project_name', 'New Project'),
            'project_finish': request.POST.get('project_finish'),
            'components': request.POST.getlist('components[]'),
            'materials': request.POST.getlist('materials[]'),
            'quantities': request.POST.getlist('quantities[]'),
            'volumes': request.POST.getlist('volumes[]')
        }

        logger.info("Generating Excel for customer...")
        customer_quote_generator = ExcelQuoteGenerator(request.user, project_data, is_internal=False)
        customer_excel_content = customer_quote_generator.generate_excel()
        logger.info("✅ Customer Excel generated successfully")

        logger.info("Generating internal Excel...")
        internal_quote_generator = ExcelQuoteGenerator(request.user, project_data, is_internal=True)
        internal_excel_content = internal_quote_generator.generate_excel()
        logger.info("✅ Internal Excel generated successfully")

        # Setup email addresses
        customer_email = request.user.company.contact_email
        internal_email = settings.INTERNAL_QUOTE_EMAIL
        
        logger.info(f"Customer email: {customer_email}")
        logger.info(f"Internal email: {internal_email}")

        logger.info("Sending emails...")
        email_sent = send_excel_quote_email(
            customer_excel_content,
            internal_excel_content,
            project_data['project_name'],
            customer_email,
            internal_email,
            project_data,
            request.user.company
        )

        if email_sent:
            logger.info("✅ Quote generated and sent successfully")
            return JsonResponse({
                'status': 'success',
                'message': 'Quote has been sent to your email'
            })
        else:
            logger.error("❌ Error sending emails")
            return JsonResponse({
                'status': 'error',
                'message': 'Error sending email'
            }, status=500)

    except Exception as e:
        logger.error("❌ Error in quote generation:")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Stacktrace:", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Error generating quote: {str(e)}'
        }, status=500)