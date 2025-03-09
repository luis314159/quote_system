import os
import io
import logging
import pandas as pd
from weasyprint import HTML, CSS
from tempfile import NamedTemporaryFile
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

class ExcelToPdfConverter:
    """
    Utility class to convert Excel quotes to PDF format
    """
    def __init__(self, excel_data, template_context=None):
        """
        Initialize the converter with Excel binary data
        
        Args:
            excel_data (bytes): Binary Excel file content
            template_context (dict, optional): Context data for enhancing PDF output
        """
        self.excel_data = excel_data
        self.template_context = template_context or {}
        
    def _excel_to_html(self):
        """
        Converts Excel data to HTML
        
        Returns:
            str: HTML representation of the Excel data
        """
        logger.info("Converting Excel to HTML")
        
        try:
            # Save Excel data to a temporary file
            with NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                temp_file.write(self.excel_data)
                temp_file_path = temp_file.name
            
            # Read Excel with pandas
            dfs = pd.read_excel(temp_file_path, sheet_name=None, engine='openpyxl')
            
            # Get the active sheet
            active_sheet = list(dfs.keys())[0]
            df = dfs[active_sheet]
            
            # Convert to HTML with styling
            html = df.to_html(index=False, classes='table table-bordered', border=1)
            
            # Get quote details from context if available
            quote_number = self.template_context.get('quote_number', 'N/A')
            project_name = self.template_context.get('project_name', 'N/A')
            date = self.template_context.get('date', 'N/A')
            valid_until = self.template_context.get('valid_until', 'N/A')
            
            # Create a complete HTML document with styling
            html = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Quote {quote_number}</title>
                <style>
                    @page {{ 
                        size: letter; 
                        margin: 2cm;
                    }}
                    body {{ 
                        font-family: Arial, sans-serif; 
                        margin: 0;
                        padding: 0;
                    }}
                    .header {{
                        margin-bottom: 20px;
                    }}
                    .header img {{
                        max-width: 200px;
                        height: auto;
                    }}
                    .info-table {{
                        width: 100%;
                        margin-bottom: 20px;
                    }}
                    .info-table td {{
                        padding: 5px;
                    }}
                    .table {{ 
                        width: 100%; 
                        border-collapse: collapse; 
                        margin-bottom: 30px;
                    }}
                    .table td, .table th {{ 
                        border: 1px solid #ddd; 
                        padding: 8px; 
                        font-size: 10pt;
                    }}
                    .table tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    .table th {{ 
                        padding-top: 12px; 
                        padding-bottom: 12px; 
                        text-align: center; 
                        background-color: #E0E0E0; 
                        font-weight: bold;
                    }}
                    .terms {{
                        margin-top: 20px;
                        font-size: 10pt;
                    }}
                    .terms h4 {{
                        margin-bottom: 5px;
                    }}
                    .terms p {{
                        margin-top: 5px;
                    }}
                    .footer {{
                        position: fixed;
                        bottom: 0;
                        width: 100%;
                        text-align: center;
                        font-size: 9pt;
                        color: #666;
                        padding: 10px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <img src="{os.path.join(settings.STATIC_ROOT, 'images', 'gpoargaHDpng.png')}" alt="Company Logo">
                    <h2>Quote #{quote_number}</h2>
                </div>
                
                <table class="info-table">
                    <tr>
                        <td><strong>Project:</strong></td>
                        <td>{project_name}</td>
                        <td><strong>Date:</strong></td>
                        <td>{date}</td>
                    </tr>
                    <tr>
                        <td><strong>Valid Until:</strong></td>
                        <td>{valid_until}</td>
                        <td></td>
                        <td></td>
                    </tr>
                </table>
                
                {html}
                
                <div class="terms">
                    <h4>Delivery:</h4>
                    <p>6 weeks or advise required</p>
                    
                    <h4>Payment Terms:</h4>
                    <p>Net 15 after shipping</p>
                    
                    <h4>Incoterms:</h4>
                    <p>Fob Grupo ARGA Plant at Chihuahua</p>
                    
                    <h4>Notes:</h4>
                    <p>We can provide logistic service Door to Door including customs clearance. To be quoted based on needs and weight.</p>
                </div>
                
                <div class="footer">
                    <p>This is an automatically generated quote. For questions, please contact {self.template_context.get('contact_email', '')}</p>
                </div>
            </body>
            </html>
            """
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
            return html
            
        except Exception as e:
            logger.error(f"Error converting Excel to HTML: {str(e)}")
            logger.error("Stacktrace:", exc_info=True)
            raise
    
    def convert_to_pdf(self):
        """
        Convert Excel data to PDF format
        
        Returns:
            bytes: PDF file content as bytes
        """
        logger.info("Converting Excel to PDF")
        
        try:
            # First convert Excel to HTML
            html_content = self._excel_to_html()
            
            # Save the HTML to a temporary file
            with NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
                temp_html.write(html_content.encode('utf-8'))
                temp_html_path = temp_html.name
            
            # Create a buffer for the PDF
            pdf_buffer = io.BytesIO()
            
            # Convert HTML to PDF using WeasyPrint
            HTML(filename=temp_html_path).write_pdf(
                pdf_buffer,
                stylesheets=[
                    CSS(string='''
                        @page { 
                            size: letter; 
                            margin: 1cm;
                        }
                        body { 
                            font-family: Arial, sans-serif; 
                        }
                    ''')
                ]
            )
            
            # Clean up the temporary file
            os.unlink(temp_html_path)
            
            # Position the buffer at the beginning
            pdf_buffer.seek(0)
            
            logger.info("PDF conversion completed successfully")
            return pdf_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error converting to PDF: {str(e)}")
            logger.error("Stacktrace:", exc_info=True)
            raise