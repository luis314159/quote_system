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

from ..services.pdf_conversion_service import PDFConverter

# Configure logging
logger = logging.getLogger(__name__)

def send_excel_quote_email(customer_excel_content, internal_excel_content, project_name, user_email, internal_email_addr, project_data, company):
    """Send quote Excel to customer and internal email using direct SMTP with optional PDF conversion."""
    try:
        # Check if PDF conversion is supported
        pdf_supported = PDFConverter.is_conversion_supported()
        format_type = 'Excel & PDF' if pdf_supported else 'Excel'
        
        logger.info("=" * 50)
        logger.info(f"STARTING EMAIL SENDING PROCESS WITH DIRECT SMTP ({format_type} FORMAT)")
        logger.info("=" * 50)
        
        # Convert Excel to PDF if supported
        customer_pdf_content = None
        internal_pdf_content = None
        
        if pdf_supported:
            logger.info("Attempting to convert Excel files to PDF...")
            customer_pdf_content = PDFConverter.convert_excel_to_pdf(customer_excel_content)
            internal_pdf_content = PDFConverter.convert_excel_to_pdf(internal_excel_content)
            
            if customer_pdf_content:
                logger.info("✅ Customer PDF generated successfully")
            else:
                logger.warning("⚠️ Failed to generate customer PDF")
                
            if internal_pdf_content:
                logger.info("✅ Internal PDF generated successfully")
            else:
                logger.warning("⚠️ Failed to generate internal PDF")

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
            'format_type': format_type  # Indicator of the format (Excel or Excel & PDF)
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

        # Generate base filename for attachments
        base_filename = f"Grupo_ARGA_Quote_{project_name.strip().replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}"
        
        # Attach Excel for customer
        customer_excel = MIMEApplication(
            customer_excel_content, 
            _subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        excel_filename = f"{base_filename}.xlsx"
        customer_excel.add_header('Content-Disposition', 'attachment', filename=excel_filename)
        msg.attach(customer_excel)
        
        # Attach PDF for customer if available
        if customer_pdf_content:
            customer_pdf = MIMEApplication(customer_pdf_content, _subtype='pdf')
            pdf_filename = f"{base_filename}.pdf"
            customer_pdf.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
            msg.attach(customer_pdf)

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

        # Generate base filename for internal attachments
        internal_base_filename = f"Grupo_ARGA_Quote_INTERNAL_{project_name.strip().replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}"
        
        # Attach internal Excel
        internal_excel = MIMEApplication(
            internal_excel_content, 
            _subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        internal_excel_filename = f"{internal_base_filename}.xlsx"
        internal_excel.add_header('Content-Disposition', 'attachment', filename=internal_excel_filename)
        msg_internal.attach(internal_excel)
        
        # Attach internal PDF if available
        if internal_pdf_content:
            internal_pdf = MIMEApplication(internal_pdf_content, _subtype='pdf')
            internal_pdf_filename = f"{internal_base_filename}.pdf"
            internal_pdf.add_header('Content-Disposition', 'attachment', filename=internal_pdf_filename)
            msg_internal.attach(internal_pdf)

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
        logger.info(f"Format type: {format_type}")
        
        attachment_info = f"Excel: {excel_filename}"
        if customer_pdf_content:
            attachment_info += f", PDF: {pdf_filename}"
        logger.info(f"Customer attachments: {attachment_info}")
        
        internal_attachment_info = f"Excel: {internal_excel_filename}"
        if internal_pdf_content:
            internal_attachment_info += f", PDF: {internal_pdf_filename}"
        logger.info(f"Internal attachments: {internal_attachment_info}")

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

# Maintain the original function for compatibility
def send_quote_email(customer_pdf_content, internal_pdf_content, project_name, user_email, internal_email_addr, project_data, company):
    """Original PDF quote sender function (kept for backward compatibility)"""
    logger.warning("Using deprecated PDF quote sending function - consider migrating to Excel format")
    # This is a reference to the original implementation
    # We're just forwarding to the new function to maintain compatibility
    return send_excel_quote_email(customer_pdf_content, internal_pdf_content, project_name, user_email, internal_email_addr, project_data, company)