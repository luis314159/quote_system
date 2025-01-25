from django.shortcuts import render, redirect
from django.http import HttpRequest
import pandas as pd
from utils import analyze_step_file


def home(request: HttpRequest):
    return render(request, 'quote/home.html')


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
            result_df = analyze_step_file(file)
            # Store the DataFrame in the session
            request.session['result_data'] = result_df.to_dict('records')
            return redirect('results')
        except Exception as e:
            return render(request, 'upload.html', {'error': str(e)})
            
    return render(request, 'quote/upload.html')

def results(request: HttpRequest):
    if not request.session.get('result_data'):
        return redirect('upload')
        
    # Get the DataFrame from the session
    df = pd.DataFrame(request.session['result_data'])
    
    # Convert DataFrame to list of dictionaries for template rendering
    table_data = df[['Component', 'Volume (in³)', 'Material', 'Quantity']].to_dict('records')
    
    # Calculate some summary statistics
    total_components = len(df)
    total_volume = df['Volume (in³)'].sum()
    total_quantity = df['Quantity'].sum()
    
    context = {
        'table_data': table_data,
        'summary': {
            'total_components': total_components,
            'total_volume': f"{total_volume:.2f}",
            'total_quantity': total_quantity
        }
    }
    
    return render(request, 'results.html', context)