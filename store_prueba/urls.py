from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("admin/", admin.site.urls),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # módulos
    path("usuarios/", include(("usuarios.urls", "usuarios"), namespace="usuarios")),
    path("inventario/", include(("inventario.urls", "inventario"), namespace="inventario")),
    path("compras/", include(("compras.urls", "compras"), namespace="compras")),
    path("ventas/", include(("ventas.urls", "ventas"), namespace="ventas")),
    path("proveedores/", include(("proveedores.urls", "proveedores"), namespace="proveedores")),
    path("clientes/", include(("clientes.urls", "clientes"), namespace="clientes")),
    path("caja/", include(("caja.urls", "caja"), namespace="caja")),
    path("catalogo/", include(("catalogo.urls", "catalogo"), namespace="catalogo")),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
