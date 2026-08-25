from django.shortcuts import render
from .models import Cliente

def lista(request):
    clientes = Cliente.objects.all()
    
    # Calcular estadísticas
    con_telefono = sum(1 for c in clientes if c.telefono)
    con_email = sum(1 for c in clientes if c.email)
    con_direccion = sum(1 for c in clientes if c.direccion)
    
    context = {
        'clientes': clientes,
        'con_telefono': con_telefono,
        'con_email': con_email,
        'con_direccion': con_direccion,
    }
    return render(request, 'clientes/lista.html', context)
