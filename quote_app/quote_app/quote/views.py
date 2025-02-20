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

from .models import (
    MaterialDensity, Company, CompanyMaterialPrice, 
    CompanyFinishPrice, Finish
)
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
            result_df = analyze_step_file(file, './data/csv')
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
        
        company = request.user.company
        
        # Obtener materiales disponibles para la empresa con sus densidades y precios
        available_materials = []
        for material_price in CompanyMaterialPrice.objects.filter(
            company=company,
            is_active=True
        ).select_related('material'):
            material = material_price.material
            available_materials.append({
                'id': material.id,
                'name': material.name or material.get_material_type_display(),
                'material_type': material.material_type,
                'density': material.density,
                'price_per_lb': float(material_price.price_per_lb)
            })
        logger.debug(f"Available materials for company {company.name}: {available_materials}")
        
        # Obtener y loguear los acabados disponibles y sus precios
        finish_prices = {
            price.finish.name: float(price.price_multiplier)
            for price in CompanyFinishPrice.objects.filter(
                company=company,
                is_active=True
            )
        }
        logger.debug(f"Company finish prices: {finish_prices}")
        
        # Preparar y loguear el contexto
        context = {
            'table_data': df.to_dict('records'),
            'available_materials': available_materials,
            'finish_prices': finish_prices,
            'available_finishes': [
                {'id': f.id, 'name': f.name} 
                for f in company.finishes.filter(
                    company_prices__is_active=True
                )
            ]
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
        """Calculate costs for all components considering material weight, quantity and price per pound."""
        costs_data = []
        total_volume = 0
        total_weight = 0
        total_cost = 0

        # Obtener precios de materiales para la empresa
        material_prices = {
            cp.material.id: {
                'price_per_lb': float(cp.price_per_lb),
                'density': cp.material.density,
                'name': cp.material.name or cp.material.get_material_type_display()
            }
            for cp in CompanyMaterialPrice.objects.filter(
                company=self.company,
                is_active=True
            ).select_related('material')
        }

        for comp, mat_id, qty, vol in zip(
            self.project_data['components'],
            self.project_data['materials'],
            self.project_data['quantities'],
            self.project_data['volumes']
        ):
            try:
                # Convert values to appropriate types
                volume = float(vol)
                quantity = int(qty)
                mat_id = int(mat_id)
                
                if mat_id not in material_prices:
                    logger.warning(f"No price found for material ID {mat_id} in company {self.company.name}")
                    continue
                    
                material_data = material_prices[mat_id]
                
                # Calculate weight using material density
                weight = volume * material_data['density']  # Weight per unit in pounds
                
                # Calculate costs
                unit_cost = weight * material_data['price_per_lb']  # Cost for one unit
                subtotal = unit_cost * quantity  # Cost for all units of this component
                
                # Apply finish multiplier if specified
                finish_name = self.project_data.get('project_finish')
                finish_multiplier = 1.0
                
                if finish_name:
                    try:
                        finish_price = CompanyFinishPrice.objects.get(
                            company=self.company,
                            finish__name=finish_name,
                            is_active=True
                        )
                        finish_multiplier = float(finish_price.price_multiplier)
                        subtotal *= finish_multiplier
                    except CompanyFinishPrice.DoesNotExist:
                        logger.warning(f"No finish price found for {finish_name} in company {self.company.name}")
                
                # Update totals
                total_volume += volume * quantity
                total_weight += weight * quantity
                total_cost += subtotal
                
                costs_data.append({
                    'component': comp,
                    'material': material_data['name'],
                    'quantity': quantity,
                    'volume': volume,
                    'weight': weight,
                    'unit_cost': unit_cost,
                    'subtotal': subtotal,
                    'price_per_pound': material_data['price_per_lb'],
                    'finish_multiplier': finish_multiplier
                })
                
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing component {comp}: {str(e)}")
                continue
        
        return costs_data, total_volume, total_weight, total_cost

    
    
    def _add_customer_components_table(self):
        """Simplified table for customer view - without unit costs"""
        costs_data, _, total_weight, total_cost = self.calculate_component_costs()
        
        items_data = [['Component', 'Material', 'Quantity']]
        
        for item in costs_data:
            items_data.append([
                item['component'],
                item['material'],
                f"{item['quantity']:,d}"
            ])
        
        # Add totals row
        items_data.append([
            'TOTALS',
            '',
            '',
        ])

        components_table = Table(items_data, colWidths=[3*inch, 2.5*inch, 2*inch])
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
        """Detailed table for internal use - includes all cost details"""
        costs_data, total_volume, total_weight, total_cost = self.calculate_component_costs()
        
        items_data = [[
            'Component', 
            'Material', 
            'Qty',
            'Volume (in³)',
            'Weight (lb)',
            'Price/lb',
            'Unit Cost',
            'Subtotal'
        ]]
        
        for item in costs_data:
            items_data.append([
                item['component'],
                item['material'],
                f"{item['quantity']:,d}",
                f"{item['volume']:,.2f}",
                f"{item['weight']:,.2f}",
                f"${item['price_per_pound']:,.2f}",
                f"${item['unit_cost']:,.2f}",
                f"${item['subtotal']:,.2f}"
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
            colWidths=[1.2*inch, 1.2*inch, 0.6*inch, 0.9*inch, 0.9*inch, 0.8*inch, 0.9*inch, 1*inch]
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

def send_quote_email(customer_pdf_content, internal_pdf_content, project_name, user_email, internal_email_addr, project_data, company):
    """Send quote PDF to customer and internal email using direct SMTP."""
    try:
        logger.info("=" * 50)
        logger.info("INICIANDO PROCESO DE ENVÍO DE CORREO CON SMTP DIRECTO")
        logger.info("=" * 50)

        # Preparar mensaje para el cliente
        msg = MIMEMultipart('alternative')
        msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
        msg["To"] = user_email
        msg["Subject"] = f"Your Quote for Project: {project_name}"

        # Contexto para las plantillas
        email_context = {
            'project_name': project_name,
            'company_name': company.name,
            'contact_name': company.contact_name,
            'contact_email': company.contact_email,
            'project_finish': project_data.get('project_finish', 'None')
        }

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

        # Preparar mensaje interno
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
        logger.info("=" * 80)
        logger.info("INICIANDO GENERACIÓN DE COTIZACIÓN")
        logger.info("=" * 80)
        
        if not request.user.is_authenticated:
            logger.warning("Usuario no autenticado")
            return redirect('login')
            
        if not request.user.company:
            logger.warning("Usuario no asociado a una empresa")
            return render(request, 'quote/error.html', {
                'error': 'Usuario no asociado a una empresa'
            })

        # Log request data for debugging
        logger.info("Datos POST recibidos:")
        logger.info(f"Nombre del proyecto: {request.POST.get('project_name')}")
        logger.info(f"Acabado del proyecto: {request.POST.get('project_finish')}")
        logger.info(f"Componentes: {request.POST.getlist('components[]')}")
        logger.info(f"Materiales: {request.POST.getlist('materials[]')}")
        logger.info(f"Cantidades: {request.POST.getlist('quantities[]')}")
        logger.info(f"Volúmenes: {request.POST.getlist('volumes[]')}")

        # Validar datos recibidos
        if not all([
            request.POST.getlist('components[]'),
            request.POST.getlist('materials[]'),
            request.POST.getlist('quantities[]'),
            request.POST.getlist('volumes[]')
        ]):
            logger.error("❌ Faltan datos requeridos en el formulario")
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

        logger.info("Generando PDF para cliente...")
        customer_quote_generator = QuoteGenerator(request.user, project_data, is_internal=False)
        customer_pdf_content = customer_quote_generator.generate_pdf()
        logger.info("✅ PDF de cliente generado exitosamente")

        logger.info("Generando PDF interno...")
        internal_quote_generator = QuoteGenerator(request.user, project_data, is_internal=True)
        internal_pdf_content = internal_quote_generator.generate_pdf()
        logger.info("✅ PDF interno generado exitosamente")

        logger.info("Enviando correos electrónicos...")
        email_sent = send_quote_email(
            customer_pdf_content,
            internal_pdf_content,
            project_data['project_name'],
            request.user.company.contact_email,
            settings.INTERNAL_QUOTE_EMAIL,
            project_data,
            request.user.company
        )

        if email_sent:
            logger.info("✅ Cotización generada y enviada exitosamente")
            return JsonResponse({
                'status': 'success',
                'message': 'Quote has been sent to your email'
            })
        else:
            logger.error("❌ Error al enviar los correos electrónicos")
            return JsonResponse({
                'status': 'error',
                'message': 'Error sending email'
            }, status=500)

    except Exception as e:
        logger.error("❌ Error en la generación de la cotización:")
        logger.error(f"Tipo de error: {type(e).__name__}")
        logger.error(f"Mensaje de error: {str(e)}")
        logger.error("Stacktrace:", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Error generating quote: {str(e)}'
        }, status=500)