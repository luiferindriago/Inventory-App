# Manual de Usuario
## Sistema de Inventario — Herrajes & Baños

---

## Contenido

1. [Acceso y navegación](#acceso)
2. [Dashboard](#dashboard)
3. [Inventario](#inventario)
4. [Registrar una venta](#ventas)
5. [Historial de ventas](#historial)
6. [Pedidos a proveedores](#pedidos)
7. [Clientes](#clientes)
8. [Finanzas](#finanzas)
9. [Exportar datos a Excel](#exportar)
10. [Preguntas frecuentes](#faq)

---

## 1. Acceso y navegación {#acceso}

La app se abre desde cualquier navegador (Chrome, Safari, Edge) en computadora o teléfono celular. No requiere instalación.

**URL de la app:** `https://herrajes-inventario.streamlit.app` *(o la que hayas configurado)*

La navegación está en el panel izquierdo. Toca o haz clic en cualquier sección para ir a ella:

| Sección | Para qué sirve |
|---|---|
| 🏠 Dashboard | Vista general del negocio |
| 📦 Inventario | Ver y editar productos |
| 🛒 Nueva Venta | Registrar una venta |
| 📋 Historial Ventas | Consultar ventas pasadas |
| 🚚 Pedidos | Órdenes de compra a proveedores |
| 👥 Clientes | Directorio de clientes |
| 💰 Finanzas | Ingresos, egresos y balance |

---

## 2. Dashboard {#dashboard}

El dashboard es la pantalla de inicio. Muestra de un vistazo:

- **Ingresos totales** — todo el dinero que ha entrado
- **Egresos totales** — todo el dinero que ha salido
- **Balance neto** — la diferencia entre ingresos y egresos
- **Ventas completadas** — cantidad de ventas registradas

### Alertas de stock bajo
En la columna derecha aparecen los productos que tienen el stock igual o por debajo del mínimo configurado:
- 🔴 = agotado (stock en 0)
- 🟡 = por debajo del mínimo

### Gráfico de ingresos por mes
Muestra la evolución de ingresos mes a mes para que veas la tendencia del negocio.

---

## 3. Inventario {#inventario}

### Ver el inventario

Ve a **📦 Inventario → pestaña "Ver inventario"**.

Puedes:
- **Buscar** un producto escribiendo su código o parte del nombre
- **Filtrar por categoría** usando el selector (Bisagra, Clip, Manilla, etc.)
- Ver el **margen de ganancia** calculado automáticamente por producto
- Ver el **estado del stock** de cada producto (🟢 OK / 🟡 Bajo / 🔴 Agotado)

### Editar un producto (precios, stock mínimo, etc.)

1. Ve a **📦 Inventario → pestaña "Agregar / Editar producto"**
2. En **Modo** selecciona **"Editar existente"**
3. En el selector elige el producto que quieres modificar
4. Cambia los campos que necesites:
   - **Precio costo** — lo que pagaste al proveedor
   - **Precio venta** — lo que cobras al cliente
   - **Stock mínimo** — a partir de qué cantidad quieres recibir alerta de reorden
   - **Stock actual** — puedes corregirlo si hubo un conteo físico
5. Haz clic en **💾 Guardar producto**

> **Tip:** Cuando ingreses precio de costo y venta, la app te muestra el margen de ganancia en tiempo real antes de guardar.

### Agregar un producto nuevo

1. Ve a **📦 Inventario → pestaña "Agregar / Editar producto"**
2. En **Modo** selecciona **"Agregar nuevo"**
3. Completa los campos:
   - **Código** — identificador único (ej. BA01). Se guarda en mayúsculas automáticamente
   - **Descripción** — nombre completo del producto
   - **Categoría** — Bisagra, Clip, Manilla, Pomo, Policarbonato, Kit u Otro
   - **Stock actual** — cuántas unidades tienes ahora
   - **Stock mínimo** — cantidad mínima antes de que aparezca alerta de reorden
   - **Precio costo** — lo que pagaste
   - **Precio venta** — lo que cobras
   - **Unidad** — Unidad, Par, Caja, Metro o Kit
4. Haz clic en **💾 Guardar producto**

### Ajustar el punto de alerta de reorden

El **stock mínimo** es el número que dispara la alerta 🟡 en el dashboard y en el inventario.

Por ejemplo: si pones stock mínimo = 5, cuando el producto llegue a 5 unidades o menos aparecerá la alerta automáticamente.

Para cambiarlo: edita el producto → cambia el campo **Stock mínimo** → guarda.

---

## 4. Registrar una venta {#ventas}

1. Ve a **🛒 Nueva Venta**
2. Selecciona el **cliente** (o déjalo en "Sin cliente" si es venta directa)
3. Confirma la **fecha** (por defecto es el día de hoy)
4. Selecciona el **estado**:
   - **Completada** — descuenta el stock y registra el ingreso automáticamente
   - **Pendiente de pago** — queda registrada pero no mueve stock ni finanzas hasta que la completes
   - **Cancelada** — queda en el historial pero no afecta nada
5. Agrega los productos uno por uno:
   - Elige el producto del selector
   - Ajusta la cantidad
   - Verifica o modifica el precio unitario (viene precargado con el precio de venta)
   - Clic en **➕ Agregar a la venta**
6. Repite el paso 5 para cada producto
7. Verifica el total en pantalla
8. Clic en **✅ Registrar venta**

> **Importante:** Al registrar una venta como "Completada" el sistema automáticamente descuenta las cantidades del stock y registra el ingreso en Finanzas. No necesitas hacer nada más.

---

## 5. Historial de ventas {#historial}

Ve a **📋 Historial Ventas**.

Puedes filtrar por:
- **Estado** — Completada, Pendiente de pago, Cancelada
- **Fecha desde / hasta** — para ver un período específico

El campo **Total período** muestra la suma de todas las ventas filtradas.

### Ver el detalle de una venta

En la parte inferior de la pantalla, selecciona cualquier venta del selector y verás el desglose completo: qué productos se vendieron, cantidades, precios y subtotales.

---

## 6. Pedidos a proveedores {#pedidos}

### Crear un pedido nuevo

1. Ve a **🚚 Pedidos → pestaña "Nuevo pedido"**
2. Selecciona o escribe el nombre del **proveedor**
3. Confirma la **fecha del pedido** y la **fecha estimada de llegada**
4. Verás una tabla con **todos tus productos**:
   - La columna **Sugerido** calcula automáticamente cuánto necesitas para llegar al stock mínimo
   - La columna **Pedir** viene precargada con esa sugerencia — puedes modificarla libremente
   - Pon **0** en los productos que no vas a pedir
   - Ajusta el **costo unitario** si el proveedor cambió los precios
5. El total estimado se calcula automáticamente
6. Clic en **✅ Registrar pedido**

> **Tip:** Puedes editar toda la tabla de una sola vez sin ir producto por producto. Solo modifica las cantidades que necesitas y deja el resto en 0.

### Marcar un pedido como recibido

Cuando llegue la mercancía:

1. Ve a **🚚 Pedidos → pestaña "Ver pedidos"**
2. En la sección **"Marcar pedido como recibido"** selecciona el pedido
3. Verifica los productos y cantidades
4. Clic en **✅ Confirmar recepción — actualiza stock**

El sistema sumará automáticamente las cantidades recibidas al stock de cada producto.

---

## 7. Clientes {#clientes}

### Agregar un cliente

1. Ve a **👥 Clientes → pestaña "Agregar cliente"**
2. Completa los datos (solo el nombre es obligatorio):
   - Nombre o razón social
   - RIF o cédula
   - Teléfono
   - Email
   - Dirección
   - Tipo: Persona natural, Empresa o Distribuidor
3. Clic en **💾 Guardar cliente**

### Ver historial de un cliente

En la pestaña **"Ver clientes"** la tabla muestra para cada cliente:
- Cuántas compras ha hecho
- El total acumulado en compras completadas

Esto te permite identificar rápidamente a tus mejores clientes.

---

## 8. Finanzas {#finanzas}

### Ver el balance

Ve a **💰 Finanzas**. Los tres indicadores principales muestran:
- **Ingresos totales** — suma de todo lo que entró
- **Egresos totales** — suma de todo lo que salió
- **Balance neto** — lo que queda

> Las ventas completadas y los pedidos registrados alimentan esto automáticamente. Solo necesitas agregar movimientos manuales para gastos que la app no registra sola (alquiler, transporte, servicios, etc.).

### Registrar un movimiento manual

1. Ve a **💰 Finanzas → pestaña "Registro manual"**
2. Selecciona el **tipo**: Ingreso o Egreso
3. Selecciona la **categoría** (Gasto operativo, Transporte, Otro, etc.)
4. Ingresa el **monto**
5. Confirma la **fecha**
6. Agrega una **descripción** breve
7. Clic en **💾 Registrar**

### Filtrar movimientos

En la pestaña **"Movimientos"** puedes filtrar por tipo (ingresos / egresos) y por categoría para analizar en detalle de dónde viene el dinero y a dónde va.

---

## 9. Exportar datos a Excel {#exportar}

En las siguientes secciones encontrarás un botón **📥 Descargar CSV** o **📥 Exportar CSV**:

- **📦 Inventario** → exporta la lista completa de productos con precios y stock
- **📋 Historial Ventas** → exporta las ventas del período filtrado
- **👥 Clientes** → exporta el directorio de clientes
- **💰 Finanzas** → exporta los movimientos filtrados

El archivo `.csv` se abre directamente en Excel. Para abrirlo correctamente:
1. Abre Excel
2. Ve a **Datos → Desde texto/CSV**
3. Selecciona el archivo descargado
4. Excel detecta las columnas automáticamente
5. Clic en **Cargar**

> También puedes hacer doble clic directo sobre el archivo y Excel lo abre solo, aunque a veces puede no separar las columnas correctamente. El método de importación es más confiable.

---

## 10. Preguntas frecuentes {#faq}

**¿Qué pasa si me equivoco en una venta?**
Por ahora puedes registrar un movimiento manual de egreso en Finanzas para compensar el monto, y ajustar el stock manualmente editando el producto en Inventario. Una función de anular ventas puede agregarse en una versión futura.

**¿Puedo cambiar el precio de un producto sin afectar ventas pasadas?**
Sí. Las ventas ya registradas guardan el precio al momento de la venta. Cambiar el precio del producto en Inventario solo afecta las ventas futuras.

**¿La app funciona en el celular?**
Sí, se puede usar desde el navegador del celular. Para mejor experiencia en móvil usa el celular en **modo horizontal** o amplía el texto desde la configuración del navegador.

**¿Qué pasa si no hay internet?**
La app requiere conexión a internet para funcionar ya que los datos viven en la nube. Sin internet no se puede acceder.

**¿Cada cuánto debo hacer respaldo?**
Los datos están en Supabase que tiene respaldo automático. Adicionalmente te recomendamos exportar los CSV de inventario, ventas y finanzas **una vez al mes** y guardarlos en una carpeta de OneDrive o Google Drive.

**¿Cómo agrego a otra persona para que use la app?**
Solo compártele la URL. Cualquier persona con el enlace puede acceder. Si en el futuro quieres agregar contraseñas por usuario, eso se puede implementar.

**¿El sistema avisa cuando hay stock bajo?**
Sí, en el Dashboard aparece automáticamente la lista de productos con stock igual o menor al mínimo configurado. Para recibir alertas por WhatsApp o correo eso requeriría una integración adicional.

---

*Sistema desarrollado con Streamlit + Supabase · Versión 1.0*
