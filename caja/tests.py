from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from caja.models import Caja, MovimientoCaja


class CajaTransferenciaTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='cajauser',
            email='caja@example.com',
            password='testpass123'
        )
        self.caja = Caja.objects.create(
            usuario=self.user,
            saldo_inicial_efectivo=Decimal('100.00'),
            saldo_inicial_qr=Decimal('200.00'),
        )

    def test_traspaso_no_se_mezcla_con_ingreso_de_ventas(self):
        MovimientoCaja.objects.create(
            caja=self.caja,
            tipo='INGRESO',
            metodo_pago='EFECTIVO',
            categoria='VENTA',
            descripcion='Venta en efectivo',
            monto=Decimal('50.00'),
            usuario=self.user,
        )
        MovimientoCaja.objects.create(
            caja=self.caja,
            tipo='INGRESO',
            metodo_pago='EFECTIVO',
            categoria='TRASPASO',
            descripcion='Traspaso QR a efectivo',
            monto=Decimal('30.00'),
            usuario=self.user,
        )
        MovimientoCaja.objects.create(
            caja=self.caja,
            tipo='EGRESO',
            metodo_pago='QR',
            categoria='TRASPASO',
            descripcion='Traspaso efectivo a QR',
            monto=Decimal('30.00'),
            usuario=self.user,
        )

        self.assertEqual(self.caja.total_ingresos_ventas_efectivo, Decimal('50.00'))
        self.assertEqual(self.caja.total_traspasos_ingreso_efectivo, Decimal('30.00'))
        self.assertEqual(self.caja.total_traspasos_egreso_qr, Decimal('30.00'))
        self.assertEqual(self.caja.total_ingresos_efectivo, Decimal('80.00'))
        self.assertEqual(self.caja.saldo_esperado_efectivo, Decimal('180.00'))

    def test_resultado_bruto_suma_apertura_y_ventas_sin_egresos(self):
        MovimientoCaja.objects.create(
            caja=self.caja,
            tipo='INGRESO',
            metodo_pago='EFECTIVO',
            categoria='VENTA',
            descripcion='Venta en efectivo',
            monto=Decimal('50.00'),
            usuario=self.user,
        )
        MovimientoCaja.objects.create(
            caja=self.caja,
            tipo='INGRESO',
            metodo_pago='EFECTIVO',
            categoria='TRASPASO',
            descripcion='Traspaso a efectivo',
            monto=Decimal('30.00'),
            usuario=self.user,
        )
        MovimientoCaja.objects.create(
            caja=self.caja,
            tipo='EGRESO',
            metodo_pago='EFECTIVO',
            categoria='GASTO',
            descripcion='Gasto',
            monto=Decimal('20.00'),
            usuario=self.user,
        )

        self.assertEqual(self.caja.resultado_bruto_efectivo, Decimal('150.00'))
        self.assertEqual(self.caja.resultado_bruto_qr, Decimal('200.00'))
        self.assertEqual(self.caja.resultado_bruto_total, Decimal('350.00'))

    def test_dashboard_reporte_por_rango_suma_ingresos_y_egresos(self):
        self.client.force_login(self.user)

        caja_1 = Caja.objects.create(
            usuario=self.user,
            saldo_inicial_efectivo=Decimal('50.00'),
            saldo_inicial_qr=Decimal('10.00'),
            estado='CERRADA',
        )
        caja_2 = Caja.objects.create(
            usuario=self.user,
            saldo_inicial_efectivo=Decimal('20.00'),
            saldo_inicial_qr=Decimal('5.00'),
            estado='CERRADA',
        )

        MovimientoCaja.objects.create(
            caja=caja_1,
            tipo='INGRESO',
            metodo_pago='EFECTIVO',
            categoria='VENTA',
            descripcion='Venta del rango',
            monto=Decimal('80.00'),
            usuario=self.user,
            fecha=timezone.now() - timedelta(days=10),
        )
        MovimientoCaja.objects.create(
            caja=caja_1,
            tipo='EGRESO',
            metodo_pago='EFECTIVO',
            categoria='GASTO',
            descripcion='Gasto del rango',
            monto=Decimal('20.00'),
            usuario=self.user,
            fecha=timezone.now() - timedelta(days=8),
        )
        MovimientoCaja.objects.create(
            caja=caja_2,
            tipo='INGRESO',
            metodo_pago='QR',
            categoria='VENTA',
            descripcion='Venta fuera del rango',
            monto=Decimal('500.00'),
            usuario=self.user,
            fecha=timezone.now() - timedelta(days=70),
        )

        fecha_inicio = (timezone.localdate() - timedelta(days=30)).isoformat()
        fecha_fin = timezone.localdate().isoformat()
        response = self.client.get(
            f'/caja/?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['resumen_rango']['ingresos'], Decimal('80.00'))
        self.assertEqual(response.context['resumen_rango']['egresos'], Decimal('20.00'))
        self.assertEqual(response.context['resumen_rango']['saldo'], Decimal('60.00'))

    def test_dashboard_admin_filtra_por_usuario(self):
        admin = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123',
        )
        otro_usuario = get_user_model().objects.create_user(
            username='otro_usuario',
            password='testpass123',
        )
        otra_caja = Caja.objects.create(
            usuario=otro_usuario,
            estado='CERRADA',
        )
        MovimientoCaja.objects.create(
            caja=self.caja,
            tipo='INGRESO',
            metodo_pago='EFECTIVO',
            categoria='VENTA',
            descripcion='Venta del usuario seleccionado',
            monto=Decimal('40.00'),
            usuario=self.user,
        )
        MovimientoCaja.objects.create(
            caja=otra_caja,
            tipo='INGRESO',
            metodo_pago='EFECTIVO',
            categoria='VENTA',
            descripcion='Venta de otro usuario',
            monto=Decimal('90.00'),
            usuario=otro_usuario,
        )

        self.client.force_login(admin)
        response = self.client.get(
            f'/caja/?usuario={self.user.id}&'
            f'fecha_inicio={(timezone.localdate() - timedelta(days=1)).isoformat()}&'
            f'fecha_fin={timezone.localdate().isoformat()}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['resumen_rango']['ingresos'], Decimal('40.00'))
        self.assertEqual(response.context['resumen_rango']['cantidad_cajas'], 1)

    def test_dashboard_admin_muestra_historial_del_usuario_filtrado_sin_caja_abierta(self):
        admin = get_user_model().objects.create_superuser(
            username='admin_historial',
            email='adminhistorial@example.com',
            password='testpass123',
        )
        otro_usuario = get_user_model().objects.create_user(
            username='otro_historial',
            password='testpass123',
        )
        caja_cerrada = Caja.objects.create(
            usuario=self.user,
            saldo_inicial_efectivo=Decimal('10.00'),
            saldo_inicial_qr=Decimal('0.00'),
            estado='CERRADA',
        )
        caja_abierta_otra = Caja.objects.create(
            usuario=otro_usuario,
            saldo_inicial_efectivo=Decimal('30.00'),
            saldo_inicial_qr=Decimal('0.00'),
            estado='ABIERTA',
        )
        movimiento_usuario = MovimientoCaja.objects.create(
            caja=caja_cerrada,
            tipo='INGRESO',
            metodo_pago='EFECTIVO',
            categoria='VENTA',
            descripcion='Historial cerrado del usuario seleccionado',
            monto=Decimal('55.00'),
            usuario=self.user,
        )
        MovimientoCaja.objects.create(
            caja=caja_abierta_otra,
            tipo='INGRESO',
            metodo_pago='EFECTIVO',
            categoria='VENTA',
            descripcion='Movimiento de otro usuario',
            monto=Decimal('99.00'),
            usuario=otro_usuario,
        )

        self.client.force_login(admin)
        response = self.client.get(
            f'/caja/?usuario={self.user.id}&'
            f'fecha_inicio={(timezone.localdate() - timedelta(days=30)).isoformat()}&'
            f'fecha_fin={timezone.localdate().isoformat()}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['movimientos_recientes']), [movimiento_usuario])
