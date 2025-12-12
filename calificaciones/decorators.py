from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login
from functools import wraps

def rol_requerido(rol_nombre):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            try:
                if request.user.perfil.rol == rol_nombre:
                    return view_func(request, *args, **kwargs)
            except:
                pass
            
            raise PermissionDenied
        return _wrapped_view
    return decorator

admin_requerido = rol_requerido('ADMIN')
contador_requerido = rol_requerido('CONTADOR')