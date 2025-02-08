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

class QuoteGenerator:
    def __init__(self, user, project_data):
        self.user = user
        self.company = user.company
        self.project_data = project_data
        self.elements = []
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()

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
        # Calculate total price
        total_price = 0
        for mat, qty in zip(self.project_data['materials'], self.project_data['quantities']):
            unit_price = (
                float(self.company.stainless_steel_price) if mat == 'stainless_steel'
                else float(self.company.carbon_steel_price)
            )
            total_price += unit_price * float(qty)

        # Create summary data
        summary_data = [
            ['Project Summary'],
            [f'Total Components: {len(self.project_data["components"])}'],
            [f'Total Price: ${total_price:,.2f} USD'],
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

    def _create_info_tables(self, company_info, quote_info):
        """Create and add the company and quote info tables to elements."""
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

        # Combine tables side by side
        main_table = Table([[left_table, right_table]], colWidths=[4.5*inch, 3*inch])
        self.elements.append(main_table)
        self.elements.append(Spacer(1, 20))

    def create_second_page(self):
        self.elements.append(PageBreak())
        self._add_components_table()

    def _add_components_table(self):
        self.elements.append(Paragraph("Components Details", self.styles['Heading2']))
        self.elements.append(Spacer(1, 20))

        items_data = [['Component', 'Material', 'Quantity']]
        for comp, mat, qty in zip(
            self.project_data['components'],
            self.project_data['materials'],
            self.project_data['quantities']
        ):
            items_data.append([
                comp,
                mat.replace('_', ' ').title(),
                qty
            ])

        components_table = Table(items_data, colWidths=[3*inch, 2.5*inch, 2*inch])
        components_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 12),
        ]))
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

def send_quote_email(pdf_content, project_data, user, internal_email):
    """
    Send quote PDF to customer and internal email with enhanced information.
    """
    try:
        project_name = project_data['project_name']
        filename = f"Grupo_ARGA_Quote_{project_name.strip().replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Prepare customer email
        customer_context = {
            'company_name': user.company.name,
            'contact_name': user.company.contact_name,
            'project_name': project_name,
            'valid_days': 30,
        }
        customer_body = render_to_string(r'F:\aethersoft\quote_app\quote_app\quote_app\quote\templates\emails\quotes_customer.html', customer_context)
        
        # Customer email
        customer_email = EmailMessage(
            subject=f'Cotización para Proyecto: {project_name}',
            body=customer_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.company.contact_email]
        )
        customer_email.content_subtype = "html"
        customer_email.attach(filename, pdf_content, 'application/pdf')
        customer_email.send()

        # Calculate totals for internal email
        total_price = 0
        material_counts = {}
        for mat, qty in zip(project_data['materials'], project_data['quantities']):
            material_counts[mat] = material_counts.get(mat, 0) + 1
            unit_price = (
                float(user.company.stainless_steel_price) if mat == 'stainless_steel'
                else float(user.company.carbon_steel_price)
            )
            total_price += unit_price * float(qty)

        # Prepare internal email context
        internal_context = {
            'company_name': user.company.name,
            'contact_name': user.company.contact_name,
            'contact_email': user.company.contact_email,
            'contact_phone': user.company.contact_phone,
            'project_name': project_name,
            'total_components': len(project_data['components']),
            'total_price': f"${total_price:,.2f}",
            'material_distribution': material_counts,
            'generated_by': f"{user.first_name} {user.last_name}",
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stainless_price': user.company.stainless_steel_price,
            'carbon_price': user.company.carbon_steel_price
        }
        
        internal_body = render_to_string('F:/aethersoft/quote_app/quote_app/quote_app/quote/emails/quote_internal.html', internal_context)

        # Internal email
        internal_msg = EmailMessage(
            subject=f'Nueva Cotización - {project_name} - {user.company.name}',
            body=internal_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[internal_email]
        )
        internal_msg.content_subtype = "html"
        internal_msg.attach(filename, pdf_content, 'application/pdf')
        internal_msg.send()

        logger.info(f"Quote emails sent successfully for project: {project_name}")
        return True

    except Exception as e:
        logger.error(f"Error sending quote emails: {str(e)}", exc_info=True)
        return False

@require_http_methods(["GET", "POST"])
def generate_quote(request):
    """Generate and email PDF quote with company branding."""
    if request.method == "GET":
        return JsonResponse({
            'status': 'error',
            'message': 'Este endpoint solo acepta peticiones POST'
        }, status=405)

    try:
        if not request.user.is_authenticated:
            return redirect('login')
            
        if not request.user.company:
            return render(request, 'quote/error.html', {
                'error': 'Usuario no asociado a una empresa'
            })

        # Get the result data from session
        result_data = request.session.get('result_data')
        if not result_data:
            return JsonResponse({
                'status': 'error',
                'message': 'No se encontraron datos del proyecto'
            }, status=400)

        # Collect project data from result_data
        df = pd.DataFrame(result_data)
        project_data = {
            'project_name': request.POST.get('project_name', 'New Project'),
            'components': df['Component'].tolist(),
            'materials': df['Material'].tolist(),
            'quantities': df['Quantity'].tolist()
        }

        logger.info(f"Generating quote for project: {project_data['project_name']}")
        logger.debug(f"Project data: {project_data}")

        # Generate PDF
        quote_generator = QuoteGenerator(request.user, project_data)
        pdf_content = quote_generator.generate_pdf()

        # Send emails
        email_sent = send_quote_email(
            pdf_content,
            project_data,
            request.user,
            settings.INTERNAL_QUOTE_EMAIL
        )

        if email_sent:
            # Clear session data after successful quote generation
            request.session.pop('result_data', None)
            return JsonResponse({
                'status': 'success',
                'message': 'La cotización ha sido enviada a su correo electrónico'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Error al enviar el correo electrónico'
            }, status=500)

    except Exception as e:
        logger.error(f"Error generating quote: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Error al generar la cotización: {str(e)}'
        }, status=500)
