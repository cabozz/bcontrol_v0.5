# app/__init__.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from .auth_session import require_role

from .routes import clients_router, logs_router, allowed_clients_router, ignored_patterns_router
from .routes.auth_router import router as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="TCP Server Admin API — PostgreSQL modular")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------- DASHBOARD AT "/" ----------
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8" />
    <title>TCP Dashboard</title>
    <style>
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0;
            padding: 0;
            background: #0f172a;
            color: #e5e7eb;
        }
        header {
            background: #020617;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #1f2933;
        }
        header h1 {
            margin: 0;
            font-size: 18px;
        }
        .tag {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 999px;
            background: #1d4ed8;
            color: #e5e7eb;
        }
        main {
            padding: 16px;
        }
        section {
            max-width: 900px;
            margin: 0 auto;
            background: #020617;
            border-radius: 8px;
            padding: 12px 14px;
            border: 1px solid #1f2937;
            box-shadow: 0 10px 30px rgba(0,0,0,0.35);
        }
        h2 {
            margin: 0 0 8px 0;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: .02em;
            text-transform: uppercase;
            color: #9ca3af;
        }
        h3 {
            margin: 0 0 6px 0;
            font-size: 13px;
            font-weight: 500;
            color: #e5e7eb;
        }
        small {
            color: #6b7280;
            font-size: 11px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        th, td {
            padding: 4px 6px;
            border-bottom: 1px solid #111827;
        }
        th {
            text-align: left;
            color: #9ca3af;
            font-weight: 500;
            font-size: 11px;
        }
        tr:nth-child(even) td {
            background: #020617;
        }
        tr:nth-child(odd) td {
            background: #020617;
        }
        .status-pill {
            display: inline-flex;
            align-items: center;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: .04em;
        }
        .status-online {
            background: rgba(16, 185, 129, 0.1);
            color: #6ee7b7;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .status-offline {
            background: rgba(239, 68, 68, 0.1);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .toolbar {
            display: flex;
            gap: 8px;
            align-items: center;
            margin-bottom: 6px;
        }
        .toolbar label {
            font-size: 11px;
            color: #9ca3af;
        }
        select, input, button, textarea {
            border-radius: 4px;
            border: 1px solid #1f2937;
            background: #020617;
            color: #e5e7eb;
            padding: 5px 6px;
            font-size: 12px;
        }
        select:focus, input:focus, textarea:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.5);
        }
        button {
            cursor: pointer;
            background: #2563eb;
            border-color: #1d4ed8;
            font-weight: 500;
        }
        button:hover {
            background: #1d4ed8;
        }
        textarea {
            resize: vertical;
            min-height: 50px;
        }
        .muted {
            color: #6b7280;
            font-size: 11px;
        }
        footer {
            padding: 4px 12px 8px;
            font-size: 11px;
            color: #6b7280;
            border-top: 1px solid #111827;
        }
        #recentMessages {
            margin-top: 6px;
            border-radius: 6px;
            border: 1px solid #111827;
            background: #020617;
            padding: 6px 8px;
            max-height: 200px;
            overflow-y: auto;
            font-family: "JetBrains Mono", Menlo, monospace;
            font-size: 11px;
        }
        .msg-line {
            margin: 1px 0;
        }
        .msg-time {
            color: #64748b;
        }
        .msg-dir-in {
            color: #22c55e;
        }
        .msg-dir-out {
            color: #38bdf8;
        }
        .msg-dir-sys {
            color: #eab308;
        }
        button { padding: 6px 10px;}
    </style>
</head>
<body>

<div id="dashboardApp" style="display:none;">

<header>
    <div>
        <h1>Monitoreo Multimarca BControl 2026 v.5</h1>
        <div class="muted" id="userBadge"></div>
    </div>

    <div style="display:flex; gap:8px; align-items:center;">
        <button id="logoutBtn"
                style="background:#334155;"
                onclick="doLogout()">
            Cerrar sesión
        </button>
    </div>
</header>

<main>
    <section>
        <h2>Paneles</h2>
        <small>Paneles registrados con este usuario</small>

        <div class="toolbar" style="margin-top:8px;">
            <label for="clientSelect">Panel de destino:</label>
            <select id="clientSelect">
                <option value="">-- No hay paneles en línea --</option>
            </select>
            <button type="button" onclick="refreshClients()">Actualizar</button>
        </div>

        <table id="clientsTable">
            <thead>
                <tr>
                    <th>Client</th>
                    <th>Client Alive</th>
                    <th>Last seen</th>

                </tr>
            </thead>
            <tbody>
                <!-- filled by JS -->
            </tbody>
        </table>

        <hr style="border-color:#111827; margin:10px 0;" />

<div id="commandsContainer"
     style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
    <span class="muted">Seleccione un panel para habilitar los comandos.</span>
</div>

<span id="commandStatus" class="muted"></span>

        <div style="margin-top:14px;">
            <h3>Últimos 10 mensajes recibidos</h3>
            <small class="muted">Mas reciente primero</small>
            <div id="recentMessages">
                <!-- messages filled by JS -->
                <span class="muted">Aún no hay mensajes</span>
            </div>
        </div>
    </section>
</main>

<footer>
    Carlos Incendio - BControl Terminal 2025 - Santiago, Chile
</footer>
</div>

<div id="loginOverlay" style="
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(2, 6, 23, 0.92);
    backdrop-filter: blur(6px);
    z-index: 9999;
">
  <div style="
      width: 360px;
      background: #020617;
      border: 1px solid #1f2937;
      border-radius: 12px;
      padding: 18px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.55);
  ">
    <h2 style="margin:0 0 10px 0; font-size:16px; color:#e5e7eb;">Login</h2>
    <div class="muted" style="margin-bottom:12px;">Ingrese usuario y contraseña.</div>

    <input id="loginUser" placeholder="usuario" style="width:100%; margin-bottom:8px;" />
    <input id="loginPass" type="password" placeholder="contraseña" style="width:100%; margin-bottom:10px;" />

    <button id="loginBtn" style="width:100%;">Acceder</button>
    <div id="loginStatus" class="muted" style="margin-top:10px;"></div>
    
  </div>
</div>

<script>
// ---------------- AUTH / SESSION ----------------
let currentUser = null;

function showDashboard() {
    document.getElementById("dashboardApp").style.display = "block";
    document.getElementById("loginOverlay").style.display = "none";
}

function showLogin() {
    document.getElementById("dashboardApp").style.display = "none";
    document.getElementById("loginOverlay").style.display = "flex";
    document.getElementById("userBadge").textContent = "";
}

async function loadMe() {
    try {
        const res = await fetch("/auth/me");
        if (res.ok) {
            currentUser = await res.json();
            showDashboard();
            applyRoleUI();
            return true;
        }
    } catch {}
    currentUser = null;
    showLogin();
    return false;
}

async function doLogin() {
    const username = document.getElementById("loginUser").value.trim();
    const password = document.getElementById("loginPass").value.trim();
    const status = document.getElementById("loginStatus");

    status.textContent = "Accediendo...";

    const res = await fetch("/auth/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
        status.textContent = "Usuario y contraseña incorrectos.";
        return;
    }

    status.textContent = "Conexion Exitosa ✅";

    const ok = await loadMe();
    if (!ok) return;

    refreshClients();
    refreshLogs();
    startAutoRefresh();
}

function applyRoleUI() {
    if (!currentUser) return;

    const badge = document.getElementById("userBadge");
    if (badge) {
        badge.textContent =
            `Sesion iniciada como: ${currentUser.username} (${currentUser.role})`;
    }
}


function formatTime(ts) {
    if (!ts) return "";
    const d = new Date(ts);
    return d.toLocaleString();
}

async function refreshClients() {
    try {
        const res = await fetch("/clients");
        const all = await res.json();

        const online = all.filter(c => c.status === "connected");

        const select = document.getElementById("clientSelect");
        const currentValue = select.value;
        select.innerHTML = "";

        if (!online || online.length === 0) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "-- no online clients --";
            select.appendChild(opt);
        } else {
            const defaultOpt = document.createElement("option");
            defaultOpt.value = "";
            defaultOpt.textContent = "-- Seleccione Panel --";
            select.appendChild(defaultOpt);

            online.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c.client_id;
                opt.textContent = c.description || c.client_id;
                select.appendChild(opt);
            });

            if (currentValue) {
                select.value = currentValue;
            }
        }

        const tbody = document.querySelector("#clientsTable tbody");
        tbody.innerHTML = "";
        all.forEach(c => {
            const tr = document.createElement("tr");

            const tdId = document.createElement("td");
            tdId.textContent = c.description || c.client_id;

            const tdStatus = document.createElement("td");
            const pill = document.createElement("span");
            pill.classList.add("status-pill");
            if (c.status === "connected") {
                pill.classList.add("status-online");
                pill.textContent = "ONLINE";
            } else if (c.status === "disconnected") {
                pill.classList.add("status-offline");
                pill.textContent = "OFFLINE";
            } else {
                pill.textContent = c.status || "UNKNOWN";
            }

            const tdAlive = document.createElement("td");
            const alivePill = document.createElement("span");
            alivePill.classList.add("status-pill");

            if (c.alive_status === "connected") {
                alivePill.classList.add("status-online");
                alivePill.textContent = "CONNECTED";
            } else if (c.alive_status === "pending") {
                alivePill.classList.add("status-offline");
                alivePill.textContent = "PENDING";
            } else {
                // No info yet
                alivePill.textContent = "";
            }

            tdAlive.appendChild(alivePill);

            // Last seen,
            const tdLastSeen = document.createElement("td");
            tdLastSeen.textContent = c.last_seen ? formatTime(c.last_seen) : "";


            tr.appendChild(tdId);
            tr.appendChild(tdAlive);
            tr.appendChild(tdLastSeen);


            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Error refreshing clients:", err);
    }
}

async function refreshLogs() {
    try {
        const res = await fetch("/logs?limit=10");
        const data = await res.json();

        const container = document.getElementById("recentMessages");
        container.innerHTML = "";

        if (!data || data.length === 0) {
            const span = document.createElement("span");
            span.classList.add("muted");
            span.textContent = "No messages yet.";
            container.appendChild(span);
            return;
        }

        data.forEach(log => {
            const line = document.createElement("div");
            line.classList.add("msg-line");

            const t = document.createElement("span");
            t.classList.add("msg-time");
            t.textContent = `[${formatTime(log.timestamp)}] `;

            const d = document.createElement("span");
            if (log.direction === "incoming") {
                d.classList.add("msg-dir-in");
                d.textContent = "DESDE  ";
            } else if (log.direction === "outgoing") {
                d.classList.add("msg-dir-out");
                d.textContent = "OUT ";
            } else {
                d.classList.add("msg-dir-sys");
                d.textContent = "SYS ";
            }

            const c = document.createElement("span");
            c.textContent = `[${log.description || "N/A"}] `;

            const m = document.createElement("span");
            m.textContent = log.message || "";

            line.appendChild(t);
            line.appendChild(d);
            line.appendChild(c);
            line.appendChild(m);

            container.appendChild(line);
        });
    } catch (err) {
        console.error("Error refreshing logs:", err);
    }
}

async function quickSend(payload) {
    const select = document.getElementById("clientSelect");
    const client_id = select.value;
    const statusSpan = document.getElementById("sendStatus");

    if (!client_id) {
        statusSpan.textContent = "Select a client first.";
        return;
    }

    try {
        const res = await fetch("/clients/send", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ client_id, message: payload })
        });

        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            statusSpan.textContent = `Error: ${data.detail || res.status}`;
            return;
        }

        refreshLogs();   // update dashboard history
    } catch (err) {
        console.error("Quick send error:", err);
        statusSpan.textContent = "Error sending quick command.";
    }
}

let refreshTimer = null;
const REFRESH_INTERVAL_MS = 2000;

function startAutoRefresh() {
    if (refreshTimer) return; // already running

    refreshTimer = setInterval(() => {
        refreshClients();
        refreshLogs();
    }, REFRESH_INTERVAL_MS);
}

async function doLogout() {
    try {
        await fetch("/auth/logout", { method: "POST" });
    } catch {}

    currentUser = null;

    // reset UI
    document.getElementById("dashboardApp").style.display = "none";
    document.getElementById("loginOverlay").style.display = "flex";

    // clear fields
    document.getElementById("loginPass").value = "";
    document.getElementById("loginStatus").textContent = "";

    if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null; }

}

window.addEventListener("load", async () => {
    document.getElementById("loginBtn").addEventListener("click", doLogin);

    document.getElementById("loginPass").addEventListener("keydown", (e) => {
        if (e.key === "Enter") doLogin();
    });

    document.getElementById("clientSelect").addEventListener("change", (e) => {
    const client_id = e.target.value;
    if (client_id) {
        loadCommandsForClient(client_id);
    } else {
        document.getElementById("commandsContainer").innerHTML =
            `<span class="muted"> Seleccione un panel para habilitar comandos.</span>`;
    }
    });


    const ok = await loadMe();
    if (!ok) return; // stay on login overlay
    refreshClients();
    refreshLogs();
    startAutoRefresh();

});

async function loadCommandsForClient(client_id) {
    const container = document.getElementById("commandsContainer");
    const status = document.getElementById("commandStatus");

    container.innerHTML = `<span class="muted">Loading commands…</span>`;
    status.textContent = "";

    try {
        const res = await fetch(`/clients/${client_id}/commands`);
        if (!res.ok) {
            container.innerHTML = `<span class="muted">Failed to load commands</span>`;
            return;
        }

        const commands = await res.json();

        container.innerHTML = "";

        if (!commands.length) {
            container.innerHTML = `<span class="muted">No hay comandos disponibles para esta central.</span>`;
            return;
        }

        commands.forEach(cmd => {
            const btn = document.createElement("button");
            btn.textContent = cmd.name;
            btn.title = cmd.description || cmd.name;
            btn.style.minWidth = "90px";

            // Role-based UI (backend still enforces)
            if (cmd.admin_only && currentUser.role !== "admin") {
                btn.disabled = true;
                btn.style.opacity = "0.4";
                btn.style.cursor = "not-allowed";
                btn.title = "Admin only";
            } else {
                btn.onclick = () => sendCommand(client_id, cmd.id, cmd.name);
            }

            container.appendChild(btn);
        });

    } catch (err) {
        console.error("loadCommandsForClient error:", err);
        container.innerHTML = `<span class="muted">Error loading commands</span>`;
    }
}

async function sendCommand(client_id, command_id, command_name) {
    const status = document.getElementById("commandStatus");
    status.textContent = `Sending ${command_name}…`;

    try {
        const res = await fetch("/clients/send-command", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ client_id, command_id })
        });

        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            status.textContent = `Error: ${data.detail || res.status}`;
            return;
        }

        status.textContent = `${command_name} Enviado ✅`;
    } catch (err) {
        console.error("sendCommand error:", err);
        status.textContent = "Hubo un error al enviar el comando.";
    }
}

</script>

</body>
</html>
        """

    # ---------- API ROUTERS ----------
    app.include_router(auth_router)

    # public read-only
    app.include_router(clients_router)
    app.include_router(logs_router)

    # admin-only config
    app.include_router(allowed_clients_router, dependencies=[Depends(require_role("admin"))])
    app.include_router(ignored_patterns_router, dependencies=[Depends(require_role("admin"))])
    app.include_router(auth_router, dependencies=[Depends(require_role("admin"))])

    return app
