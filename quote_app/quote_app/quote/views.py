import json
from django.core.mail import EmailMessage
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.conf import settings
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.enums import TA_LEFT
from datetime import datetime, timedelta
from io import BytesIO
import os
import logging
from django.views.decorators.http import require_http_methods
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .models import MaterialDensity
from utils.step_analyzer import analyze_step_file

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def home(request: HttpRequest):
    return render(request, 'quote/home.html')

def contact(request: HttpRequest):
    return render(request, 'quote/contact.html')

def about(request: HttpRequest):
    return render(request, 'quote/about.html')


def upload_step(request: HttpRequest):
    if request.method == 'POST':
        if 'step_file' not in request.FILES:
            return render(request, 'upload.html', {'error': 'No file selected'})
            
        file = request.FILES['step_file']
        if not file.name.lower().endswith(('.step', '.stp')):
            return render(request, 'upload.html', {'error': 'Invalid file type'})
            
        try:
            # Process STEP file here
            result_df = analyze_step_file(file, "F://aethersoft//quote_app//quote_app//quote_app//data//csv")
            # Store the DataFrame in the session
            request.session['result_data'] = result_df.to_dict('records')
            return redirect('quote:results')
        except Exception as e:
            return render(request, 'quote/upload.html', {'error': str(e)})
            
    return render(request, 'quote/upload.html')

def results(request: HttpRequest):
    logger.debug("Request received for results.")
    
    if not request.session.get('result_data'):
        logger.debug("Session does not contain 'result_data'. Redirecting to 'upload'.")
        return redirect('upload')
    
    if not request.user.is_authenticated:
        logger.debug("User is not authenticated. Redirecting to 'login'.")
        return redirect('login')
    
    if not request.user.company:
        logger.debug("User is not associated with any company.")
        return render(request, 'quote/error.html', {
            'error': 'Usuario no asociado a una empresa'
        })
    
    try:
        # Obtener y loguear los datos de la sesión
        result_data = request.session['result_data']
        logger.debug(f"Session 'result_data': {result_data}")
        
        df = pd.DataFrame(result_data)
        
        # Log de las columnas originales
        logger.debug(f"Original DataFrame columns: {df.columns.tolist()}")
        
        # Renombrar columnas y loguear
        df = df.rename(columns={
            'Volume (in³)': 'volume',
            'Component': 'component',
            'Material': 'material',
            'Vertices': 'vertices',
            'Faces': 'faces',
            'Quantity': 'quantity'
        })
        logger.debug(f"Renamed DataFrame columns: {df.columns.tolist()}")
        
        # Obtener y loguear las densidades de materiales
        material_densities = {
            material.material_type: material.density 
            for material in MaterialDensity.objects.all()
        }
        logger.debug(f"Material densities: {material_densities}")
        
        # Obtener y loguear los precios de la empresa
        company = request.user.company
        company_prices = {
            'stainless_steel': company.stainless_steel_price,
            'carbon_steel': company.carbon_steel_price
        }
        logger.debug(f"Company prices for {company.name}: {company_prices}")
        
        # Preparar y loguear el contexto
        context = {
            'table_data': df.to_dict('records'),
            'material_densities': material_densities,
            'company_prices': {
                'stainless_steel': float(company.stainless_steel_price),
                'carbon_steel': float(company.carbon_steel_price)
            }
        }
        logger.debug(f"Context prepared for rendering: {context}")
        
        return render(request, 'quote/results.html', context)
        
    except Exception as e:
        logger.error(f"Error processing results: {str(e)}", exc_info=True)
        return render(request, 'quote/error.html', {
            'error': f'Error procesando resultados: {str(e)}'
        })

def update_material(request: HttpRequest):
    if request.method == 'POST':
        data = json.loads(request.body)
        component = data.get('component')
        new_material = data.get('material')
        
        # Obtener los datos actuales
        result_data = request.session.get('result_data', [])
        df = pd.DataFrame(result_data)
        
        # Actualizar el material para el componente específico
        df.loc[df['Component'] == component, 'Material'] = new_material
        
        # Recalcular volúmenes por material
        df = df.rename(columns={
            'Volume (in³)': 'volume',
            'Component': 'component',
            'Material': 'material',
            'Vertices': 'vertices',
            'Faces': 'faces',
            'Quantity': 'quantity'
        })
        
        volume_by_material = df.groupby('material').apply(
            lambda x: (x['volume'] * x['quantity']).sum()
        ).round(2).to_dict()
        
        # Guardar datos actualizados en la sesión
        request.session['result_data'] = df.to_dict('records')
        
        return JsonResponse({
            'success': True,
            'volume_by_material': volume_by_material,
            'total_volume': sum(volume_by_material.values())
        })
    
    return JsonResponse({'success': False}, status=400)

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.enums import TA_LEFT
from datetime import datetime, timedelta
from io import BytesIO
import os
import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

logger = logging.getLogger(__name__)

class QuoteGenerator:
    def __init__(self, user, project_data, is_internal=False):
        self.user = user
        self.company = user.company
        self.project_data = project_data
        self.elements = []
        self.styles = getSampleStyleSheet()
        self.is_internal = is_internal  # Flag para diferenciar el tipo de PDF
        self.setup_custom_styles()
    
        self.material_densities = {
            material.material_type: material.density 
            for material in MaterialDensity.objects.all()
        }

    def setup_custom_styles(self):
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_LEFT,
            spaceAfter=30,
            textColor=colors.black
        )
        
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            alignment=TA_LEFT,
            spaceAfter=20,
            textColor=colors.black
        )

    def create_first_page(self):
        # Add logo
        logo_path = os.path.join(settings.STATIC_ROOT, 'images', 'gpoargaHDpng.png')
        if os.path.exists(logo_path):
            logo = Image(logo_path)
            logo.drawHeight = 1.2*inch
            logo.drawWidth = 3*inch
            self.elements.append(logo)
        
        self.elements.append(Spacer(1, 20))
        
        # Add header
        self._add_header()
        
        # Add company and quote info
        self._add_company_info()
        
        # Add project summary
        self._add_project_summary()

    def _add_project_summary(self):
        """Add project summary section to the PDF."""
        # Calculate costs using the new calculation method
        costs_data, total_volume, total_weight, total_cost = self.calculate_component_costs()
        
        # Create summary data
        summary_data = [
            ['Project Summary'],
            [f'Total Components: {len(self.project_data["components"])}'],
            [f'Total Weight: {total_weight:,.2f} lbs'],
            [f'Total Price: ${total_cost:,.2f} USD'],
            ['Material Distribution:'],
        ]
        
        # Count materials
        material_counts = {}
        for mat in self.project_data['materials']:
            material_counts[mat] = material_counts.get(mat, 0) + 1
        
        for mat, count in material_counts.items():
            summary_data.append([f'- {mat.replace("_", " ").title()}: {count} components'])

        summary_table = Table(summary_data, colWidths=[7.5*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ]))
        self.elements.append(summary_table)
        self.elements.append(Spacer(1, 20))

    def _add_header(self):
        header = Table([
            [Paragraph("GRUPO ARGA", self.title_style)],
            [Paragraph("QUOTE", self.title_style)],
            [Paragraph(f"Project: {self.project_data['project_name']}", self.subtitle_style)]
        ], colWidths=[7.5*inch])
        self.elements.append(header)
        self.elements.append(Spacer(1, 20))

    def _add_company_info(self):
        quote_number = datetime.now().strftime("%Y%m%d-1")
        current_date = datetime.now()
        valid_date = current_date + timedelta(days=30)

        company_info = [
            ['Customer:', self.company.name],
            ['Contact:', self.company.contact_name],
            ['Email:', self.company.contact_email],
            ['Phone:', self.company.contact_phone],
            ['Address:', self.company.address]
        ]

        quote_info = [
            ['Date:', current_date.strftime('%B %d, %Y')],
            ['Valid until:', valid_date.strftime('%B %d, %Y')],
            ['Quote No:', quote_number],
            ['Rev:', '1']
        ]

        self._create_info_tables(company_info, quote_info)

    def calculate_component_costs(self):
        """Calculate costs for all components considering material weight."""
        costs_data = []
        total_volume = 0
        total_weight = 0
        total_cost = 0

        for comp, mat, qty, vol in zip(
            self.project_data['components'],
            self.project_data['materials'],
            self.project_data['quantities'],
            self.project_data['volumes']
        ):
            volume = float(vol)
            quantity = float(qty)
            
            # Get material density and calculate weight
            density = self.material_densities.get(mat, 0.284)  # Default density if not found
            weight = volume * density
            
            # Get appropriate price per pound based on material
            if mat == 'stainless_steel':
                price_per_pound = float(self.company.stainless_steel_price)
            elif mat == 'carbon_steel':
                price_per_pound = float(self.company.carbon_steel_price)
            else:
                # Default to carbon steel price for unknown materials
                price_per_pound = float(self.company.carbon_steel_price)
            
            # Calculate costs based on weight
            unit_cost = weight * price_per_pound
            total_item_cost = unit_cost * quantity
            
            # Update totals
            total_volume += volume * quantity
            total_weight += weight * quantity
            total_cost += total_item_cost
            
            costs_data.append({
                'component': comp,
                'material': mat,
                'quantity': quantity,
                'volume': volume,
                'weight': weight,
                'unit_cost': unit_cost,
                'total_cost': total_item_cost,
                'price_per_pound': price_per_pound
            })
        
        return costs_data, total_volume, total_weight, total_cost

    def _add_customer_components_table(self):
        """Simplified table for customer view"""
        costs_data, _, _, total_cost = self.calculate_component_costs()
        
        items_data = [['Component', 'Material', 'Quantity']]
        
        for item in costs_data:
            items_data.append([
                item['component'],
                item['material'].replace('_', ' ').title(),
                f"{item['quantity']:,.0f}",
                #f"${item['total_cost']:,.2f}"
            ])
        
        # Add total row
        # items_data.append([
        #     'TOTAL',
        #     '',
        #     '',
        #     f"${total_cost:,.2f}"
        # ])

        components_table = Table(items_data, colWidths=[2.5*inch, 2*inch, 1.5*inch, 1.5*inch])
        components_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        self.elements.append(components_table)

    def _create_info_tables(self, company_info, quote_info):
        left_table = Table(company_info, colWidths=[1.5*inch, 3*inch])
        right_table = Table(quote_info, colWidths=[1.5*inch, 2*inch])
        
        table_style = TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ])
        
        left_table.setStyle(table_style)
        right_table.setStyle(table_style)

        main_table = Table([[left_table, right_table]], colWidths=[4.5*inch, 3*inch])
        self.elements.append(main_table)
        self.elements.append(Spacer(1, 20))

    def create_second_page(self):
        self.elements.append(PageBreak())
        self._add_components_table()

    def _add_components_table(self):
        self.elements.append(Paragraph("Components Details", self.styles['Heading2']))
        self.elements.append(Spacer(1, 20))

        if self.is_internal:
            self._add_internal_components_table()
        else:
            self._add_customer_components_table()


    def _add_internal_components_table(self):
        """Detailed table for internal use"""
        costs_data, total_volume, total_weight, total_cost = self.calculate_component_costs()
        
        items_data = [[
            'Component', 
            'Material', 
            'Quantity',
            'Volume (in³)',
            'Weight (lbs)',
            'Price/lb',
            'Unit Cost',
            'Total Cost'
        ]]
        
        for item in costs_data:
            items_data.append([
                item['component'],
                item['material'].replace('_', ' ').title(),
                f"{item['quantity']:,.0f}",
                f"{item['volume']:,.2f}",
                f"{item['weight']:,.2f}",
                f"${item['price_per_pound']:,.2f}",
                f"${item['unit_cost']:,.2f}",
                f"${item['total_cost']:,.2f}"
            ])
        
        # Add totals row
        items_data.append([
            'TOTALS',
            '',
            '',
            f"{total_volume:,.2f}",
            f"{total_weight:,.2f}",
            '',
            '',
            f"${total_cost:,.2f}"
        ])

        components_table = Table(
            items_data,
            colWidths=[1.5*inch, 1.2*inch, 0.7*inch, 0.9*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.9*inch]
        )
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, -1), (-1, -1), colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
        ])
        
        components_table.setStyle(table_style)
        self.elements.append(components_table)

    def generate_pdf(self):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        self.create_first_page()
        self.create_second_page()
        
        doc.build(self.elements, onFirstPage=self.add_footer, onLaterPages=self.add_footer)
        
        return buffer.getvalue()

    @staticmethod
    def add_footer(canvas, doc):
        canvas.saveState()
        styles = getSampleStyleSheet()
        
        footer_text = Table([
            [
                Paragraph('GRUPO ARGA', styles['Heading4']),
                Paragraph('Calle Valle de Aldama y\nLibramiento Oriente 24302\nChih. Mexico 31376', styles['Normal']),
                Paragraph('alan_ruiz@grupoarga.com\nwww.grupoarga.com\n+52 614 189 17 29', styles['Normal'])
            ]
        ], colWidths=[2*inch, 3*inch, 2.5*inch])
        
        footer_text.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        footer_text.wrapOn(canvas, doc.width, doc.bottomMargin)
        footer_text.drawOn(canvas, doc.leftMargin, doc.bottomMargin - 30)
        
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(7.5*inch, 0.5*inch, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

def send_quote_email(customer_pdf_content, internal_pdf_content, project_name, user_email, internal_email_addr, project_data, company, material_densities):
    """Send quote PDF to customer and internal email using direct SMTP."""
    try:
        logger.info("=" * 50)
        logger.info("INICIANDO PROCESO DE ENVÍO DE CORREO CON SMTP DIRECTO")
        logger.info("=" * 50)

        # Preparar datos para las plantillas
        components_data = []
        total_volume = 0
        total_weight = 0
        total_cost = 0

        for comp, mat, qty, vol in zip(
            project_data['components'],
            project_data['materials'],
            project_data['quantities'],
            project_data['volumes']
        ):
            # Calcular precio unitario según el material
            unit_price = (
                float(company.stainless_steel_price) 
                if mat == 'stainless_steel'
                else float(company.carbon_steel_price)
            )
            
            # Calcular peso usando la densidad del material
            density = material_densities.get(mat, 0.284)  # 0.284 lbs/in³ como valor por defecto
            weight = float(vol) * density
            
            # Calcular costos
            total_item_cost = unit_price * float(qty)
            
            components_data.append({
                'component': comp,
                'material': mat.replace('_', ' ').title(),
                'quantity': qty,
                'volume': float(vol),
                'weight': weight,
                'unit_cost': unit_price,
                'total_cost': total_item_cost
            })
            
            total_volume += float(vol) * float(qty)
            total_weight += weight * float(qty)
            total_cost += total_item_cost

        # Contexto para las plantillas
        email_context = {
            'project_name': project_name,
            'components': components_data,
            'total_components': len(components_data),
            'total_volume': total_volume,
            'total_weight': total_weight,
            'total_cost': total_cost,
            'company_name': company.name,
            'contact_name': company.contact_name,
            'contact_email': company.contact_email
        }

        # Crear mensaje para el cliente
        msg = MIMEMultipart('alternative')
        msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
        msg["To"] = user_email
        msg["Subject"] = f"Your Quote for Project: {project_name}"

        # Renderizar plantillas para el cliente
        logger.info("Intentando renderizar plantillas de correo para cliente")
        try:
            text_content = render_to_string('quote/emails/customer_quote.txt', email_context)
            html_content = render_to_string('quote/emails/customer_quote.html', email_context)
            logger.info("Plantillas renderizadas exitosamente")
        except Exception as e:
            logger.error(f"Error renderizando plantillas: {str(e)}")
            raise

        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        # Adjuntar PDF para cliente
        customer_pdf = MIMEApplication(customer_pdf_content, _subtype='pdf')
        filename = f"Grupo_ARGA_Quote_{project_name.strip().replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.pdf"
        customer_pdf.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(customer_pdf)

        # Preparar mensaje interno con PDF detallado
        msg_internal = MIMEMultipart('alternative')
        msg_internal["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
        msg_internal["To"] = internal_email_addr
        msg_internal["Subject"] = f"[INTERNAL] New Quote Generated - Project: {project_name}"

        # Renderizar plantillas para correo interno
        text_content = render_to_string('quote/emails/internal_quote.txt', email_context)
        html_content = render_to_string('quote/emails/internal_quote.html', email_context)

        msg_internal.attach(MIMEText(text_content, 'plain'))
        msg_internal.attach(MIMEText(html_content, 'html'))

        # Adjuntar PDF interno
        internal_pdf = MIMEApplication(internal_pdf_content, _subtype='pdf')
        internal_filename = f"Grupo_ARGA_Quote_INTERNAL_{project_name.strip().replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.pdf"
        internal_pdf.add_header('Content-Disposition', 'attachment', filename=internal_filename)
        msg_internal.attach(internal_pdf)

        # Adjuntar logo si existe
        try:
            logo_path = os.path.join(settings.STATIC_ROOT, 'images', 'gpoargaHDpng.png')
            with open(logo_path, "rb") as logo_file:
                logo = MIMEImage(logo_file.read())
                logo.add_header('Content-ID', '<logo>')
                logo.add_header('Content-Disposition', 'inline')
                msg.attach(logo)
                msg_internal.attach(logo)
        except FileNotFoundError:
            logger.warning("Logo no encontrado, continuando sin él")

        # Enviar correos usando SMTP
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            if settings.MAIL_TLS:
                server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            
            # Enviar al cliente
            logger.info(f"Enviando correo al cliente: {user_email}")
            server.sendmail(settings.MAIL_FROM_EMAIL, user_email, msg.as_string())
            
            # Enviar correo interno
            logger.info(f"Enviando correo interno a: {internal_email_addr}")
            server.sendmail(
                settings.MAIL_FROM_EMAIL,
                internal_email_addr,
                msg_internal.as_string()
            )

        logger.info("Proceso de envío completado exitosamente")
        return True

    except Exception as e:
        logger.error("Error en el envío de correo:")
        logger.error(f"Tipo de error: {type(e).__name__}")
        logger.error(f"Mensaje de error: {str(e)}")
        logger.error("Stacktrace:", exc_info=True)
        return False
    
@require_http_methods(["POST"])
def generate_quote(request):
    try:
        logger.info("Iniciando generación de cotización")
        
        if not request.user.is_authenticated:
            return redirect('login')
            
        if not request.user.company:
            return render(request, 'quote/error.html', {
                'error': 'Usuario no asociado a una empresa'
            })

        # Collect project data including volumes
        project_data = {
            'project_name': request.POST.get('project_name', 'New Project'),
            'components': request.POST.getlist('components[]'),
            'materials': request.POST.getlist('materials[]'),
            'quantities': request.POST.getlist('quantities[]'),
            'volumes': request.POST.getlist('volumes[]')
        }

        # Get material densities
        material_densities = {
            material.material_type: material.density 
            for material in MaterialDensity.objects.all()
        }

        # Generate customer PDF
        customer_quote_generator = QuoteGenerator(request.user, project_data, is_internal=False)
        customer_pdf_content = customer_quote_generator.generate_pdf()

        # Generate internal PDF
        internal_quote_generator = QuoteGenerator(request.user, project_data, is_internal=True)
        internal_pdf_content = internal_quote_generator.generate_pdf()

        # Send emails with appropriate PDFs
        email_sent = send_quote_email(
            customer_pdf_content,  # PDF para el cliente
            internal_pdf_content,  # PDF para uso interno
            project_data['project_name'],
            request.user.company.contact_email,
            settings.INTERNAL_QUOTE_EMAIL,
            project_data,
            request.user.company,
            material_densities
        )

        if email_sent:
            return JsonResponse({
                'status': 'success',
                'message': 'Quote has been sent to your email'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Error sending email'
            }, status=500)

    except Exception as e:
        logger.error(f"Error generating quote: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Error generating quote: {str(e)}'
        }, status=500)