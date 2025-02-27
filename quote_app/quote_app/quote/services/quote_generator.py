import os
import logging
from io import BytesIO
from datetime import datetime, timedelta

from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.enums import TA_LEFT

from ..models import MaterialDensity, CompanyMaterialPrice, CompanyFinishPrice

# Configure logging
logger = logging.getLogger(__name__)

class QuoteGenerator:
    def __init__(self, user, project_data, is_internal=False):
        self.user = user
        self.company = user.company
        self.project_data = project_data
        self.elements = []
        self.styles = getSampleStyleSheet()
        self.is_internal = is_internal  # Flag to differentiate PDF type
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

        # Get material prices for the company
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