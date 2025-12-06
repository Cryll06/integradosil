from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages 
from .models import Perfil, Calificacion, Auditoria, DocumentoFuente
from .forms import CalificacionForm, CargaMasivaExcelForm, CargaPDFForm, CrearUsuarioForm
from .decorators import admin_requerido, contador_requerido 
import pandas as pd 
from django.db import transaction 
from django.core.exceptions import ValidationError, PermissionDenied
from .utils_ocr import procesar_pdf_ocr
from decimal import Decimal

# Vistas de autenticacion y roles

def login_view(request):
    # Si el usuario ya está logueado, lo mandamos a su interfaz/portal
    if request.user.is_authenticated:
        return redirect('redireccion_rol')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Bienvenido, {user.username}")
            return redirect('redireccion_rol')
        else:
            messages.error(request, "Usuario o contraseña incorrectos")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión exitosamente")
    return redirect('login')

def redireccion_rol(request):
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        if request.user.is_superuser:
            # Si es Superadmin, lo mandamos al dashboard de Admin
            return redirect('admin_dashboard')
        elif request.user.perfil.rol == 'ADMIN':
            return redirect('admin_dashboard')
        elif request.user.perfil.rol == 'CONTADOR':
            return redirect('contador_dashboard')
    except Perfil.DoesNotExist:
        # Fallback si el superadmin (que no tiene perfil) se loguea
        if request.user.is_superuser:
            messages.info(request, "Redirigido al Superadmin")
            return redirect('/superadmin/')
        else:
            logout(request)
            messages.error(request, "Tu perfil no está configurado. Contacta al administrador")
            return redirect('login')
    
    return redirect('login')


# Interfaz del Admin


@admin_requerido
def admin_dashboard(request):
    total_calificaciones = Calificacion.objects.count()
    total_documentos = DocumentoFuente.objects.count()
    total_usuarios = User.objects.filter(is_superuser=False).count()
    ultimas_acciones = Auditoria.objects.all()[:5] 
    
    context = {
        'total_calificaciones': total_calificaciones,
        'total_documentos': total_documentos,
        'total_usuarios': total_usuarios,
        'ultimas_acciones': ultimas_acciones,
    }
    return render(request, 'admin/dashboard.html', context)

@admin_requerido
def admin_auditoria(request):
    query = request.GET.get('q', '')
    if query:
        log_auditoria = Auditoria.objects.filter(detalle__icontains=query)
    else:
        log_auditoria = Auditoria.objects.all()
        
    return render(request, 'admin/auditoria.html', {'logs': log_auditoria, 'query': query})

@admin_requerido
def admin_usuarios(request):
    usuarios = Perfil.objects.filter(user__is_superuser=False).select_related('user')
    return render(request, 'admin/usuarios.html', {'usuarios': usuarios})

@admin_requerido
def admin_crear_usuario(request):
    if request.method == 'POST':
        form = CrearUsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario creado exitosamente')
            return redirect('admin_usuarios')
    else:
        form = CrearUsuarioForm()
    return render(request, 'admin/form_usuario.html', {'form': form, 'accion': 'Crear'})

@admin_requerido
def admin_editar_usuario(request, user_id):
    user = get_object_or_404(User, pk=user_id, is_superuser=False)
    
    if request.method == 'POST':
        rol = request.POST.get('rol')
        if rol in ['ADMIN', 'CONTADOR']:
            user.perfil.rol = rol
            user.perfil.save()
            messages.success(request, f'Rol de {user.username} actualizado')
            return redirect('admin_usuarios')
        else:
            messages.error(request, 'Rol no válido')

    return render(request, 'admin/form_usuario.html', {'usuario_obj': user, 'accion': 'Editar'})


# Interfaz del Contador/Trabajador

@contador_requerido
def contador_dashboard(request):
    # Solo muestra las calificaciones creadas por el usuario actual
    calificaciones = Calificacion.objects.filter(creado_por=request.user)
    return render(request, 'contador/dashboard.html', {'calificaciones': calificaciones})

@contador_requerido
def calificacion_crear(request):

    doc_id = request.POST.get('documento_fuente_id')
    doc_instance = None
    if doc_id:
        doc_instance = get_object_or_404(DocumentoFuente, id=doc_id)
        
    if request.method == 'POST':

        is_ocr = doc_instance is not None
        

        form = CalificacionForm(request.POST, ocr_mode=is_ocr) 
        
        if form.is_valid():
            try:
                with transaction.atomic(): 
                    calificacion = form.save(commit=False)
                    calificacion.creado_por = request.user
                    

                    if doc_instance:
                        calificacion.documento_respaldo = doc_instance
                    elif 'documento_respaldo_upload' in request.FILES:

                        pdf_file = request.FILES['documento_respaldo_upload']
                        doc_manual = DocumentoFuente.objects.create(
                            archivo=pdf_file,
                            nombre_original=pdf_file.name,
                            tipo_documento='PDF',
                            subido_por=request.user
                        )
                        calificacion.documento_respaldo = doc_manual
                        
                    calificacion._request_user_username = request.user.username
                    calificacion.save()
                    messages.success(request, 'Calificación creada exitosamente')
                    return redirect('contador_dashboard')
            
            except ValidationError as e:
                messages.error(request, f"Error de validación: {e.messages[0]}")
            except Exception as e:
                messages.error(request, f"Error inesperado: {str(e)}")
        else:
            messages.error(request, "El formulario tiene errores")
            
    else:

        form = CalificacionForm()
        
    return render(request, 'contador/form_calificacion.html', {
        'form': form, 
        'accion': 'Crear',
        'documento_id': doc_id 
    })

@contador_requerido
def calificacion_guardar_ocr(request):

    doc_id = request.POST.get('documento_fuente_id')
    doc_instance = None

    if not doc_id or request.method != 'POST':
        messages.error(request, "Flujo de validación OCR inválido o incompleto")
        return redirect('contador_dashboard')
        

    doc_instance = get_object_or_404(DocumentoFuente, id=doc_id)
    

    form = CalificacionForm(request.POST, ocr_mode=True)
    
    if form.is_valid():
        try:
            with transaction.atomic():
                calificacion = form.save(commit=False)
                calificacion.creado_por = request.user
                

                calificacion.documento_respaldo = doc_instance
                
                calificacion._request_user_username = request.user.username
                calificacion.save()
                
                messages.success(request, 'Calificación creada y validada exitosamente')
                return redirect('contador_dashboard')
                
        except ValidationError as e:
            messages.error(request, f"Error de validación: {e.messages[0]}")
        except Exception as e:
            messages.error(request, f"Error inesperado al guardar: {str(e)}")
    

    return render(request, 'contador/form_calificacion.html', {
        'form': form, 
        'accion': 'Crear (Validar OCR)',
        'documento_id': doc_id 
    })

@contador_requerido
def calificacion_editar(request, pk):

    calificacion = get_object_or_404(Calificacion, pk=pk, creado_por=request.user) 
    
    if request.method == 'POST':

        form = CalificacionForm(request.POST, request.FILES, instance=calificacion)
        if form.is_valid():
            try:
                calificacion_editada = form.save(commit=False)
                

                if request.FILES.get('documento_respaldo_upload'):
                    pdf_file = request.FILES['documento_respaldo_upload']
                    

                    doc_manual = DocumentoFuente.objects.create(
                        archivo=pdf_file,
                        nombre_original=pdf_file.name,
                        tipo_documento='PDF',
                        subido_por=request.user
                    )
                    calificacion_editada.documento_respaldo = doc_manual
                    
                calificacion_editada._request_user_username = request.user.username
                calificacion_editada.save()
                messages.success(request, 'Calificación actualizada')
                return redirect('contador_dashboard')
            except ValidationError as e:
                messages.error(request, f"Error de validación: {e.messages[0]}")
            except Exception as e:
                messages.error(request, f"Error inesperado: {str(e)}")
    else:

        form = CalificacionForm(instance=calificacion)
        
    return render(request, 'contador/form_calificacion.html', {'form': form, 'accion': 'Editar'})

@contador_requerido
def calificacion_eliminar(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk, creado_por=request.user) 
    calificacion._request_user_username = request.user.username
    calificacion.delete()
    
    messages.info(request, 'Calificación eliminada.')
    return redirect('contador_dashboard')


@contador_requerido
def carga_masiva_excel(request):
    if request.method == 'POST':
        form = CargaMasivaExcelForm(request.POST, request.FILES)
        if form.is_valid():
            archivo_excel = request.FILES['archivo_excel']
            
            doc = DocumentoFuente.objects.create(
                archivo=archivo_excel,
                nombre_original=archivo_excel.name,
                tipo_documento='EXCEL',
                subido_por=request.user
            )

            try:
                df = pd.read_excel(archivo_excel)
                
                columnas_requeridas = [
                    'Corredor', 'Anio', 'Monto', 
                    'F8', 'F9', 'F10', 'F11', 'F12', 'F13',
                    'F14', 'F15', 'F16', 'F17', 'F18', 'F19'
                ]
                
                for col in columnas_requeridas:
                    if col not in df.columns:
                        raise Exception(f"La columna requerida '{col}' no se encontró en el archivo Excel Por favor, descargue la plantilla oficial y no modifique las cabeceras")
                

                
                columnas_a_limpiar = ['Monto', 'F8', 'F9', 'F10', 'F11', 'F12', 'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19']
                
                for col in columnas_a_limpiar:
 
                    df[col] = df[col].fillna(0).astype(str).str.replace(',', '.')
                    

                    df[col] = df[col].apply(lambda x: Decimal(str(x)) if pd.notna(x) and str(x).strip() else Decimal('0.0'))


                df['Anio'] = pd.to_numeric(df['Anio'], errors='coerce').fillna(0).astype(int)

                calificaciones_para_crear = []
                
                with transaction.atomic():
                    for index, row in df.iterrows():
  
                        año_int = int(row['Anio'])
                        
  
                        c = Calificacion(
                            corredor=row['Corredor'],
                            anio_tributario=año_int, 
                            monto=row['Monto'], 
                            f8=row['F8'], f9=row['F9'], f10=row['F10'],
                            f11=row['F11'], f12=row['F12'], f13=row['F13'],
                            f14=row['F14'], f15=row['F15'], f16=row['F16'],
                            f17=row['F17'], f18=row['F18'], f19=row['F19'],
                            documento_respaldo=doc,
                            creado_por=request.user
                        )
                        c.clean() 
                        calificaciones_para_crear.append(c)
                    
                    Calificacion.objects.bulk_create(calificaciones_para_crear)
                
                Auditoria.objects.create(
                    usuario_accion=request.user.username,
                    accion='UPLOAD_EXCEL',
                    modelo_afectado='Calificacion',
                    instancia_id=doc.id,
                    detalle=f"Carga masiva de {len(calificaciones_para_crear)} registros desde {doc.nombre_original}"
                )

                messages.success(request, f"Carga masiva exitosa Se crearon {len(calificaciones_para_crear)} registros")
                return redirect('contador_dashboard')

            except ValidationError as e:
                messages.error(request, f"Error de validación en el Excel (Fila {index + 2}): {e.messages[0]} No se guardó ningún registro")
            except Exception as e:
                messages.error(request, f"Error procesando el archivo: {str(e)}")
                
    else:
        form = CargaMasivaExcelForm()
        
    return render(request, 'contador/carga_excel.html', {'form': form})


@contador_requerido
def carga_pdf_ocr(request):
    if request.method == 'POST':
        form = CargaPDFForm(request.POST, request.FILES)
        if form.is_valid():
            archivo_pdf = request.FILES['archivo_pdf']
            

            doc = DocumentoFuente.objects.create(
                archivo=archivo_pdf,
                nombre_original=archivo_pdf.name,
                tipo_documento='PDF',
                subido_por=request.user
            )

            try:
                archivo_pdf.seek(0)
                datos_ocr = procesar_pdf_ocr(archivo_pdf.read())

                if not datos_ocr:
                    messages.error(request, "El OCR no pudo extraer datos del PDF Revise el formato del documento")
                    return redirect('carga_pdf_ocr')

                form_calificacion = CalificacionForm(initial=datos_ocr, ocr_mode=True)
                
                messages.info(request, "Datos extraídos del PDF Por favor, verifique y guarde")
                
                return render(request, 'contador/form_calificacion.html', {
                    'form': form_calificacion, 
                    'accion': 'Crear (Validar OCR)',
                    'documento_id': doc.id 
                })

            except Exception as e:
                messages.error(request, f"Error de OCR: {str(e)}")
                
    else:
        form = CargaPDFForm()
        
    return render(request, 'contador/carga_pdf.html', {'form': form})