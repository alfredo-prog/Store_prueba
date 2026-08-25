from django.urls import path
from . import views

app_name = 'caja'

urlpatterns = [
    path('', views.dashboard_caja, name='dashboard'),
    path('abrir/', views.abrir_caja, name='abrir_caja'),
    path('cerrar/<int:caja_id>/', views.cerrar_caja, name='cerrar_caja'),
    path('movimiento/agregar/', views.agregar_movimiento, name='agregar_movimiento'),
    path('movimiento/eliminar/<int:movimiento_id>/', views.eliminar_movimiento, name='eliminar_movimiento'),
    path('detalle/<int:caja_id>/', views.detalle_caja, name='detalle_caja'),
    path('api/status/', views.api_caja_status, name='api_status'),
    path('lista/', views.lista_cajas, name='lista_cajas'),
    path('movimientos/<int:caja_id>/', views.lista_movimientos, name='lista_movimientos'),
]
