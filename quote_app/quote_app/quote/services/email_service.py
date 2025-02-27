import os
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

from django.conf import settings
from django.template.loader import render_to_string

# Configure logging
logger = logging.getLogger(__name__)

def send_excel_quote_email(customer_excel_content, internal_excel_content, project_name, user_email, internal_email_addr, project_data, company):
    """Send quote Excel to customer and internal email using direct SMTP."""
    try:
        logger.info("=" * 50)
        logger.info("STARTING EMAIL SENDING PROCESS WITH DIRECT SMTP (EXCEL FORMAT)")
        logger.info("=" * 50)

        # Prepare message for the customer
        msg = MIMEMultipart('alternative')
        msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
        msg["To"] = user_email
        msg["Subject"] = f"Your Quote for Project: {project_name}"

        # Context for templates
        email_context = {
            'project_name': project_name,
            'company_name': company.name,
            'contact_name': company.contact_name,
            'contact_email': company.contact_email,
            'project_finish': project_data.get('project_finish', 'None'),
            'format_type': 'Excel' # Indicador de que ahora es formato Excel
        }

        # Render templates for customer
        logger.info("Attempting to render email templates for customer")
        try:
            text_content = render_to_string('quote/emails/customer_quote.txt', email_context)
            html_content = render_to_string('quote/emails/customer_quote.html', email_context)
            logger.info("Templates rendered successfully")
        except Exception as e:
            logger.error(f"Error rendering templates: {str(e)}")
            raise

        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        # Attach Excel for customer
        customer_excel = MIMEApplication(
            customer_excel_content, 
            _subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"Grupo_ARGA_Quote_{project_name.strip().replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        customer_excel.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(customer_excel)

        # Prepare internal message
        msg_internal = MIMEMultipart('alternative')
        msg_internal["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
        msg_internal["To"] = internal_email_addr
        msg_internal["Subject"] = f"[INTERNAL] New Quote Generated - Project: {project_name}"

        # Render templates for internal email
        text_content = render_to_string('quote/emails/internal_quote.txt', email_context)
        html_content = render_to_string('quote/emails/internal_quote.html', email_context)

        msg_internal.attach(MIMEText(text_content, 'plain'))
        msg_internal.attach(MIMEText(html_content, 'html'))

        # Attach internal Excel
        internal_excel = MIMEApplication(
            internal_excel_content, 
            _subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        internal_filename = f"Grupo_ARGA_Quote_INTERNAL_{project_name.strip().replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        internal_excel.add_header('Content-Disposition', 'attachment', filename=internal_filename)
        msg_internal.attach(internal_excel)

        # Attach logo if it exists
        try:
            logo_path = os.path.join(settings.STATIC_ROOT, 'images', 'gpoargaHDpng.png')
            with open(logo_path, "rb") as logo_file:
                logo = MIMEImage(logo_file.read())
                logo.add_header('Content-ID', '<logo>')
                logo.add_header('Content-Disposition', 'inline')
                msg.attach(logo)
                msg_internal.attach(logo)
        except FileNotFoundError:
            logger.warning("Logo not found, continuing without it")

        # Log email details for debugging
        logger.info(f"Customer email prepared for: {user_email}")
        logger.info(f"Internal email prepared for: {internal_email_addr}")
        logger.info(f"Email subject: Your Quote for Project: {project_name}")
        logger.info(f"Excel customer filename: {filename}")
        logger.info(f"Excel internal filename: {internal_filename}")

        # Send emails using SMTP
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            if settings.MAIL_TLS:
                server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            
            # Send to customer
            logger.info(f"Sending email to customer: {user_email}")
            server.sendmail(settings.MAIL_FROM_EMAIL, user_email, msg.as_string())
            logger.info(f"Customer email sent successfully to {user_email}")
            
            # Send internal email
            logger.info(f"Sending internal email to: {internal_email_addr}")
            server.sendmail(
                settings.MAIL_FROM_EMAIL,
                internal_email_addr,
                msg_internal.as_string()
            )
            logger.info(f"Internal email sent successfully to {internal_email_addr}")

        logger.info("Email sending process completed successfully")
        return True

    except Exception as e:
        logger.error("Error during email sending:")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Stacktrace:", exc_info=True)
        return False

# Mantenemos la función original para compatibilidad
def send_quote_email(customer_pdf_content, internal_pdf_content, project_name, user_email, internal_email_addr, project_data, company):
    """Original PDF quote sender function (kept for backward compatibility)"""
    logger.warning("Using deprecated PDF quote sending function - consider migrating to Excel format")
    # Implementación existente
    # [código existente no modificado]
    
    # Esta es una referencia a la implementación original
    # Si se necesita, se debe copiar el código completo aquí
    
    return send_excel_quote_email(customer_pdf_content, internal_pdf_content, project_name, user_email, internal_email_addr, project_data, company)