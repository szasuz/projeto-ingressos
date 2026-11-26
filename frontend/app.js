const API_URL = window.location.origin.startsWith("http")
  ? "/reservas"
  : "http://127.0.0.1:8000/reservas";

const state = {
  evento: "Festival Eletrônico 2026",
  setor: "Padrão",
  preco: 180,
  quantidade: 2,
};

function mostrarToast(reservaId, modo = "ok") {
  const container = document.getElementById("toast-container");
  const isDlq = modo === "dlq";

  const toast = document.createElement("div");
  toast.className = `pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl border backdrop-blur-md shadow-2xl transition-all duration-300 translate-x-4 opacity-0 ${
    isDlq
      ? "bg-rose-950/90 border-rose-500/40 text-rose-100"
      : "bg-slate-900/95 border-emerald-500/40 text-slate-100"
  }`;

  toast.innerHTML = `
    <span class="text-base">${isDlq ? "⚠️" : "✅"}</span>
    <div class="text-xs">
      <p class="font-semibold">${isDlq ? "Reserva enviada com falha simulada" : "Ingresso reservado!"}</p>
    </div>
  `;

  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.remove("translate-x-4", "opacity-0"));

  setTimeout(() => {
    toast.classList.add("translate-x-4", "opacity-0");
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

const qtyDisplay = document.getElementById("qty-display");
const totalDisplay = document.getElementById("total-display");
const resumoTexto = document.getElementById("resumo-texto");
const logsEl = document.getElementById("logs");

const SPINNER_SVG = `
  <svg class="animate-spin h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
`;

function setLoading(buttonEl, isLoading, loadingText) {
  if (isLoading) {
    buttonEl.dataset.originalHtml = buttonEl.innerHTML;
    buttonEl.disabled = true;
    buttonEl.innerHTML = `${SPINNER_SVG}<span>${loadingText}</span>`;
  } else {
    buttonEl.disabled = false;
    if (buttonEl.dataset.originalHtml) {
      buttonEl.innerHTML = buttonEl.dataset.originalHtml;
    }
  }
}

function atualizarTotal() {
  qtyDisplay.textContent = state.quantidade;
  const total = state.preco * state.quantidade;
  const precoFmt = state.preco.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  resumoTexto.textContent = `${state.quantidade}x Ingresso ${state.setor} (${precoFmt} cada)`;
  totalDisplay.textContent = total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

document.querySelectorAll(".setor-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".setor-btn").forEach((b) => {
      b.classList.remove("bg-indigo-600", "text-white");
      b.classList.add("text-slate-400");
    });
    btn.classList.remove("text-slate-400");
    btn.classList.add("bg-indigo-600", "text-white");
    state.setor = btn.dataset.setor;
    state.preco = Number(btn.dataset.preco);
    atualizarTotal();
  });
});

document.getElementById("qty-minus").addEventListener("click", () => {
  if (state.quantidade > 1) { state.quantidade--; atualizarTotal(); }
});
document.getElementById("qty-plus").addEventListener("click", () => {
  if (state.quantidade < 10) { state.quantidade++; atualizarTotal(); }
});

function montarPayload(sobrescrever = {}) {
  return {
    cliente: document.getElementById("cliente").value,
    documento: document.getElementById("documento").value,
    email: document.getElementById("email").value,
    evento: state.evento,
    setor: state.setor,
    quantidade: state.quantidade,
    pagamento: document.getElementById("pagamento").value,
    valor_total: state.preco * state.quantidade,
    simular_erro: false,
    ...sobrescrever,
  };
}

function adicionarLog(texto, tempoMs, tipo = "ok") {
  const empty = document.getElementById("empty-state");
  if (empty) empty.remove();

  const estilos = {
    ok: "border-emerald-500/25 bg-emerald-500/10 text-emerald-300",
    dlq: "border-rose-500/30 bg-rose-500/10 text-rose-300",
    erro: "border-red-500/30 bg-red-500/10 text-red-300",
  };

  const item = document.createElement("div");
  item.className = `px-3 py-2 rounded-lg border font-mono text-[11px] flex items-center justify-between gap-2 ${estilos[tipo]}`;
  item.innerHTML = `<span class="truncate">${texto}</span><span class="opacity-70 shrink-0">${tempoMs}ms</span>`;
  logsEl.prepend(item);
}

async function enviarReserva(payload, modo = "ok") {
  const inicio = performance.now();
  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    const tempoMs = Math.round(performance.now() - inicio);

    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

    const logTipo = modo === "dlq" ? "dlq" : "ok";
    const tag = modo === "dlq" ? "DLQ" : "202 OK";
    adicionarLog(`${data.reserva_id} • reserva.criada • ${tag}`, tempoMs, logTipo);

    if (modo !== "rajada") {
      mostrarToast(data.reserva_id, modo);
    }
  } catch (err) {
    const tempoMs = Math.round(performance.now() - inicio);
    adicionarLog(`ERRO • ${err.message}`, tempoMs, "erro");
  }
}

const btnSubmit = document.getElementById("btn-submit");
document.getElementById("form-reserva").addEventListener("submit", async (e) => {
  e.preventDefault();
  setLoading(btnSubmit, true, "Reservando ingresso...");
  try {
    await enviarReserva(montarPayload(), "ok");
  } finally {
    setLoading(btnSubmit, false);
  }
});

const btnDlq = document.getElementById("btn-dlq");
btnDlq.addEventListener("click", async () => {
  setLoading(btnDlq, true, "Simulando Falha...");
  try {
    await enviarReserva(montarPayload({ valor_total: 9999.0, simular_erro: true }), "dlq");
  } finally {
    setLoading(btnDlq, false);
  }
});

const btnRajada = document.getElementById("btn-rajada");
btnRajada.addEventListener("click", async () => {
  setLoading(btnRajada, true, "Disparando 10x...");
  try {
    const disparos = [];
    for (let i = 1; i <= 10; i++) {
      disparos.push(enviarReserva(montarPayload({ cliente: `Cliente Rajada #${i}` }), "rajada"));
    }
    await Promise.all(disparos);
    mostrarToast("10 reservas enviadas em rajada", "ok");
  } finally {
    setLoading(btnRajada, false);
  }
});

document.getElementById("btn-limpar").addEventListener("click", () => {
  logsEl.innerHTML = `
    <div id="empty-state" class="h-full flex flex-col items-center justify-center text-center px-4">
      <p class="text-xs text-slate-400">Nenhum evento publicado ainda.</p>
      <p class="text-[11px] text-slate-500 mt-1">Os retornos imediatos (HTTP 202) aparecerão aqui.</p>
    </div>
  `;
});

atualizarTotal();