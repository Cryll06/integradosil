from django import forms
from .models import Calificacion, Perfil
from django.contrib.auth.models import User

class CalificacionForm(forms.ModelForm):

    documento_respaldo_upload = forms.FileField(label="Documento de Respaldo", required=False)

    class Meta:
        model = Calificacion

        exclude = ['creado_por', 'documento_respaldo'] 
    
    def __init__(self, *args, **kwargs):

        ocr_mode = kwargs.pop('ocr_mode', False)
        
        super().__init__(*args, **kwargs)
        

        if ocr_mode:

            del self.fields['documento_respaldo_upload']
            

        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

class CargaMasivaExcelForm(forms.Form):
    archivo_excel = forms.FileField(label="Archivo (XLSX)", 
                                    widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'}))

class CargaPDFForm(forms.Form):
    archivo_pdf = forms.FileField(label="Archivo (PDF)", 
                                  widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}))


class CrearUsuarioForm(forms.ModelForm):
    rol = forms.ChoiceField(choices=Perfil.ROLES, widget=forms.Select(attrs={'class': 'form-select'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'rol', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            user.perfil.rol = self.cleaned_data["rol"]
            user.perfil.save()
        return user