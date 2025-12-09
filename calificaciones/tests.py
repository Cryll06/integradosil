from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
import unittest.mock
from calificaciones.models import Calificacion, Auditoria
from django.core.files.uploadedfile import SimpleUploadedFile

MOCK_PDF_CONTENT = b"Contenido PDF simulado"

class ReglaNegocioTests(TestCase):

    def setUp(self):
        User.objects.filter(username='test_contador').delete()
        self.user = User.objects.create_user('test_contador', 'test@test.com', 'pass123')
        self.user.perfil.rol = 'CONTADOR'
        self.user.perfil.save()

    def test_validacion_suma_factores_EXITOSA(self):
        print("\n--- [CAJA BLANCA] Prueba de Consistencia (Suma 1.0) ---")
        conteo_inicial = Calificacion.objects.count()
        
        cal = Calificacion(
            corredor="Corredor A", anio_tributario=2025, monto=1000,
            f8=Decimal('0.4'), f9=Decimal('0.6'), 
            f10=Decimal('0.0'), f19=Decimal('0.0'),
            creado_por=self.user
        )
        cal.full_clean()
        cal.save()
        
        self.assertEqual(Calificacion.objects.count(), conteo_inicial + 1)
        print("--- [Resultado] OK: Registro guardado correctamente ---")

    def test_validacion_suma_factores_FALLIDA(self):
        print("\n--- [CAJA BLANCA] Prueba de Rechazo (Suma 1.1) ---")
        conteo_inicial = Calificacion.objects.count()
        
        with self.assertRaises(ValidationError):
            cal = Calificacion(
                corredor="Corredor B", anio_tributario=2025, monto=1000,
                f8=Decimal('0.5'), f9=Decimal('0.5'), f10=Decimal('0.1'), f19=Decimal('0.0'), 
                creado_por=self.user
            )
            cal.full_clean()
        
        self.assertEqual(Calificacion.objects.count(), conteo_inicial)
        print("--- [Resultado] OK: Error de validación capturado (Consistencia de Reglas) ---")


class SeguridadYIntegracionTests(TestCase):

    def setUp(self):
        self.client = self.client_class()
        User.objects.filter(username__in=['admin_jefe', 'contador_op']).delete()
        
        self.admin_user = User.objects.create_user('admin_jefe', 'admin@test.com', 'pass123')
        self.admin_user.perfil.rol = 'ADMIN'
        self.admin_user.perfil.save()
        
        self.contador_user = User.objects.create_user('contador_op', 'contador@test.com', 'pass123')
        self.contador_user.perfil.rol = 'CONTADOR'
        self.contador_user.perfil.save()

    def test_seguridad_acceso_denegado_rol(self):
        print("\n--- [SEGURIDAD] Prueba de Acceso Denegado (403) ---")
        self.client.login(username='contador_op', password='pass123')
        # El contador NO puede ver el dashboard de admin
        response = self.client.get('/admin/dashboard/')
        self.assertEqual(response.status_code, 403)
        print("--- [Resultado] OK: Acceso denegado (403) al rol CONTADOR ---")

    def test_trazabilidad_completa_en_auditoria(self):
        print("\n--- [TRAZABILIDAD] Prueba de Registro de Auditoría (100% de Trazabilidad) ---")
        
        # 1. Login como Contador (el único que puede crear)
        self.client.login(username='contador_op', password='pass123')
        
        conteo_auditoria_inicial = Auditoria.objects.count()
        
        # 2. ENVIAMOS TODOS LOS CAMPOS (El Formulario es estricto y los pide todos)
        datos_completos = {
            'corredor': 'Test Corp',
            'anio_tributario': 2025,
            'monto': 100,
            # Campos obligatorios (aunque sean 0)
            'f8': 0.1, 'f9': 0, 'f10': 0, 'f11': 0, 'f12': 0, 'f13': 0,
            'f14': 0, 'f15': 0, 'f16': 0, 'f17': 0, 'f18': 0, 'f19': 0.9 
        }

        response = self.client.post('/calificacion/nueva/', datos_completos, follow=True)
        
        # 3. Verificamos que se creó el registro de auditoría
        self.assertEqual(Auditoria.objects.count(), conteo_auditoria_inicial + 1)
        
        # 4. Verificamos el contenido del log
        log = Auditoria.objects.first() 
        self.assertEqual(log.accion, 'CREATE')
        self.assertIn('contador_op', log.usuario_accion) 
        print("--- [Resultado] OK: Registro de Auditoría exitoso ---")

    @unittest.mock.patch('calificaciones.views.procesar_pdf_ocr')
    def test_integracion_flujo_ocr_exitosa(self, mock_ocr):
        print("\n--- [INTEGRACIÓN] Prueba de Flujo OCR a Validación ---")
        self.client.login(username='contador_op', password='pass123')

        mock_ocr.return_value = {
            'corredor': 'OCR_TEST_SA',
            'anio_tributario': 2024,
            'monto': 150000.00,
            'f8': '0.7',
            'f19': '0.3'
        }
        
        pdf_file = SimpleUploadedFile("test.pdf", MOCK_PDF_CONTENT, content_type="application/pdf")

        response_upload = self.client.post('/carga-pdf-ocr/', {'archivo_pdf': pdf_file}, follow=True)
        
        self.assertTemplateUsed(response_upload, 'contador/form_calificacion.html')
        self.assertContains(response_upload, 'value="OCR_TEST_SA"')
        
        print("--- [Resultado] OK: Integración de OCR a Formulario OK ---")