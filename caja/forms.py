from django import forms
from .models import Caja, MovimientoCaja


class AperturaCajaForm(forms.ModelForm):
    class Meta:
        model = Caja
        fields = ['saldo_inicial_efectivo', 'saldo_inicial_qr', 'fecha_apertura']
        widgets = {
            'saldo_inicial_efectivo': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '0.00',
                    'step': '0.01',
                    'min': '0'
                }
            ),
            'saldo_inicial_qr': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '0.00',
                    'step': '0.01',
                    'min': '0'
                }
            ),
            'fecha_apertura': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['saldo_inicial_efectivo'].label = "Saldo inicial en efectivo"
        self.fields['saldo_inicial_qr'].label = "Saldo inicial en QR"
        self.fields['fecha_apertura'].label = "Fecha de apertura"
        
        # Campo fecha siempre visible para todos los usuarios
        print(f"AperturaCajaForm - Usuario: {user}, is_superuser: {user.is_superuser if user else 'None'}")


class MovimientoCajaForm(forms.ModelForm):
    class Meta:
        model = MovimientoCaja
        fields = ['tipo', 'metodo_pago', 'categoria', 'descripcion', 'monto', 'referencia', 'fecha']
        widgets = {
            'tipo': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'metodo_pago': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'categoria': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'descripcion': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Descripción del movimiento'
                }
            ),
            'monto': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '0.00',
                    'step': '0.01',
                    'min': '0.01'
                }
            ),
            'referencia': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Referencia (opcional)'
                }
            ),
            'fecha': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['tipo'].label = "Tipo de movimiento"
        self.fields['metodo_pago'].label = "Método de pago"
        self.fields['categoria'].label = "Categoría"
        self.fields['descripcion'].label = "Descripción"
        self.fields['monto'].label = "Monto"
        self.fields['referencia'].label = "Referencia"
        self.fields['referencia'].required = False
        self.fields['fecha'].label = "Fecha"
        
        # Campo fecha siempre visible para todos los usuarios
        print(f"MovimientoCajaForm - Usuario: {user}, is_superuser: {user.is_superuser if user else 'None'}")


class CierreCajaForm(forms.Form):
    saldo_final_efectivo = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }
        ),
        label="Saldo final en efectivo"
    )
    
    saldo_final_qr = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }
        ),
        label="Saldo final en QR"
    )
    
    observaciones = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones sobre el cierre de caja...'
            }
        ),
        label="Observaciones",
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        saldo_efectivo = cleaned_data.get('saldo_final_efectivo')
        saldo_qr = cleaned_data.get('saldo_final_qr')
        
        if saldo_efectivo is not None and saldo_efectivo < 0:
            self.add_error('saldo_final_efectivo', 'El saldo no puede ser negativo')
        
        if saldo_qr is not None and saldo_qr < 0:
            self.add_error('saldo_final_qr', 'El saldo no puede ser negativo')
        
        return cleaned_data
