// Variables globales
let filaCounter = 0;
let availableProducts = [];
const CART_STORAGE_KEY = 'pos_venta_cart_state';

// Mostrar/ocultar campo Cliente
function ocultarCliente() {
    const clienteField = document.getElementById('clienteField');
    const btnOcultar = document.getElementById('btnOcultarCliente');
    const btnMostrar = document.getElementById('btnMostrarCliente');
    if (clienteField) clienteField.style.display = 'none';
    if (btnOcultar) btnOcultar.style.display = 'none';
    if (btnMostrar) btnMostrar.style.display = '';
}

function mostrarCliente() {
    const clienteField = document.getElementById('clienteField');
    const btnOcultar = document.getElementById('btnOcultarCliente');
    const btnMostrar = document.getElementById('btnMostrarCliente');
    if (clienteField) clienteField.style.display = '';
    if (btnOcultar) btnOcultar.style.display = '';
    if (btnMostrar) btnMostrar.style.display = 'none';
}

// Mostrar/ocultar campo Descuento
function ocultarDescuento() {
    const descuentoField = document.getElementById('descuentoField');
    const btnOcultar = document.getElementById('btnOcultarDescuento');
    const btnMostrar = document.getElementById('btnMostrarDescuento');
    if (descuentoField) descuentoField.style.display = 'none';
    if (btnOcultar) btnOcultar.style.display = 'none';
    if (btnMostrar) btnMostrar.style.display = '';
}

function mostrarDescuento() {
    const descuentoField = document.getElementById('descuentoField');
    const btnOcultar = document.getElementById('btnOcultarDescuento');
    const btnMostrar = document.getElementById('btnMostrarDescuento');
    if (descuentoField) descuentoField.style.display = '';
    if (btnOcultar) btnOcultar.style.display = '';
    if (btnMostrar) btnMostrar.style.display = 'none';
}

// Inicializar cuando DOM esté listo
window.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado - Inicializando POS');
    ocultarCliente();
    ocultarDescuento();
    loadAvailableProducts();
    restoreCartFromStorage();
    setupEventListeners();
    togglePaymentFields();
});

// Mostrar/ocultar campos de pago según método
function togglePaymentFields() {
    const metodoPago = document.getElementById('metodo_pago');
    if (!metodoPago) return;

    const montoEfectivoGroup = document.getElementById('montoEfectivoGroup');
    const cambioGroup = document.getElementById('cambioGroup');

    if (metodoPago.value === 'EFECTIVO') {
        if (montoEfectivoGroup) montoEfectivoGroup.style.display = 'block';
        if (cambioGroup) cambioGroup.style.display = 'block';
    } else {
        if (montoEfectivoGroup) montoEfectivoGroup.style.display = 'none';
        if (cambioGroup) cambioGroup.style.display = 'none';

        const montoEfectivoInput = document.getElementById('monto_efectivo');
        const cambioInput = document.getElementById('cambio');

        if (montoEfectivoInput) montoEfectivoInput.value = '';
        if (cambioInput) cambioInput.value = 'Bs.0.00';
    }
}

function buildCartRow(item) {
    const rowId = item.rowId || ++filaCounter;
    const fila = document.createElement("tr");
    fila.id = 'fila_' + rowId;
    fila.dataset.productId = item.productId || '';

    const hasProductId = !!item.productId;
    const productoInput = hasProductId
        ? '<td><input type="hidden" name="producto_id[]" value="' + item.productId + '">' +
          '<input type="text" name="producto[]" value="' + (item.producto || '').replace(/"/g, '&quot;') + '" readonly class="form-control"></td>'
        : '<td><input type="text" name="producto[]" value="' + (item.producto || '').replace(/"/g, '&quot;') + '" placeholder="Buscar producto..." oninput="buscarProducto(this)" class="form-control"></td>';

    fila.innerHTML = '<td class="item-numero">' + rowId + '</td>' +
        '<td><input type="number" name="cantidad[]" value="' + (item.cantidad || 1) + '" min="1" oninput="calcularSubtotal(this)" class="form-control"></td>' +
        productoInput +
        '<td><input type="number" name="precio[]" value="' + (item.precio || '0.00') + '" step="0.01" min="0" oninput="calcularSubtotal(this)" class="form-control"></td>' +
        '<td><input type="text" name="subtotal[]" value="' + (item.subtotal || '0.00') + '" readonly class="form-control"></td>' +
        '<td><button type="button" onclick="eliminarFila(' + rowId + ')" class="btn btn-danger btn-sm"><i class="fas fa-trash"></i></button></td>';

    return fila;
}

function persistCartToStorage() {
    try {
        const filas = Array.from(document.querySelectorAll('#detalleBody tr'));
        const state = filas.map((fila, index) => ({
            rowId: parseInt(fila.id.replace('fila_', ''), 10) || index + 1,
            productId: fila.dataset.productId || '',
            producto: fila.querySelector("[name='producto[]']")?.value || '',
            cantidad: fila.querySelector("[name='cantidad[]']")?.value || 1,
            precio: fila.querySelector("[name='precio[]']")?.value || '0.00',
            subtotal: fila.querySelector("[name='subtotal[]']")?.value || '0.00'
        }));
        localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
        console.warn('No se pudo guardar el carrito:', error);
    }
}

function restoreCartFromStorage() {
    try {
        const savedData = localStorage.getItem(CART_STORAGE_KEY);
        if (!savedData) return false;
        const state = JSON.parse(savedData);
        if (!Array.isArray(state) || state.length === 0) return false;

        const tbody = document.querySelector('#detalleBody');
        if (!tbody) return false;

        tbody.innerHTML = '';
        state.forEach(item => {
            const fila = buildCartRow(item);
            tbody.appendChild(fila);
        });

        reordenarItems();
        actualizarTotales();
        return true;
    } catch (error) {
        console.warn('No se pudo restaurar el carrito:', error);
        return false;
    }
}

function clearCartStorage() {
    try {
        localStorage.removeItem(CART_STORAGE_KEY);
    } catch (error) {
        console.warn('No se pudo limpiar el carrito:', error);
    }
}

// Agregar fila manual a la tabla
function agregarFila() {
    filaCounter++;
    const tbody = document.querySelector("#detalleBody");
    const fila = buildCartRow({ rowId: filaCounter, producto: '', cantidad: 1, precio: '0.00', subtotal: '0.00' });
    
    tbody.appendChild(fila);
    actualizarTotales();
    reordenarItems();
}

// Eliminar fila
function eliminarFila(filaId) {
    const fila = document.getElementById('fila_' + filaId);
    if (fila) {
        fila.remove();
        actualizarTotales();
        reordenarItems();
    }
}

// Reordenar números de items
function reordenarItems() {
    const filas = document.querySelectorAll("#detalleBody tr");
    filas.forEach((fila, index) => {
        const itemNumero = fila.querySelector('.item-numero');
        if (itemNumero) {
            itemNumero.textContent = index + 1;
        }

        const rowIdInput = fila.id.replace('fila_', '');
        const rowId = parseInt(rowIdInput, 10) || index + 1;
        fila.id = 'fila_' + rowId;
        const button = fila.querySelector('button');
        if (button) {
            button.setAttribute('onclick', 'eliminarFila(' + rowId + ')');
        }
    });
    persistCartToStorage();
}

// Calcular subtotal de una fila
function calcularSubtotal(input) {
    const fila = input.closest("tr");
    const cantidad = parseFloat(fila.querySelector("[name='cantidad[]']").value) || 0;
    const precio = parseFloat(fila.querySelector("[name='precio[]']").value) || 0;
    const subtotal = cantidad * precio;
    fila.querySelector("[name='subtotal[]']").value = subtotal.toFixed(2);
    actualizarTotales();
}

// Buscar producto en fila y autocompletar precio
function buscarProducto(input) {
    if (typeof availableProducts === 'undefined' || !availableProducts.length) return;
    const searchTerm = input.value.toLowerCase();
    const fila = input.closest("tr");
    const precioInput = fila.querySelector("[name='precio[]']");
    if (!precioInput || searchTerm.length < 2) return;

    const producto = availableProducts.find(p =>
        p.name.toLowerCase().includes(searchTerm) || p.code.toLowerCase().includes(searchTerm)
    );

    if (producto) {
        precioInput.value = producto.price.toFixed(2);
        calcularSubtotal(precioInput);
    } else {
        precioInput.value = '';
        calcularSubtotal(precioInput);
    }
}

// Actualizar totales y mostrar/ocultar secciones
function actualizarTotales() {
    const filas = document.querySelectorAll("#detalleBody tr");
    let subtotal = 0;

    filas.forEach(fila => {
        subtotal += parseFloat(fila.querySelector("[name='subtotal[]']").value) || 0;
    });

    persistCartToStorage();

    const totalGeneralEl = document.getElementById("totalGeneral");
    if (totalGeneralEl) totalGeneralEl.textContent = 'Bs.' + subtotal.toFixed(2);

    const tieneProductos = filas.length > 0;
    const detalleTable = document.getElementById("detalle");
    const mensajeVacio = document.getElementById("mensajeVacio");
    const cartSummary = document.getElementById("cartSummary");
    const paymentSection = document.getElementById("paymentSection");
    const confirmarBtn = document.getElementById("confirmarBtn");

    if (detalleTable) detalleTable.style.display = tieneProductos ? "table" : "none";
    if (mensajeVacio) mensajeVacio.style.display = tieneProductos ? "none" : "block";
    if (cartSummary) cartSummary.style.display = tieneProductos ? "block" : "none";
    if (paymentSection) paymentSection.style.display = tieneProductos ? "block" : "none";
    if (confirmarBtn) confirmarBtn.disabled = !tieneProductos;

    updateSummary();
}

// Agregar producto desde catálogo
function addToCart(productId) {
    const product = availableProducts.find(p => p.id === productId);
    if (!product) return;
    // Si el producto ya está en el carrito, aumentar la cantidad
    const tbody = document.querySelector("#detalleBody");
    const filas = Array.from(tbody.querySelectorAll('tr'));
    const existingRow = filas.find(r => r.dataset.productId == productId);

    if (existingRow) {
        const cantidadInput = existingRow.querySelector("[name='cantidad[]']");
        if (cantidadInput) {
            cantidadInput.value = (parseFloat(cantidadInput.value) || 0) + 1;
            calcularSubtotal(cantidadInput);
            actualizarTotales();
            return;
        }
    }

    // Si no existe, crear una nueva fila con el product id
    filaCounter++;
    const fila = document.createElement("tr");
    fila.id = 'fila_' + filaCounter;
    fila.dataset.productId = productId;

    fila.innerHTML = '<td class="item-numero">' + filaCounter + '</td>' +
        '<td><input type="number" name="cantidad[]" value="1" min="1" oninput="calcularSubtotal(this)" class="form-control"></td>' +
        '<td><input type="hidden" name="producto_id[]" value="' + product.id + '">' +
            '<input type="text" name="producto[]" value="' + product.name + '" readonly class="form-control"></td>' +
        '<td><input type="number" name="precio[]" value="' + product.price.toFixed(2) + '" step="0.01" oninput="calcularSubtotal(this)" class="form-control"></td>' +
        '<td><input type="text" name="subtotal[]" value="' + product.price.toFixed(2) + '" readonly class="form-control"></td>' +
        '<td><button type="button" onclick="eliminarFila(' + filaCounter + ')" class="btn btn-danger btn-sm"><i class="fas fa-trash"></i></button></td>';

    tbody.appendChild(fila);
    calcularSubtotal(fila.querySelector("[name='cantidad[]']"));
    actualizarTotales();
    reordenarItems();
}

// Cargar productos disponibles desde JSON
function loadAvailableProducts() {
    const grid = document.getElementById('productsGrid');
    if (!grid) {
        console.error('Grid de productos no encontrado');
        return;
    }
    
    const productsDataStr = grid.getAttribute('data-products');
    console.log('Datos de productos en atributo:', productsDataStr);
    let productsData = [];

    if (productsDataStr && productsDataStr !== '[]' && productsDataStr !== '') {
        try {
            productsData = JSON.parse(productsDataStr);
            console.log('Productos parseados:', productsData);
        } catch (e) {
            console.error('Error parsing productos:', e);
        }
    } else {
        console.warn('No hay datos de productos en data-products');
    }

    availableProducts = productsData.map(product => ({
        id: product.id || 0,
        name: (product.nombre || '').toString(),
        price: parseFloat(product.precio_venta || 0),
        stock: parseInt(product.stock || 0),
        code: (product.codigo || '').toString()
    }));

    console.log('Productos disponibles cargados:', availableProducts);
    displayProducts(availableProducts);
    updateProductCounter(availableProducts.length);
}

// Mostrar productos en grid
function displayProducts(products) {
    const grid = document.getElementById('productsGrid');
    if (!grid) {
        console.error('Grid no encontrado');
        return;
    }

    grid.innerHTML = '';

    if (!products || products.length === 0) {
        grid.innerHTML = '<div class="col-12 text-center py-5 text-muted"><i class="fas fa-box-open fa-3x mb-2"></i><p class="mt-3">No hay productos disponibles</p></div>';
        return;
    }

    products.forEach(product => {
        const card = document.createElement('div');
        card.className = 'col-md-6 col-lg-4 mb-3';
        card.innerHTML = '<div class="card h-100 shadow-sm">' +
            '<div class="card-body">' +
            '<h6 class="card-title fw-bold">' + product.name + '</h6>' +
            '<p class="card-text text-primary fw-bold fs-5 mb-1">Bs.' + product.price.toFixed(2) + '</p>' +
            '<p class="card-text text-muted small mb-2">Stock: <span class="' + (product.stock <= 0 ? 'text-danger' : 'text-success') + ' fw-bold">' + product.stock + '</span></p>' +
            '<button type="button" class="btn btn-sm btn-primary w-100" onclick="addToCart(' + product.id + ')" ' + (product.stock <= 0 ? 'disabled' : '') + '>' +
            '<i class="fas fa-plus me-1"></i>' + (product.stock <= 0 ? 'Sin stock' : 'Agregar') +
            '</button></div></div>';
        grid.appendChild(card);
    });
    console.log('Se mostraron ' + products.length + ' productos');
}

// Actualizar contador de productos
function updateProductCounter(count, isFiltered) {
    const counterElement = document.getElementById('productCount');
    if (counterElement) {
        if (isFiltered) {
            counterElement.textContent = count + ' de ' + availableProducts.length;
        } else {
            counterElement.textContent = count;
        }
    }
}

// Buscar productos en catálogo
function searchProducts() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) {
        console.error('Search input no encontrado');
        return;
    }
    
    const searchTerm = (searchInput.value || '').toLowerCase().trim();
    console.log('Buscando:', searchTerm);
    console.log('Productos disponibles:', availableProducts);
    
    let productsToShow = availableProducts;

    if (searchTerm.length > 0) {
        productsToShow = availableProducts.filter(product =>
            (product.name || '').toLowerCase().includes(searchTerm) ||
            (product.code || '').toLowerCase().includes(searchTerm)
        );
        console.log('Productos filtrados:', productsToShow);
    }

    displayProducts(productsToShow);
    updateProductCounter(productsToShow.length, searchTerm.length > 0);
}

// Actualizar resumen de venta
function updateSummary() {
    try {
        const filas = document.querySelectorAll("#detalleBody tr");
        let subtotal = 0;

        filas.forEach(fila => {
            subtotal += parseFloat(fila.querySelector("[name='subtotal[]']").value) || 0;
        });

        const discountInput = document.getElementById('descuento');
        const discount = parseFloat(discountInput ? discountInput.value : 0) || 0;
        const total = subtotal * (1 - discount / 100);

        const subtotalEl = document.getElementById('subtotal');
        const discountEl = document.getElementById('discount');
        const totalEl = document.getElementById('total');

        if (subtotalEl) subtotalEl.textContent = 'Bs.' + subtotal.toFixed(2);
        if (discountEl) discountEl.textContent = 'Bs.' + (subtotal * discount / 100).toFixed(2);
        if (totalEl) totalEl.textContent = 'Bs.' + total.toFixed(2);

        const metodoPago = document.getElementById('metodo_pago');
        const montoEfectivoInput = document.getElementById('monto_efectivo');
        const cambioInput = document.getElementById('cambio');

        if (metodoPago && cambioInput) {
            const efectivo = parseFloat(montoEfectivoInput ? montoEfectivoInput.value : 0) || 0;
            const cambio = efectivo - total;
            cambioInput.value = cambio >= 0 ? 'Bs.' + cambio.toFixed(2) : 'Bs.0.00';
        }
    } catch (error) {
        console.error('Error updating summary:', error);
    }
}

// Configurar event listeners
function setupEventListeners() {
    console.log('Configurando event listeners');
    
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.querySelector('.search-btn');
    
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = (e.target.value || '').toLowerCase();
            console.log('Input búsqueda:', searchTerm);
            searchProducts();
        });
        
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchProducts();
            }
        });
    }

    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            console.log('Click en botón búsqueda');
            searchProducts();
        });
    }

    const ventaForm = document.getElementById('ventaForm');
    if (ventaForm) {
        ventaForm.addEventListener('submit', function(e) {
            console.log('🔵 Formulario de venta siendo enviado');
            const filas = document.querySelectorAll("#detalleBody tr");
            if (filas.length === 0) {
                e.preventDefault();
                alert('Debe agregar al menos un producto a la venta');
                return false;
            }

            let productosValidos = true;
            filas.forEach(fila => {
                const cantidad = parseFloat(fila.querySelector("[name='cantidad[]']").value) || 0;
                const precio = parseFloat(fila.querySelector("[name='precio[]']").value) || 0;
                const producto = fila.querySelector("[name='producto[]']").value;

                if (!producto || cantidad <= 0 || precio <= 0) {
                    productosValidos = false;
                }
            });

            if (!productosValidos) {
                e.preventDefault();
                alert('Todos los productos deben tener nombre, cantidad y precio validos');
                return false;
            }

            const metodoPago = document.getElementById('metodo_pago');
            if (!metodoPago || !metodoPago.value) {
                e.preventDefault();
                alert('Debe seleccionar un metodo de pago');
                return false;
            }

            if (metodoPago.value === 'EFECTIVO') {
                const totalText = document.getElementById('total').textContent.replace(/Bs\.\s?/g, '');
                const total = parseFloat(totalText) || 0;
                const montoEfectivoInput = document.getElementById('monto_efectivo');
                const montoRecibido = parseFloat(montoEfectivoInput ? montoEfectivoInput.value : 0) || 0;
                if (montoRecibido < total) {
                    e.preventDefault();
                    alert('El monto recibido es insuficiente');
                    return false;
                }
            }


            console.log('✅ Validaciones pasadas, enviando formulario...');
            clearCartStorage();
            return true;
        });
    }
    
    console.log('Event listeners configurados');
}

// Inicializar
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Inicializando POS desde DOMContentLoaded');
    });
} else {
    console.log('Inicializando POS inmediatamente');
}
