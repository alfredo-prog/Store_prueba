from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import RegistroForm, PerfilForm
from .models import Usuario


def registro(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect("dashboard")
    else:
        form = RegistroForm()
    
    return render(request, "usuarios/registro.html", {"form": form})


@login_required(login_url='/login/')
def perfil(request):
    if request.method == "POST":
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("usuarios:perfil")
    else:
        form = PerfilForm(instance=request.user)
    
    return render(request, "usuarios/perfil.html", {"form": form})


@login_required(login_url='/login/')
def lista(request):
    usuarios = Usuario.objects.all()
    
    # Calcular estadísticas
    total_usuarios = usuarios.count()
    usuarios_activos = usuarios.filter(is_active=True).count()
    con_staff = usuarios.filter(is_staff=True).count()
    con_superuser = usuarios.filter(is_superuser=True).count()
    
    context = {
        'usuarios': usuarios,
        'total_usuarios': total_usuarios,
        'usuarios_activos': usuarios_activos,
        'con_staff': con_staff,
        'con_superuser': con_superuser,
    }
    return render(request, 'usuarios/lista.html', context)
