import json
import logging
import pandas as pd
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render

from ..models import (
    Company, CompanyMaterialPrice, CompanyFinishPrice
)

# Configure logging
logger = logging.getLogger(__name__)

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
        # Get and log session data
        result_data = request.session['result_data']
        logger.debug(f"Session 'result_data': {result_data}")
        
        df = pd.DataFrame(result_data)
        
        # Log original columns
        logger.debug(f"Original DataFrame columns: {df.columns.tolist()}")
        
        # Rename columns and log
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
        
        # Get available materials for the company with densities and prices
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
        
        # Get and log available finishes and prices
        finish_prices = {
            price.finish.name: float(price.price_multiplier)
            for price in CompanyFinishPrice.objects.filter(
                company=company,
                is_active=True
            )
        }
        logger.debug(f"Company finish prices: {finish_prices}")
        
        # Prepare and log context
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
        
        # Get current data
        result_data = request.session.get('result_data', [])
        df = pd.DataFrame(result_data)
        
        # Update material for the specific component
        df.loc[df['Component'] == component, 'Material'] = new_material
        
        # Recalculate volumes by material
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
        
        # Save updated data in session
        request.session['result_data'] = df.to_dict('records')
        
        return JsonResponse({
            'success': True,
            'volume_by_material': volume_by_material,
            'total_volume': sum(volume_by_material.values())
        })
    
    return JsonResponse({'success': False}, status=400)