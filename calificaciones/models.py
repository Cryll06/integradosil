from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import json
from decimal import Decimal

#MODELO DE ROLES
class Perfil(models.Model):
    ROLES = (
        ('ADMIN', 'Administrador de Negocio'), 
        ('CONTADOR', 'Contador / Trabajador'),   
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=20, choices=ROLES, default='CONTADOR')
    
    class Meta:
        db_table = 'NUAM_PERFILES_USUARIO'
        verbose_name = "Perfil de Usuario"
        
    def __str__(self):
        return f"{self.user.username} ({self.get_rol_display()})"


@receiver(post_save, sender=User)
def crear_o_actualizar_perfil(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)
    instance.perfil.save()


#MODELO PARA DOCUMENTOS (PDF/EXCEL)
class DocumentoFuente(models.Model):
    TIPOS = (('PDF', 'PDF'), ('EXCEL', 'Excel'))
    archivo = models.FileField(upload_to='documentos_fuente/%Y/%m/')
    nombre_original = models.CharField(max_length=255)
    tipo_documento = models.CharField(max_length=10, choices=TIPOS)
    subido_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='documentos_subidos')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'NUAM_DOCUMENTOS_FUENTE'
        verbose_name = "Documento Fuente"

    def __str__(self):
        return f"ID:{self.id} - {self.nombre_original}"


#MODELO CALIFICACION
class Calificacion(models.Model):
    corredor = models.CharField("Corredor", max_length=150, db_index=True) 
    anio_tributario = models.IntegerField("Año Tributario", db_index=True) 
    monto = models.DecimalField("Monto", max_digits=15, decimal_places=2)

    f8 = models.DecimalField("Factor F8", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f9 = models.DecimalField("Factor F9", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f10 = models.DecimalField("Factor F10", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f11 = models.DecimalField("Factor F11", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f12 = models.DecimalField("Factor F12", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f13 = models.DecimalField("Factor F13", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f14 = models.DecimalField("Factor F14", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f15 = models.DecimalField("Factor F15", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f16 = models.DecimalField("Factor F16", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f17 = models.DecimalField("Factor F17", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f18 = models.DecimalField("Factor F18", max_digits=5, decimal_places=4, default=Decimal('0.0'))
    f19 = models.DecimalField("Factor F19", max_digits=5, decimal_places=4, default=Decimal('0.0'))

    documento_respaldo = models.ForeignKey(DocumentoFuente, on_delete=models.SET_NULL, null=True, blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='calificaciones_creadas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'NUAM_CALIFICACIONES'
        verbose_name = "Calificación"
        verbose_name_plural = "Calificaciones"
        ordering = ['-fecha_creacion']

    def clean(self):

        factors = [
            self.f8, self.f9, self.f10, self.f11, self.f12, self.f13,
            self.f14, self.f15, self.f16, self.f17, self.f18, self.f19
        ]
        suma_factores = sum(factor or Decimal('0.0') for factor in factors)
        
        if suma_factores > Decimal('1.0'):
            raise ValidationError(f"Error de Negocio: La suma de factores ({suma_factores}) excede el límite de 10")


        valores_numericos = factors + [self.monto]
        

        if any(v < Decimal('0.0') for v in valores_numericos if v is not None):
             raise ValidationError("Error de Integridad: Los montos y factores no pueden ser valores negativos")
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


    @property
    def suma_total_factores(self):

        factors = [
            self.f8, self.f9, self.f10, self.f11, self.f12, self.f13,
            self.f14, self.f15, self.f16, self.f17, self.f18, self.f19
        ]

        return sum(factor or Decimal('0.0') for factor in factors).quantize(Decimal('0.0001'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Calificación {self.id} - {self.corredor} ({self.anio_tributario})"

#MODELO AUDITORIA
class Auditoria(models.Model):

    usuario_accion = models.CharField(max_length=150, null=True, blank=True)
    accion = models.CharField(max_length=20) 
    modelo_afectado = models.CharField(max_length=100)
    instancia_id = models.PositiveIntegerField(null=True, blank=True)
    detalle = models.TextField(null=True, blank=True)
    data_anterior = models.JSONField(null=True, blank=True) 
    data_nueva = models.JSONField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True) 
    class Meta:
        db_table = 'NUAM_BITACORA_AUDITORIA'
        verbose_name = "Registro de Auditoría"
        ordering = ['-fecha']


def serializar_instancia(instancia):
    data = {}
    for field in instancia._meta.fields:
        valor = getattr(instancia, field.name)

        if isinstance(valor, models.fields.files.FieldFile):
            data[field.name] = valor.name
        elif isinstance(valor, models.Model):
            data[field.name] = str(valor)
        else:
            try:
                json.dumps(valor)
                data[field.name] = valor
            except TypeError:
                data[field.name] = str(valor) 
    return data

@receiver(post_save, sender=Calificacion)
def auditar_guardado(sender, instance, created, **kwargs):
  
    if kwargs.get('raw', False): return 
    usuario = getattr(instance, '_request_user_username', 'sistema')
    data_nueva = serializar_instancia(instance)
    
    Auditoria.objects.create(
        usuario_accion=usuario,
        accion='CREATE' if created else 'UPDATE',
        modelo_afectado=sender._meta.model_name,
        instancia_id=instance.pk,
        data_nueva=data_nueva,
        detalle=f"Se {'creó' if created else 'actualizó'} la calificación {instance.pk}"
    )

@receiver(post_delete, sender=Calificacion)
def auditar_borrado(sender, instance, **kwargs):

    usuario = getattr(instance, '_request_user_username', 'sistema')
    
    Auditoria.objects.create(
        usuario_accion=usuario,
        accion='DELETE',
        modelo_afectado=sender._meta.model_name,
        instancia_id=instance.pk,
        data_anterior=serializar_instancia(instance),
        detalle=f"Se eliminó la calificación {instance.pk} ({instance.corredor})"
    )


    