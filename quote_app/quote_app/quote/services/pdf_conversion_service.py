import os
import tempfile
import platform
import subprocess
import logging
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

class PDFConverter:
    @staticmethod
    def is_conversion_supported():
        """
        Check if PDF conversion is supported on this system.
        Returns True if:
        1. Running on Linux
        2. LibreOffice is installed
        3. ENABLE_PDF_CONVERSION setting is True
        """
        try:
            # Check operating system
            is_linux = platform.system().lower() == 'linux'
            if not is_linux:
                logger.info("PDF conversion not supported: Not running on Linux")
                return False
                
            # Check if LibreOffice is available
            libreoffice_exists = False
            try:
                result = subprocess.run(
                    ['which', 'libreoffice'], 
                    check=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    timeout=5  # Timeout after 5 seconds
                )
                libreoffice_exists = len(result.stdout) > 0
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                libreoffice_exists = False
                
            if not libreoffice_exists:
                logger.info("PDF conversion not supported: LibreOffice not found")
                return False
                
            # Check setting
            pdf_conversion_enabled = getattr(settings, 'ENABLE_PDF_CONVERSION', False)
            if not pdf_conversion_enabled:
                logger.info("PDF conversion disabled in settings")
                return False
                
            logger.info("PDF conversion is supported and enabled")
            return True
            
        except Exception as e:
            logger.error(f"Error checking PDF conversion support: {str(e)}")
            return False
    
    @staticmethod
    def convert_excel_to_pdf(excel_bytes):
        """
        Convert Excel content to PDF using LibreOffice.
        
        Args:
            excel_bytes: Binary content of the Excel file
            
        Returns:
            bytes: PDF content or None if conversion failed
        """
        if not PDFConverter.is_conversion_supported():
            return None
            
        try:
            # Create temporary directory to work in
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write Excel content to temp file
                temp_excel_path = os.path.join(temp_dir, 'temp_quote.xlsx')
                with open(temp_excel_path, 'wb') as f:
                    f.write(excel_bytes)
                
                logger.info(f"Excel file saved to temporary location: {temp_excel_path}")
                
                # Convert to PDF using LibreOffice
                logger.info("Starting LibreOffice conversion process")
                try:
                    # Set a timeout to prevent hanging
                    result = subprocess.run([
                        'libreoffice',
                        '--headless',
                        '--convert-to', 'pdf',
                        '--outdir', temp_dir,
                        temp_excel_path
                    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
                    
                    logger.info(f"LibreOffice conversion output: {result.stdout.decode('utf-8', errors='ignore')}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"LibreOffice conversion failed: {str(e)}")
                    if e.stderr:
                        logger.error(f"Error output: {e.stderr.decode('utf-8', errors='ignore')}")
                    return None
                except subprocess.TimeoutExpired:
                    logger.error("LibreOffice conversion timed out after 60 seconds")
                    return None
                
                # Check if PDF was created
                expected_pdf_path = os.path.join(temp_dir, 'temp_quote.pdf')
                if not os.path.exists(expected_pdf_path):
                    logger.error(f"PDF file not found at expected location: {expected_pdf_path}")
                    # Try with different name pattern
                    pdf_files = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
                    if pdf_files:
                        expected_pdf_path = os.path.join(temp_dir, pdf_files[0])
                        logger.info(f"Found PDF with different name: {expected_pdf_path}")
                    else:
                        logger.error("No PDF files found in output directory")
                        return None
                
                # Read PDF content
                with open(expected_pdf_path, 'rb') as f:
                    pdf_content = f.read()
                
                logger.info(f"Successfully converted Excel to PDF, size: {len(pdf_content)} bytes")
                return pdf_content
                
        except Exception as e:
            logger.error(f"Error during PDF conversion: {str(e)}")
            logger.error("Stacktrace:", exc_info=True)
            return None