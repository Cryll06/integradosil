from pdf2image import convert_from_bytes
import pytesseract
import re

def procesar_pdf_ocr(pdf_file_bytes):
    print("Iniciando procesamiento OCR...")
    try:
        images = convert_from_bytes(pdf_file_bytes)
        texto_extraido = pytesseract.image_to_string(images[0], lang='spa')
        
        print("--- TEXTO EXTRAÍDO ---")
        print(texto_extraido)
        print("----------------------")


        datos = {}
        
        match_corredor = re.search(r'Corredor:\s*(.*)', texto_extraido, re.IGNORECASE)
        if match_corredor:
            datos['corredor'] = match_corredor.group(1).strip()

        match_año = re.search(r'Año.{0,20}(\d{4})', texto_extraido, re.IGNORECASE)
        if match_año:

            datos['anio_tributario'] = match_año.group(1).strip()

        match_monto = re.search(r'Monto:\s*[$]*\s*([\d\.]+)', texto_extraido, re.IGNORECASE)
        if match_monto:
            datos['monto'] = match_monto.group(1).replace('.', '')


        for i in range(8, 20): 

            match_factor = re.search(rf'F{i}\s*:\s*([\d\.]+)', texto_extraido, re.IGNORECASE)
            if match_factor:
                val = match_factor.group(1)
                datos[f'f{i}'] = f"0{val}" if val.startswith('.') else val

        print(f"Datos extraídos: {datos}")
        return datos

    except Exception as e:
        print(f"Error en OCR: {e}")
        return None