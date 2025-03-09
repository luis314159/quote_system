import os
from spire.xls import *
from spire.xls.common import *


def convert_excel_to_pdf(input_file, output_file=None, sheet_index=0, page_setup=None):
    """
    Convert Excel file to PDF with various customization options
    
    Parameters:
    - input_file: Path to the Excel file
    - output_file: Path to save the PDF (if None, uses input filename with .pdf extension)
    - sheet_index: Index of the worksheet to convert (default: 0)
    - page_setup: Dictionary with page setup options
        - margins: dict with TopMargin, BottomMargin, LeftMargin, RightMargin (values in inches)
        - orientation: 'Portrait' or 'Landscape'
        - paper_size: PaperSizeType enum value
        - print_gridlines: Boolean to show/hide gridlines
        - print_area: Cell range to print, e.g., "A1:H10"
    """
    # Create default output filename if none provided
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}.pdf"
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create Workbook object and load Excel file
    workbook = Workbook()
    workbook.LoadFromFile(input_file)
    
    # Get the specified worksheet
    try:
        sheet = workbook.Worksheets[sheet_index]
    except Exception as e:
        print(f"Error accessing worksheet at index {sheet_index}: {e}")
        print(f"Using first worksheet instead.")
        sheet = workbook.Worksheets[0]
    
    # Apply page setup if provided
    if page_setup:
        setup = sheet.PageSetup
        
        # Apply margins
        if 'margins' in page_setup:
            margins = page_setup['margins']
            if 'TopMargin' in margins:
                setup.TopMargin = margins['TopMargin']
            if 'BottomMargin' in margins:
                setup.BottomMargin = margins['BottomMargin']
            if 'LeftMargin' in margins:
                setup.LeftMargin = margins['LeftMargin']
            if 'RightMargin' in margins:
                setup.RightMargin = margins['RightMargin']
        
        # Apply orientation
        if 'orientation' in page_setup:
            if page_setup['orientation'].lower() == 'landscape':
                setup.Orientation = PageOrientationType.Landscape
            else:
                setup.Orientation = PageOrientationType.Portrait
        
        # Apply paper size
        if 'paper_size' in page_setup:
            setup.PaperSize = page_setup['paper_size']
        
        # Apply gridlines
        if 'print_gridlines' in page_setup:
            setup.IsPrintGridlines = page_setup['print_gridlines']
        
        # Apply print area
        if 'print_area' in page_setup:
            setup.PrintArea = page_setup['print_area']
    
    # Set converter settings
    workbook.ConverterSetting.SheetFitToPage = True
    
    # Save to PDF
    sheet.SaveToPdf(output_file)
    
    # Clean up resources
    workbook.Dispose()
    
    return output_file


def convert_workbook_to_pdf(input_file, output_file=None):
    """
    Convert entire workbook to a single PDF with each sheet on a separate page
    
    Parameters:
    - input_file: Path to the Excel file
    - output_file: Path to save the PDF (if None, uses input filename with .pdf extension)
    """
    # Create default output filename if none provided
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_workbook.pdf"
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create Workbook object and load Excel file
    workbook = Workbook()
    workbook.LoadFromFile(input_file)
    
    # Set converter settings
    workbook.ConverterSetting.SheetFitToPage = True
    
    # Save to PDF
    workbook.SaveToFile(output_file, FileFormat.PDF)
    
    # Clean up resources
    workbook.Dispose()
    
    return output_file


# Example usage
if __name__ == "__main__":
    # Simple conversion with default settings
    input_file = r"data\quote_template.xlsx"
    convert_excel_to_pdf(input_file)
    
    # Conversion with custom settings
    custom_page_setup = {
        'margins': {
            'TopMargin': 0.5,
            'BottomMargin': 0.5,
            'LeftMargin': 0.5,
            'RightMargin': 0.5
        },
        'orientation': 'Landscape',
        'paper_size': PaperSizeType.PaperA4,
        'print_gridlines': True,
        'print_area': "A1:H20"
    }
    
    convert_excel_to_pdf(
        input_file, 
        output_file="output/custom_settings.pdf",
        sheet_index=0,
        page_setup=custom_page_setup
    )
    
    # Convert entire workbook to PDF
    convert_workbook_to_pdf(input_file, "output/full_workbook.pdf")