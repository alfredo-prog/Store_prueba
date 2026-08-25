from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from inventario.models import Producto
from compras.models import Compra
from ventas.models import Venta
from proveedores.models import Proveedor
from clientes.models import Cliente

@login_required(login_url='/login/')
def dashboard(request):
    context = {
        "total_productos": Producto.objects.count(),
        "total_compras": Compra.objects.count(),
        "total_ventas": Venta.objects.count(),
        "total_proveedores": Proveedor.objects.count(),
        "total_clientes": Cliente.objects.count(),
    }
    return render(request, "dashboard.html", context)

def login_view(request):
    error_message = None
    username = ""
    
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        if not username or not password:
            error_message = "Por favor ingresa usuario y contraseña."
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    error_message = "Usuario inactivo. Contacta al administrador."
            else:
                error_message = "Usuario o contraseña incorrectos."
    
    context = {
        'username': username,
        'error_message': error_message,
    }
    return render(request, 'login.html', context)

def logout_view(request):
    logout(request)
    return redirect('/login/')
