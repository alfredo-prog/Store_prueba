from django import forms
from .models import Venta, DetalleVenta
from inventario.models import Producto
from clientes.models import Cliente


class VentaForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(), 
        label="Cliente", 
        required=False,
        empty_label="Cliente ocasional"
    )
    
    metodo_pago = forms.ChoiceField(
        choices=Venta.METODO_PAGO_CHOICES,
        label="Método de pago",
        required=False
    )
    
    monto_recibido = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False,
        label="Monto recibido"
    )

    class Meta:
        model = Venta
        fields = ['cliente', 'metodo_pago', 'monto_recibido', 'fecha']
        widgets = {
            'fecha': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ['producto', 'cantidad', 'precio_unitario', 'descuento_porcentaje']

    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(activo=True), 
        label="Producto"
    )
    cantidad = forms.DecimalField(
        min_value=0.01, 
        label="Cantidad",
        decimal_places=2
    )
    precio_unitario = forms.DecimalField(
        min_value=0, 
        label="Precio unitario",
        decimal_places=2
    )
    descuento_porcentaje = forms.DecimalField(
        min_value=0, 
        max_value=100, 
        required=False, 
        label="% Descuento", 
        initial=0,
        decimal_places=2
    )

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get('producto')
        cantidad = cleaned_data.get('cantidad')
        if producto and cantidad:
            if producto.stock < cantidad:
                raise forms.ValidationError(
                    f"No hay suficiente stock de {producto.name}. "
                    f"Stock disponible: {producto.stock}"
                )
        return cleaned_data


class VentaPOSForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(), 
        label="Cliente", 
        required=False,
        empty_label="Cliente ocasional"
    )
    
    metodo_pago = forms.ChoiceField(
        choices=Venta.METODO_PAGO_CHOICES,
        label="Método de pago",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    monto_recibido = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False,
        label="Monto recibido",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    descuento_general = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False,
        label="Descuento general",
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
