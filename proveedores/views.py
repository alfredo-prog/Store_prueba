from django.shortcuts import render
from .models import Proveedor

def lista(request):
    proveedores = Proveedor.objects.all()
    
    # Calcular estadísticas
    con_telefono = sum(1 for p in proveedores if p.telefono)
    con_email = sum(1 for p in proveedores if p.email)
    con_direccion = sum(1 for p in proveedores if p.direccion)
    
    context = {
        'proveedores': proveedores,
        'con_telefono': con_telefono,
        'con_email': con_email,
        'con_direccion': con_direccion,
    }
    return render(request, 'proveedores/lista.html', context)