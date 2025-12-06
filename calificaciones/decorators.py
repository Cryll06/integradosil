from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login
from functools import wraps

def rol_requerido(rol_nombre):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1 Revisa si el usuario está logueado
            if not request.user.is_authenticated:
                # Si no está logueado, lo mandamos al login
                return redirect_to_login(request.get_full_path())
            
            # 2 Revisa si es Superadmin 
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # 3 Revisa el rol del perfil
            try:
                if request.user.perfil.rol == rol_nombre:
                    return view_func(request, *args, **kwargs)
            except:
                # Si no tiene perfil, o cualquier error, denegar acceso
                pass
            
            # Se dispara el error de acceso denegado
            raise PermissionDenied
        return _wrapped_view
    return decorator

# Creamos los decoradores específicos para usarlos de manera más facil
admin_requerido = rol_requerido('ADMIN')
contador_requerido = rol_requerido('CONTADOR')