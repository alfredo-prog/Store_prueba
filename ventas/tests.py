from datetime import timedelta

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from clientes.models import Cliente
from ventas.admin import VentaAdmin
from ventas.models import Venta


class VentaAdminFilterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user_model = get_user_model()
        self.admin_user = self.user_model.objects.create_user(
            username='admin_test',
            password='12345678',
            is_staff=True,
            is_superuser=True,
        )
        self.other_user = self.user_model.objects.create_user(
            username='vendedor_test',
            password='12345678',
        )
        self.cliente = Cliente.objects.create(nombre='Cliente Test')

        self.venta_admin = site._registry[Venta]

        self.venta_admin_user = Venta.objects.create(
            cliente=self.cliente,
            usuario=self.admin_user,
            estado='CONFIRMADO',
            total=100,
            fecha=timezone.now() - timedelta(days=3),
        )
        self.venta_other_user = Venta.objects.create(
            cliente=self.cliente,
            usuario=self.other_user,
            estado='CONFIRMADO',
            total=200,
            fecha=timezone.now() - timedelta(days=1),
        )

    def test_admin_user_sees_all_sales(self):
        self.client.login(username='admin_test', password='12345678')

        response = self.client.get(reverse('ventas:lista'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['ventas'].count(), 2)

    def test_admin_filters_by_date_range_and_user(self):
        request = self.factory.get(
            '/admin/ventas/venta/',
            {
                'fecha_desde': (timezone.now() - timedelta(days=2)).date().strftime('%Y-%m-%d'),
                'fecha_hasta': timezone.now().date().strftime('%Y-%m-%d'),
                'usuario': self.other_user.id,
            },
        )
        request.user = self.admin_user

        queryset = self.venta_admin.get_queryset(request)

        self.assertEqual(list(queryset), [self.venta_other_user])
