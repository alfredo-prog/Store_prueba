from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from compras.models import Compra, DetalleCompra
from inventario.models import Producto
from proveedores.models import Proveedor


class CompraFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='compras_test_user',
            password='12345678',
            is_staff=True,
        )
        self.proveedor = Proveedor.objects.create(
            nombre='Proveedor Test',
            telefono='11111111',
            email='proveedor@test.com',
            direccion='Calle Falsa 123',
        )
        self.producto_1 = Producto.objects.create(
            nombre='Producto A',
            proveedor=self.proveedor,
            precio_costo=10,
            precio_venta=15,
            stock=0,
            codigo='P-A-001',
        )
        self.producto_2 = Producto.objects.create(
            nombre='Producto B',
            proveedor=self.proveedor,
            precio_costo=12,
            precio_venta=18,
            stock=0,
            codigo='P-B-001',
        )
        self.client = Client()
        self.client.force_login(self.user)

    def _build_payload(self, total_forms, rows):
        payload = {
            'proveedor': str(self.proveedor.id),
            'estado': 'PENDIENTE',
            'metodo_pago': 'EFECTIVO',
            'fecha': '2026-09-18T10:00',
            'actualizar_precios': 'on',
            'detalles-TOTAL_FORMS': str(total_forms),
            'detalles-INITIAL_FORMS': '0',
            'detalles-MIN_NUM_FORMS': '0',
            'detalles-MAX_NUM_FORMS': '1000',
        }
        for index, row in enumerate(rows):
            payload[f'detalles-{index}-producto'] = str(row['producto'].id)
            payload[f'detalles-{index}-cantidad'] = str(row['cantidad'])
            payload[f'detalles-{index}-precio_unitario'] = str(row['precio_unitario'])
            payload[f'detalles-{index}-precio_venta_unitario'] = str(row['precio_venta_unitario'])
        return payload

    def test_compra_con_un_producto_se_guarda(self):
        payload = self._build_payload(1, [{
            'producto': self.producto_1,
            'cantidad': 2,
            'precio_unitario': 10,
            'precio_venta_unitario': 15,
        }])

        response = self.client.post(reverse('compras:crear'), payload)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Compra.objects.count(), 1)
        compra = Compra.objects.get()
        self.assertEqual(compra.detalles.count(), 1)

    def test_compra_con_varios_productos_guarda_todos_los_items(self):
        payload = self._build_payload(2, [
            {
                'producto': self.producto_1,
                'cantidad': 2,
                'precio_unitario': 10,
                'precio_venta_unitario': 15,
            },
            {
                'producto': self.producto_2,
                'cantidad': 3,
                'precio_unitario': 12,
                'precio_venta_unitario': 18,
            },
        ])

        response = self.client.post(reverse('compras:crear'), payload)

        self.assertEqual(response.status_code, 302)
        compra = Compra.objects.get()
        self.assertEqual(compra.detalles.count(), 2)
        self.assertEqual(set(compra.detalles.values_list('producto_id', flat=True)), {
            self.producto_1.id,
            self.producto_2.id,
        })

    def test_compra_con_producto_seleccionado_sin_precio_manual_usa_precio_del_producto(self):
        payload = {
            'proveedor': str(self.proveedor.id),
            'estado': 'PENDIENTE',
            'metodo_pago': 'EFECTIVO',
            'fecha': '2026-09-18T10:00',
            'actualizar_precios': 'on',
            'detalles-TOTAL_FORMS': '1',
            'detalles-INITIAL_FORMS': '0',
            'detalles-MIN_NUM_FORMS': '0',
            'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-producto': str(self.producto_1.id),
            'detalles-0-cantidad': '6',
            'detalles-0-precio_unitario': '',
            'detalles-0-precio_venta_unitario': '',
        }

        response = self.client.post(reverse('compras:crear'), payload)

        self.assertEqual(response.status_code, 302)
        compra = Compra.objects.get()
        self.assertEqual(compra.detalles.count(), 1)
        self.assertEqual(float(compra.detalles.first().precio_unitario), float(self.producto_1.precio_costo))
