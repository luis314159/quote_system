from django.shortcuts import render, redirect
from django.http import HttpRequest
import pandas as pd
from utils import analyze_step_file
from django.http import JsonResponse
import json
from .models import MaterialDensity
import logging

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