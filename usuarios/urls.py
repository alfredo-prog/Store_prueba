from django.urls import path
from . import views

app_name = "usuarios"

urlpatterns = [
    path('', views.lista, name='lista'),
    path('lista/', views.lista, name='lista'),
    path("registro/", views.registro, name="registro"),
    path("perfil/", views.perfil, name="perfil"),
]
