from django import forms
from .models import Producto
from proveedores.models import Proveedor
from catalogo.models import Category


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'proveedor', 'categoria', 'precio_costo', 'porcentaje_ganancia', 'precio_venta', 'stock', 'stock_minimo', 'activo', 'descripcion', 'codigo_barras', 'imagen']
        widgets = {
                        'porcentaje_ganancia': forms.NumberInput(attrs={
                            'class': 'form-control',
                            'step': '0.01',
                            'min': '0',
                            'max': '100',
                            'placeholder': '0.00',
                        }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del producto'
            }),
            'proveedor': forms.Select(attrs={
                'class': 'form-control'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control',
                'id': 'categoriaSelect'
            }),
            'precio_costo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'precio_venta': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0'
            }),
            'stock_minimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción detallada del producto...'
            }),
            'codigo_barras': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código de barras (opcional)'
            }),
            'imagen': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor.objects.all()
        self.fields['proveedor'].empty_label = "Seleccionar proveedor"
        self.fields['categoria'].queryset = Category.objects.filter(is_active=True)
        self.fields['categoria'].empty_label = "Seleccionar categoría"
        
        # Hacer campos opcionales
        self.fields['proveedor'].required = False
        self.fields['categoria'].required = False
        self.fields['codigo_barras'].required = False
        self.fields['imagen'].required = False
        
        # Mejorar el widget de imagen
        self.fields['imagen'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*',
            'title': 'Seleccionar imagen del producto (JPG, PNG, GIF)'
        })
        
    def clean(self):
        cleaned_data = super().clean()
        precio_costo = cleaned_data.get('precio_costo')
        precio_venta = cleaned_data.get('precio_venta')
        
        if precio_costo and precio_venta:
            if precio_venta <= precio_costo:
                raise forms.ValidationError(
                    "El precio de venta debe ser mayor al precio de costo"
                )
        
        return cleaned_data
    
    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen and hasattr(imagen, 'content_type'):
            # Validar tamaño máximo (5MB)
            if imagen.size > 5 * 1024 * 1024:
                raise forms.ValidationError("La imagen no puede ser mayor a 5MB")
            
            # Validar tipo de archivo
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if imagen.content_type not in allowed_types:
                raise forms.ValidationError("Solo se permiten imágenes en formato JPG, PNG, GIF o WebP")
        
        return imagen
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre:
            # Verificar que no exista un producto con el mismo nombre
            existe = Producto.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk).exists()
            if existe:
                raise forms.ValidationError("Ya existe un producto con este nombre")
        return nombre
