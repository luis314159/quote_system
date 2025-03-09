import subprocess

def excel_to_pdf(input_excel_path, output_directory='.'):
    try:
        subprocess.run([
            'libreoffice', '--headless', '--convert-to', 'pdf',
            '--outdir', output_directory, input_excel_path
        ], check=True)
        print(f'✅ Archivo convertido correctamente a PDF en {output_directory}')
    except subprocess.CalledProcessError as e:
        print(f'❌ Error al convertir archivo: {e}')

if __name__ == '__main__':
    excel_path = 'data/quote_format.xlsx'  # Cambia esta ruta según tu necesidad
    output_dir = './'  # Directorio de salida del PDF
    excel_to_pdf(excel_path, output_dir)
