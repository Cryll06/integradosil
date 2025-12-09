from django.urls import path
from . import views

urlpatterns = [
    # Urls para autenticacion y roles
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # Esta url decide si mandara al usuario a la interfaz Admin o Contador
    path('portal/', views.redireccion_rol, name='redireccion_rol'),

    # Urls para la interfaz de Admin
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/auditoria/', views.admin_auditoria, name='admin_auditoria'),
    path('admin/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin/usuarios/crear/', views.admin_crear_usuario, name='admin_crear_usuario'),
    path('admin/usuarios/editar/<int:user_id>/', views.admin_editar_usuario, name='admin_editar_usuario'),

    # Url para la interfaz de Contador/Trabajador
    path('', views.contador_dashboard, name='contador_dashboard'),
    path('calificacion/nueva/', views.calificacion_crear, name="calificacion_crear"),
    path('calificacion/editar/<int:pk>/', views.calificacion_editar, name="calificacion_editar"),
    path('calificacion/eliminar/<int:pk>/', views.calificacion_eliminar, name="calificacion_eliminar"),
    path('carga-masiva-excel/', views.carga_masiva_excel, name="carga_masiva_excel"),
    path('carga-pdf-ocr/', views.carga_pdf_ocr, name="carga_pdf_ocr"),
    path('calificacion/guardar-ocr/', views.calificacion_guardar_ocr, name="calificacion_guardar_ocr"),
    path('exportar-excel/', views.exportar_calificaciones_excel, name="exportar_excel"),
]