const socket = io(window.location.origin, {
  transports: ["websocket", "polling"]
});

let pedido = [];
let total = 0;

function agregarPedido(nombre, precio) {
  const existente = pedido.find(item => item.nombre === nombre);
  if (existente) {
    existente.cantidad++;
  } else {
    pedido.push({ nombre, precio, cantidad: 1 });
  }
  total += precio;
  actualizarPedido();
}

function eliminarItem(index) {
  const item = pedido[index];
  total -= item.precio * item.cantidad;
  pedido.splice(index, 1);
  actualizarPedido();
}

function vaciarPedido() {
  pedido = [];
  total = 0;
  actualizarPedido();
}

function actualizarPedido() {
  const lista = document.getElementById("lista-pedido");
  const totalDiv = document.getElementById("total");
  lista.innerHTML = "";

  pedido.forEach((item, index) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <span>${item.nombre} x${item.cantidad}</span>
      <span>$${(item.precio * item.cantidad).toLocaleString()}</span>
      <button onclick="eliminarItem(${index})">✕</button>
    `;
    lista.appendChild(li);
  });

  totalDiv.textContent = `Total: $${total.toLocaleString()}`;
}

function enviarPedido() {
  const mesa = document.getElementById("mesa").value.trim();

  if (!mesa) {
    alert("⚠️ Ingresa el número de mesa.");
    return;
  }

  if (pedido.length === 0) {
    alert("⚠️ No hay productos en el pedido.");
    return;
  }

  const detalles = pedido.map(item => `${item.nombre} x${item.cantidad}`).join(", ");

  fetch('/crear_pedido', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mesa, detalles, total })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === "ok") {
      alert(`✅ Pedido enviado a cocina (${mesa})`);
      vaciarPedido();
    }
  })
  .catch(err => console.error("Error al enviar pedido:", err));
}
