from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path('', views.lista, name='lista'),
    path('lista/', views.lista, name='lista'),
    path('pos/', views.pos_view, name='pos'),
    path('nueva/', views.nueva_venta, name='nueva_venta'),
    path('api/agregar-producto/', views.agregar_producto_temporal, name='agregar_producto_temporal'),
    path('api/confirmar-venta/', views.confirmar_venta, name='confirmar_venta'),
    path('api/detalle/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),
    path('api/anular/<int:venta_id>/', views.anular_venta, name='anular_venta'),
    path('api/editar/<int:venta_id>/', views.editar_venta, name='editar_venta'),
    path('api/exportar-excel/', views.exportar_ventas_excel, name='exportar_ventas_excel'),
    path('api/imprimir-reporte/', views.imprimir_reporte_ventas, name='imprimir_reporte_ventas'),
    
    # URLs para Proformas
    path('proformas/', views.lista_proformas, name='lista_proformas'),
    path('proformas/nueva/', views.nueva_proforma, name='nueva_proforma'),
    path('proformas/<int:pk>/', views.detalle_proforma, name='detalle_proforma'),
    path('proformas/<int:pk>/convertir/', views.convertir_proforma_a_venta, name='convertir_proforma_a_venta'),
    path('proformas/<int:pk>/eliminar/', views.eliminar_proforma, name='eliminar_proforma'),
    
    # Redirección para evitar errores 404
    path('nuevo/', lambda request: redirect('ventas:nueva_proforma'), name='nueva_redirect'),
]