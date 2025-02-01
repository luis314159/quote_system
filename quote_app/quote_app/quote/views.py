from django.shortcuts import render, redirect
from django.http import HttpRequest
import pandas as pd
from utils import analyze_step_file
from django.http import JsonResponse
import json
from .models import MaterialDensity
import logging
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from decimal import Decimal
from datetime import datetime
from io import BytesIO
from datetime import datetime, timedelta
from decimal import Decimal
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import os

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

@require_http_methods(["POST"])
def generate_quote(request: HttpRequest):
    """Generate professional PDF quote with company branding and improved design."""
    logger.debug("Generating quote PDF")
    
    try:
        if not request.user.is_authenticated:
            return redirect('login')
            
        if not request.user.company:
            return render(request, 'quote/error.html', {
                'error': 'Usuario no asociado a una empresa'
            })

        project_name = request.POST.get('project_name')
        logger.debug(f"Project name received: {project_name}")
        # Get company data
        company = request.user.company
        components = request.POST.getlist('components[]')
        materials = request.POST.getlist('materials[]')
        quantities = request.POST.getlist('quantities[]')
        project_name = request.POST.get('project_name', 'New Project')
        
        # Document setup
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=TA_LEFT,
            spaceAfter=30,
            textColor=colors.black
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=18,
            alignment=TA_LEFT,
            spaceAfter=20,
            textColor=colors.black
        )

        def create_first_page():
            # Add company logo
            logo_path = 'F://aethersoft//quote_app//quote_app//quote_app//static//images//gpoargaHDpng.png'  # Update with actual logo path
            if os.path.exists(logo_path):
                logo = Image(logo_path)
                logo.drawHeight = 1.2*inch
                logo.drawWidth = 3*inch
                elements.append(logo)
            
            elements.append(Spacer(1, 20))

            # Header with company name and project
            header = Table([
                [Paragraph("GRUPO ARGA", title_style)],
                [Paragraph("QUOTE", title_style)],
                [Paragraph(f"Project: {project_name}", subtitle_style)]
            ], colWidths=[7.5*inch])
            elements.append(header)
            elements.append(Spacer(1, 20))

            # Customer info and quote details
            quote_number = datetime.now().strftime("%Y%m%d-1")
            current_date = datetime.now()
            valid_date = current_date + timedelta(days=30)

            left_data = [
                ['Customer:', company.name],
                ['Contact:', company.contact_name],
                ['Email:', company.contact_email],
                ['Phone:', company.contact_phone],
                ['Address:', company.address]
            ]

            right_data = [
                ['Date:', current_date.strftime('%B %d, %Y')],
                ['Valid until:', valid_date.strftime('%B %d, %Y')],
                ['Quote No:', quote_number],
                ['Rev:', '1']
            ]

            # Create tables side by side
            left_table = Table(left_data, colWidths=[1.5*inch, 3*inch])
            right_table = Table(right_data, colWidths=[1.5*inch, 2*inch])
            
            # Style tables
            for table in [left_table, right_table]:
                table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ]))

            main_table = Table([[left_table, right_table]], colWidths=[4.5*inch, 3*inch])
            elements.append(main_table)
            elements.append(Spacer(1, 20))

            # Calculate total price
            total_price = 0
            for mat, qty in zip(materials, quantities):
                unit_price = (
                    float(company.stainless_steel_price) if mat == 'stainless_steel'
                    else float(company.carbon_steel_price)
                )
                total_price += unit_price * float(qty)

            # Project Summary
            summary_data = [
                ['Project Summary'],
                [f'Total Components: {len(components)}'],
                [f'Total Price: ${total_price:,.2f} USD'],
                ['Material Distribution:'],
            ]
            
            # Count materials
            material_counts = {}
            for mat in materials:
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
            elements.append(summary_table)
            elements.append(Spacer(1, 20))

        def create_second_page():
            elements.append(PageBreak())
            
            # Components table header
            elements.append(Paragraph("Components Details", styles['Heading2']))
            elements.append(Spacer(1, 20))

            # Detailed components table
            items_data = [['Component', 'Material', 'Quantity']]
            
            for comp, mat, qty in zip(components, materials, quantities):
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
            elements.append(components_table)

        def add_footer(canvas, doc):
            canvas.saveState()
            # Add footer text
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
            
            # Add page numbers
            page_num = canvas.getPageNumber()
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(7.5*inch, 0.5*inch, f"Page {page_num}")
            canvas.restoreState()

        # Build document
        create_first_page()
        create_second_page()
        
        doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
        pdf = buffer.getvalue()
        buffer.close()

        # Create response
        project_name_safe = project_name.strip().replace(' ', '_').lower()
        filename = f"Grupo_ARGA_Quote_{project_name_safe}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf)

        return response

    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        return render(request, 'quote/error.html', {
            'error': f'Error generando PDF: {str(e)}'
        })