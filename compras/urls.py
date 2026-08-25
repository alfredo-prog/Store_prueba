from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('lista/', views.lista, name='lista'),
    path('crear/', views.crear_compra, name='crear'),
    path('ver/<int:pk>/', views.ver_compra, name='ver'),
    path('editar/<int:pk>/', views.editar_compra, name='editar'),
    path('completar/<int:pk>/', views.completar_compra, name='completar'),
    path('eliminar/<int:pk>/', views.eliminar_compra, name='eliminar'),
]