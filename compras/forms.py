from django import forms
from .models import Compra, DetalleCompra
from proveedores.models import Proveedor
from inventario.models import Producto

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['proveedor', 'estado', 'metodo_pago', 'fecha']
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Campo fecha siempre visible para todos los usuarios
        print(f"CompraForm - Usuario: {user}, is_superuser: {user.is_superuser if user else 'None'}")

class DetalleCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ['producto', 'cantidad', 'precio_unitario']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
        }

    def has_changed(self):
        """Determina si el formulario ha cambiado"""
        if not self.is_bound:
            return False
        
        # Para formularios nuevos (sin pk), considerar que ha cambiado si tiene datos
        if not self.instance.pk:
            producto = self.data.get(f'{self.prefix}-producto')
            cantidad = self.data.get(f'{self.prefix}-cantidad')
            precio_unitario = self.data.get(f'{self.prefix}-precio_unitario')
            
            # Si tiene datos, considerar que ha cambiado
            if producto and cantidad and precio_unitario and producto != '' and cantidad != '' and precio_unitario != '':
                return True
            return False
        
        # Para formularios existentes, usar la lógica normal
        changed_data = super().changed_data
        if not changed_data:
            return False
        
        # Si todos los campos están vacíos, considerar que no ha cambiado
        producto = self.cleaned_data.get('producto') if hasattr(self, 'cleaned_data') else None
        cantidad = self.cleaned_data.get('cantidad') if hasattr(self, 'cleaned_data') else None
        precio_unitario = self.cleaned_data.get('precio_unitario') if hasattr(self, 'cleaned_data') else None
        
        if not producto and not cantidad and not precio_unitario:
            return False
        
        return True

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get('producto')
        cantidad = cleaned_data.get('cantidad')
        precio_unitario = cleaned_data.get('precio_unitario')

        # Si el formulario está completamente vacío, no validar
        if not producto and not cantidad and not precio_unitario:
            return cleaned_data

        # Si hay algún dato, validar que todos estén presentes
        if not producto:
            self.add_error('producto', 'Debe seleccionar un producto.')
        if not cantidad:
            self.add_error('cantidad', 'Debe ingresar una cantidad.')
        if not precio_unitario:
            self.add_error('precio_unitario', 'Debe ingresar un precio unitario.')

        return cleaned_data

# Formset para creación (con formularios extra)
DetalleCompraFormSet = forms.inlineformset_factory(
    Compra, 
    DetalleCompra, 
    form=DetalleCompraForm, 
    extra=1,   # solo una fila inicial
    can_delete=True,
    min_num=0,
    validate_min=False,
    validate_max=False,
    absolute_max=1000
)

# Formset para edición (sin formularios extra)
DetalleCompraFormSetEdicion = forms.inlineformset_factory(
    Compra, 
    DetalleCompra, 
    form=DetalleCompraForm, 
    extra=0,  # Sin formularios extra en edición
    can_delete=True,
    min_num=1,
    validate_min=True,
    validate_max=False,
    absolute_max=1000
)
