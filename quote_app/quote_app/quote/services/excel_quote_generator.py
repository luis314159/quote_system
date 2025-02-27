import os
import logging
import io
from datetime import datetime, timedelta
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from django.conf import settings

from ..models import MaterialDensity, CompanyMaterialPrice, CompanyFinishPrice

# Configure logging
logger = logging.getLogger(__name__)

class ExcelQuoteGenerator:
    def __init__(self, user, project_data, is_internal=False):
        self.user = user
        self.company = user.company
        self.project_data = project_data
        self.is_internal = is_internal
        
        # Cargar la plantilla Excel
        template_path = os.path.join(settings.STATIC_ROOT, 'templates', 'quote_template.xlsx')
        if not os.path.exists(template_path):
            logger.error(f"Template file not found at {template_path}")
            raise FileNotFoundError(f"Excel template not found: {template_path}")
        
        self.wb = load_workbook(template_path)
        self.ws = self.wb.active
        
        # Preparar datos de materiales y precios
        self.material_densities = {
            material.material_type: material.density 
            for material in MaterialDensity.objects.all()
        }
        
        self.material_prices = {
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
    
    def safe_write_cell(self, cell_ref, value):
        """
        Escribe un valor en una celda de manera segura, manejando celdas combinadas.
        
        Args:
            cell_ref: Referencia de celda (ej: 'A1', 'B5')
            value: Valor a escribir en la celda
        """
        try:
            self.ws[cell_ref] = value
        except AttributeError:
            logger.warning(f"No se puede escribir en celda combinada {cell_ref}, intentando otra forma...")
            # Intentar encontrar la celda principal de la combinación
            for merged_range in self.ws.merged_cells.ranges:
                # Verificar si la celda está en el rango combinado
                cell_col, cell_row = None, None
                
                # Extraer columna y fila de la referencia de celda
                # Ejemplo: 'A1' -> col='A', row=1
                import re
                match = re.match(r'([A-Z]+)([0-9]+)', cell_ref)
                if match:
                    cell_col_letter, cell_row_str = match.groups()
                    cell_row = int(cell_row_str)
                    
                    # Convertir letra de columna a número
                    cell_col = 0
                    for char in cell_col_letter:
                        cell_col = cell_col * 26 + (ord(char) - ord('A') + 1)
                else:
                    logger.error(f"Formato de celda no reconocido: {cell_ref}")
                    return
                
                # Verificar si la celda está en el rango
                if (merged_range.min_col <= cell_col <= merged_range.max_col and 
                    merged_range.min_row <= cell_row <= merged_range.max_row):
                    # Calcular la celda principal (top-left) de la combinación
                    min_col_letter = get_column_letter(merged_range.min_col)
                    main_cell = f"{min_col_letter}{merged_range.min_row}"
                    try:
                        self.ws[main_cell] = value
                        logger.info(f"Escrito en celda principal {main_cell} en lugar de {cell_ref}")
                        return
                    except Exception as e:
                        logger.error(f"Error al escribir en celda principal {main_cell}: {str(e)}")
            
            # Si llegamos aquí, no pudimos escribir en ninguna celda del rango combinado
            logger.error(f"No se pudo escribir en ninguna celda del rango combinado que incluye {cell_ref}")

    def _fill_header_info(self):
        """Rellena la información del encabezado en la plantilla Excel."""
        # Número de cotización y fechas
        current_date = datetime.now()
        valid_date = current_date + timedelta(days=30)
        quote_number = f"AR{current_date.strftime('%d%m%Y%H%M')}"
        
        # Encuentra las celdas correspondientes en el Excel y actualiza
        self.safe_write_cell('I3', current_date.strftime('%m/%d/%Y'))  # Fecha actual
        self.safe_write_cell('I4', valid_date.strftime('%m/%d/%Y'))    # Fecha de validez
        self.safe_write_cell('I5', quote_number)                       # Número de cotización
        self.safe_write_cell('I7', '1')                                # Revisión
        
        # Información del cliente
        self.safe_write_cell('B6', self.company.name)                  # Nombre del cliente
        self.safe_write_cell('B7', self.company.contact_name)          # Contacto
        self.safe_write_cell('B8', self.company.contact_email)         # Email
        
        # Proyecto
        self.safe_write_cell('B4', self.project_data['project_name'])  # Nombre del proyecto

    def _add_components(self):
        """Añade los componentes a la tabla del Excel."""
        # Define la fila inicial donde insertar componentes (después de los encabezados)
        start_row = 10
        
        # Calcular costes para cada componente
        costs_data, total_volume, total_weight, total_cost = self.calculate_component_costs()
        
        # Añadir cada componente a la tabla
        for i, item in enumerate(costs_data):
            row = start_row + i
            
            # Populate cells with safe writing
            self.safe_write_cell(f'B{row}', item['component'])                 # Nombre del componente
            self.safe_write_cell(f'C{row}', item['material'])                  # Material
            self.safe_write_cell(f'I{row}', item['quantity'])                  # Cantidad
            
            # Dependiendo de si es interno o para cliente, los precios pueden variar
            if self.is_internal:
                # Para uso interno, mostrar todos los detalles de costos
                self.safe_write_cell(f'D{row}', f"Vol: {item['volume']:.2f} in³")
                self.safe_write_cell(f'E{row}', f"Weight: {item['weight']:.2f} lbs")
                self.safe_write_cell(f'F{row}', f"${item['price_per_pound']:.2f}/lb")
                self.safe_write_cell(f'J{row}', item['unit_cost'])             # Precio unitario
                self.safe_write_cell(f'K{row}', item['subtotal'])              # Precio total
            else:
                # Para el cliente, mostrar información simplificada
                self.safe_write_cell(f'D{row}', "")                            # Volumen (vacío)
                self.safe_write_cell(f'E{row}', "")                            # Peso (vacío)
                self.safe_write_cell(f'F{row}', "")                            # Precio por libra (vacío)
                self.safe_write_cell(f'J{row}', item['unit_cost'])             # Precio unitario
                self.safe_write_cell(f'K{row}', item['subtotal'])              # Precio total
        
        # Añadir total al final
        total_row = start_row + len(costs_data) + 1
        self.safe_write_cell(f'B{total_row}', "TOTAL")
        self.safe_write_cell(f'K{total_row}', total_cost)
        
        # Aplicar formato a la fila de totales
        for col in ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']:
            try:
                cell = self.ws[f'{col}{total_row}']
                if hasattr(cell, 'font'):  # Verificar si es un objeto que puede ser formateado
                    cell.font = Font(bold=True)
                    # Agregar un fondo gris claro
                    cell.fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
            except Exception as e:
                logger.warning(f"No se pudo aplicar formato a la celda {col}{total_row}: {str(e)}")

    def calculate_component_costs(self):
        """Calculate costs for all components considering material weight, quantity and price per pound."""
        costs_data = []
        total_volume = 0
        total_weight = 0
        total_cost = 0

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
                
                if mat_id not in self.material_prices:
                    logger.warning(f"No price found for material ID {mat_id} in company {self.company.name}")
                    continue
                    
                material_data = self.material_prices[mat_id]
                
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

    def _add_terms_and_delivery(self):
        """Añade información de términos y entrega en la parte inferior del Excel."""
        # Definir fila base para términos (ajustar según plantilla)
        terms_row = 32
        
        # Términos estándar (se pueden personalizar según necesidades)
        self.safe_write_cell(f'C{terms_row}', "6 weeks or advise required")  # Entrega
        self.safe_write_cell(f'C{terms_row+1}', "Net 15 after shipping")  # Términos de pago
        self.safe_write_cell(f'C{terms_row+2}', "Fob Grupo ARGA Plant at Chihuahua")  # Incoterms
        
        # Notas adicionales
        notes = "We can provide logistic service Door to Door including customs clerance. To be quoted base on needs and weight."
        self.safe_write_cell(f'C{terms_row+3}', notes)

    def generate_excel(self):
        """Genera el archivo Excel con todos los datos de la cotización."""
        try:
            # Paso 1: Rellenar la información del encabezado
            self._fill_header_info()
            
            # Paso 2: Añadir los componentes a la tabla
            self._add_components()
            
            # Paso 3: Añadir términos y condiciones
            self._add_terms_and_delivery()
            
            # Guardar el Excel en un buffer de memoria
            buffer = io.BytesIO()
            self.wb.save(buffer)
            buffer.seek(0)
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating Excel quote: {str(e)}")
            logger.error("Stacktrace:", exc_info=True)
            raise