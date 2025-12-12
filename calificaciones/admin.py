# Interfaz del superadmin

from django.contrib import admin
from .models import Perfil, Calificacion, DocumentoFuente, Auditoria

admin.site.register(Perfil)
admin.site.register(Calificacion)
admin.site.register(DocumentoFuente)

@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'usuario_accion', 'accion', 'modelo_afectado', 'instancia_id')
    list_filter = ('accion', 'modelo_afectado', 'usuario_accion')
    search_fields = ('detalle', 'usuario_accion')
    
    #Nadie puede modificar la bitacora/log, solo vista
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False