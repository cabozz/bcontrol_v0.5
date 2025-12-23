# app/routes/dashboard.py

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

@router.get("/", response_class=HTMLResponse)
async def dashboard():
    # Simple HTML + JS dashboard
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
            display: grid;
            grid-template-columns: 1.1fr 1.2fr;
            gap: 16px;
            padding: 16px;
        }
        section {
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
        #logs-container {
            font-family: "JetBrains Mono", Menlo, monospace;
            font-size: 11px;
            background: #020617;
            border-radius: 6px;
            border: 1px solid #111827;
            padding: 6px;
            height: 360px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .log-line {
            margin: 1px 0;
        }
        .log-time {
            color: #64748b;
        }
        .log-dir-in {
            color: #22c55e;
        }
        .log-dir-out {
            color: #38bdf8;
        }
        .log-dir-sys {
            color: #eab308;
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
    </style>
</head>
<body>
<header>
    <div>
        <h1>TCP Control Dashboard</h1>
        <div class="muted">
            Backend: FastAPI + asyncio TCP + PostgreSQL
        </div>
    </div>
    <span class="tag">LIVE</span>
</header>

<main>
    <!-- Left: clients + send form -->
    <section>
        <h2>Clients</h2>
        <small>Online clients are based on active TCP connections.</small>

        <div class="toolbar" style="margin-top:8px;">
            <label for="clientSelect">Target client:</label>
            <select id="clientSelect">
                <option value="">-- no online clients --</option>
            </select>
            <button type="button" onclick="refreshClients()">Refresh</button>
        </div>

        <table id="clientsTable">
            <thead>
                <tr>
                    <th>Client ID</th>
                    <th>Status</th>
                    <th>Last seen</th>
                    <th>IP</th>
                    <th>Port</th>
                </tr>
            </thead>
            <tbody>
                <!-- filled by JS -->
            </tbody>
        </table>

        <hr style="border-color:#111827; margin:10px 0;" />

        <h2>Send Message</h2>
        <small>Select a client above or type an ID manually.</small>

        <div style="margin-top:6px;">
            <label class="muted">Client ID (override):</label><br />
            <input type="text" id="clientIdInput" placeholder="client_id (optional if selected above)" style="width:100%; margin-bottom:6px;" />
        </div>

        <div>
            <label class="muted">Message:</label><br />
            <textarea id="messageInput" placeholder="Type a message to send to the TCP client..." style="width:100%;"></textarea>
        </div>

        <div style="margin-top:8px; display:flex; gap:8px; align-items:center;">
            <button type="button" onclick="sendMessage()">Send</button>
            <span id="sendStatus" class="muted"></span>
        </div>
    </section>

    <!-- Right: logs -->
    <section>
        <h2>Logs</h2>
        <div class="toolbar">
            <label for="logLimit">Last</label>
            <select id="logLimit" onchange="refreshLogs()">
                <option value="50">50</option>
                <option value="100" selected>100</option>
                <option value="200">200</option>
            </select>
            <span class="muted">messages</span>
            <button type="button" onclick="refreshLogs()">Refresh</button>
        </div>

        <div id="logs-container">
            <!-- log lines here -->
        </div>
    </section>
</main>

<footer>
    Auto-refresh: <span id="autoRefreshStatus">ON (2s)</span> —
    <button type="button" onclick="toggleAutoRefresh()">Toggle</button>
</footer>

<script>
let autoRefresh = true;
let refreshIntervalMs = 2000;
let refreshTimer = null;

// Helper: format timestamp to local time
function formatTime(ts) {
    if (!ts) return "";
    const d = new Date(ts);
    return d.toLocaleString();
}

// Load online clients and full clients list
async function refreshClients() {
    try {
        const [onlineRes, allRes] = await Promise.all([
            fetch("/clients/online"),
            fetch("/clients")
        ]);
        const online = await onlineRes.json();
        const all = await allRes.json();

        // ---- update select ----
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
            defaultOpt.textContent = "-- select client --";
            select.appendChild(defaultOpt);

            online.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c.client_id;
                opt.textContent = c.client_id;
                select.appendChild(opt);
            });

            // keep previous selection if still present
            if (currentValue) {
                select.value = currentValue;
            }
        }

        // ---- update table ----
        const tbody = document.querySelector("#clientsTable tbody");
        tbody.innerHTML = "";
        all.forEach(c => {
            const tr = document.createElement("tr");

            const tdId = document.createElement("td");
            tdId.textContent = c.client_id;

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
            tdStatus.appendChild(pill);

            const tdLastSeen = document.createElement("td");
            tdLastSeen.textContent = c.last_seen ? formatTime(c.last_seen) : "";

            const tdIp = document.createElement("td");
            tdIp.textContent = c.ip || "";

            const tdPort = document.createElement("td");
            tdPort.textContent = c.port != null ? c.port : "";

            tr.appendChild(tdId);
            tr.appendChild(tdStatus);
            tr.appendChild(tdLastSeen);
            tr.appendChild(tdIp);
            tr.appendChild(tdPort);

            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Error refreshing clients:", err);
    }
}

// Load logs from /logs
async function refreshLogs() {
    try {
        const limit = document.getElementById("logLimit").value || 100;
        const res = await fetch(`/logs?limit=${limit}`);
        const data = await res.json();

        const container = document.getElementById("logs-container");
        container.innerHTML = "";

        if (!data || data.length === 0) {
            const empty = document.createElement("div");
            empty.classList.add("muted");
            empty.textContent = "No logs yet.";
            container.appendChild(empty);
            return;
        }

        data.forEach(log => {
            const line = document.createElement("div");
            line.classList.add("log-line");

            const timeSpan = document.createElement("span");
            timeSpan.classList.add("log-time");
            timeSpan.textContent = `[${formatTime(log.timestamp)}] `;

            const dirSpan = document.createElement("span");
            if (log.direction === "incoming") {
                dirSpan.classList.add("log-dir-in");
                dirSpan.textContent = "IN  ";
            } else if (log.direction === "outgoing") {
                dirSpan.classList.add("log-dir-out");
                dirSpan.textContent = "OUT ";
            } else {
                dirSpan.classList.add("log-dir-sys");
                dirSpan.textContent = "SYS ";
            }

            const clientSpan = document.createElement("span");
            clientSpan.textContent = `[${log.client_id || "N/A"}] `;

            const msgSpan = document.createElement("span");
            msgSpan.textContent = log.message || "";

            line.appendChild(timeSpan);
            line.appendChild(dirSpan);
            line.appendChild(clientSpan);
            line.appendChild(msgSpan);

            container.appendChild(line);
        });

        container.scrollTop = container.scrollHeight;
    } catch (err) {
        console.error("Error refreshing logs:", err);
    }
}

// Send message via /clients/send
async function sendMessage() {
    const select = document.getElementById("clientSelect");
    const clientOverride = document.getElementById("clientIdInput").value.trim();
    const message = document.getElementById("messageInput").value.trim();
    const statusSpan = document.getElementById("sendStatus");

    const client_id = clientOverride || select.value;

    if (!client_id) {
        statusSpan.textContent = "Please select or type a client_id.";
        return;
    }
    if (!message) {
        statusSpan.textContent = "Message cannot be empty.";
        return;
    }

    statusSpan.textContent = "Sending...";

    try {
        const res = await fetch("/clients/send", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ client_id, message })
        });

        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            statusSpan.textContent = `Error: ${data.detail || res.status}`;
            return;
        }

        statusSpan.textContent = "Sent ✅";
        document.getElementById("messageInput").value = "";
        // Refresh logs after send
        refreshLogs();
    } catch (err) {
        console.error("Error sending message:", err);
        statusSpan.textContent = "Error sending message (see console).";
    }
}

// Auto-refresh toggle
function toggleAutoRefresh() {
    autoRefresh = !autoRefresh;
    const label = document.getElementById("autoRefreshStatus");
    label.textContent = autoRefresh ? `ON (${refreshIntervalMs/1000}s)` : "OFF";

    if (autoRefresh && !refreshTimer) {
        startAutoRefresh();
    } else if (!autoRefresh && refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(() => {
        if (!autoRefresh) return;
        refreshClients();
        refreshLogs();
    }, refreshIntervalMs);
}

// Initial load
window.addEventListener("load", () => {
    refreshClients();
    refreshLogs();
    startAutoRefresh();
});
</script>
</body>
</html>
    """
