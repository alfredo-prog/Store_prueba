from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista, name='lista'),
    path('lista/', views.lista, name='lista'),
    path('crear/', views.crear_producto, name='crear'),
    path('editar/<int:pk>/', views.editar_producto, name='editar'),
    path('eliminar/<int:pk>/', views.eliminar_producto, name='eliminar'),
    path('cambiar-estado/<int:pk>/', views.cambiar_estado_producto, name='cambiar_estado'),
    path('check-updates/', views.check_updates, name='check_updates'),
    path('api/exportar-excel/', views.exportar_inventario_excel, name='exportar_inventario_excel'),
    path('api/imprimir-reporte/', views.imprimir_reporte_inventario, name='imprimir_reporte_inventario'),
]