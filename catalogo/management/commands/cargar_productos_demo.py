from django.core.management.base import BaseCommand
from catalogo.models import Category, Product

class Command(BaseCommand):
    help = 'Carga productos de ejemplo en el catálogo.'

    def handle(self, *args, **kwargs):
        cat, _ = Category.objects.get_or_create(name='Bebidas', defaults={'description': 'Bebidas y refrescos', 'is_active': True})
        productos = [
            {'code': 'BEB001', 'barcode': '750100000001', 'name': 'Coca Cola 600ml', 'cost_price': 8.00, 'sale_price': 12.00, 'stock': 50, 'min_stock': 10, 'description': 'Refresco Coca Cola 600ml'},
            {'code': 'BEB002', 'barcode': '750100000002', 'name': 'Pepsi 600ml', 'cost_price': 7.50, 'sale_price': 11.50, 'stock': 40, 'min_stock': 10, 'description': 'Refresco Pepsi 600ml'},
            {'code': 'BEB003', 'barcode': '750100000003', 'name': 'Agua Ciel 600ml', 'cost_price': 5.00, 'sale_price': 8.00, 'stock': 60, 'min_stock': 15, 'description': 'Agua purificada Ciel 600ml'},
            {'code': 'BEB004', 'barcode': '750100000004', 'name': 'Fanta Naranja 600ml', 'cost_price': 7.80, 'sale_price': 12.00, 'stock': 30, 'min_stock': 8, 'description': 'Refresco Fanta Naranja 600ml'},
            {'code': 'BEB005', 'barcode': '750100000005', 'name': 'Sprite 600ml', 'cost_price': 7.80, 'sale_price': 12.00, 'stock': 35, 'min_stock': 8, 'description': 'Refresco Sprite 600ml'},
        ]
        for prod in productos:
            Product.objects.get_or_create(
                code=prod['code'],
                defaults={
                    'barcode': prod['barcode'],
                    'name': prod['name'],
                    'category': cat,
                    'cost_price': prod['cost_price'],
                    'sale_price': prod['sale_price'],
                    'stock': prod['stock'],
                    'min_stock': prod['min_stock'],
                    'description': prod['description'],
                    'is_active': True,
                }
            )
        self.stdout.write(self.style.SUCCESS('Productos de ejemplo cargados.'))
