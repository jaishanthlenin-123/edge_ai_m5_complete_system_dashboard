/**
 * M5 Unified Industrial Monitoring Dashboard Application Logic
 * Integrates WebSocket live telemetry, Chart.js multi-channel oscilloscopes,
 * M3 3-LED actuator emulation, assessment station runners, and history views.
 */

// Global State
let ws = null;
let charts = {};
const MAX_CHART_POINTS = 30;
const chartBuffers = {
    labels: [],
    current: [],
    vibration: [],
    audio: [],
    anomaly: []
};

// -----------------------------------------------------------------------------
// 1. Tab Navigation & Page Lifecycle
// -----------------------------------------------------------------------------
function switchTab(tabId) {
    document.querySelectorAll(".nav-item").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.tab === tabId);
    });

    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.toggle("active", pane.id === `pane-${tabId}`);
    });

    const titles = {
        "overview": ["Executive Overview", "Unified industrial telemetry and quality assurance"],
        "vision": ["Vision Inspection Rig", "YOLOv8 PPE detection and 3-LED actuator actuation"],
        "motor": ["Motor Condition Monitoring", "Multivariate signal analysis & anomaly detection"],
        "history-insp": ["Inspection History", "Archived quality decisions and ground-truth validation"],
        "history-motor": ["Motor Telemetry History", "High-frequency sensor telemetry records"],
        "alerts": ["Alerts Center", "Centralized equipment and safety violations"],
        "assessment": ["Assessment Verification Station", "Automated benchmarks for Stations 30, 31, 32, 35"],
        "health": ["System Health & Diagnostics", "Windows hardware adapters and application uptime"]
    };

    if (titles[tabId]) {
        document.getElementById("page-title").innerText = titles[tabId][0];
        document.getElementById("page-subtitle").innerText = titles[tabId][1];
    }

    if (tabId === "history-insp") loadInspectionHistory();
    if (tabId === "history-motor") loadMotorHistory();
    if (tabId === "alerts") loadAlertsHistory();
    if (tabId === "health") loadSystemHealth();
}

document.querySelectorAll(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// Clock
setInterval(() => {
    const now = new Date();
    document.getElementById("clock-display").innerText = now.toUTCString().slice(17, 25) + " UTC";
}, 1000);


// -----------------------------------------------------------------------------
// 2. Chart.js Oscilloscope Initialization
// -----------------------------------------------------------------------------
function initCharts() {
    const commonOpts = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { display: false },
            y: {
                grid: { color: "rgba(255, 255, 255, 0.05)" },
                ticks: { color: "#94a3b8", font: { size: 10 } }
            }
        }
    };

    // Current Chart
    const ctxCurr = document.getElementById("chart-current").getContext("2d");
    charts.current = new Chart(ctxCurr, {
        type: "line",
        data: {
            labels: chartBuffers.labels,
            datasets: [{
                data: chartBuffers.current,
                borderColor: "#38bdf8",
                backgroundColor: "rgba(56, 189, 248, 0.1)",
                borderWidth: 2,
                fill: true,
                tension: 0.2
            }]
        },
        options: {
            ...commonOpts,
            scales: {
                ...commonOpts.scales,
                y: { ...commonOpts.scales.y, min: 0.0, max: 0.35 }
            }
        }
    });

    // Vibration Chart
    const ctxVib = document.getElementById("chart-vibration").getContext("2d");
    charts.vibration = new Chart(ctxVib, {
        type: "line",
        data: {
            labels: chartBuffers.labels,
            datasets: [{
                data: chartBuffers.vibration,
                borderColor: "#a855f7",
                backgroundColor: "rgba(168, 85, 247, 0.1)",
                borderWidth: 2,
                fill: true,
                tension: 0.2
            }]
        },
        options: commonOpts
    });

    // Audio Chart
    const ctxAud = document.getElementById("chart-audio").getContext("2d");
    charts.audio = new Chart(ctxAud, {
        type: "line",
        data: {
            labels: chartBuffers.labels,
            datasets: [{
                data: chartBuffers.audio,
                borderColor: "#eab308",
                backgroundColor: "rgba(234, 179, 8, 0.1)",
                borderWidth: 2,
                fill: true,
                tension: 0.2
            }]
        },
        options: commonOpts
    });

    // Anomaly Score Chart
    const ctxAnom = document.getElementById("chart-anomaly").getContext("2d");
    charts.anomaly = new Chart(ctxAnom, {
        type: "line",
        data: {
            labels: chartBuffers.labels,
            datasets: [{
                data: chartBuffers.anomaly,
                borderColor: "#22c55e",
                backgroundColor: "rgba(34, 197, 94, 0.1)",
                borderWidth: 2,
                fill: true,
                tension: 0.2
            }]
        },
        options: {
            ...commonOpts,
            scales: {
                ...commonOpts.scales,
                y: { ...commonOpts.scales.y, min: 0.0, max: 1.0 }
            }
        }
    });
}

function pushChartData(timeStr, curr, vib, aud, anom) {
    if (chartBuffers.labels.length >= MAX_CHART_POINTS) {
        chartBuffers.labels.shift();
        chartBuffers.current.shift();
        chartBuffers.vibration.shift();
        chartBuffers.audio.shift();
        chartBuffers.anomaly.shift();
    }

    chartBuffers.labels.push(timeStr);
    chartBuffers.current.push(curr);
    chartBuffers.vibration.push(vib);
    chartBuffers.audio.push(aud);
    chartBuffers.anomaly.push(anom);

    // Update charts efficiently
    if (charts.current) charts.current.update("none");
    if (charts.vibration) charts.vibration.update("none");
    if (charts.audio) charts.audio.update("none");
    if (charts.anomaly) {
        // Change color to red if anomaly score > 0.65
        const lastScore = anom;
        charts.anomaly.data.datasets[0].borderColor = lastScore >= 0.65 ? "#ef4444" : "#22c55e";
        charts.anomaly.update("none");
    }
}


// -----------------------------------------------------------------------------
// 3. WebSocket Real-Time Telemetry Stream
// -----------------------------------------------------------------------------
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/ws/telemetry`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        document.getElementById("global-pulse").className = "pulse-dot green";
        document.getElementById("global-status-text").innerText = "SYSTEM OPERATIONAL";
        console.log("[WebSocket] Telemetry stream connected.");
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleIncomingEvent(data);
        } catch (e) {
            console.error("[WebSocket] Parse error:", e);
        }
    };

    ws.onclose = () => {
        document.getElementById("global-pulse").className = "pulse-dot red";
        document.getElementById("global-status-text").innerText = "RECONNECTING...";
        setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = (err) => {
        console.error("[WebSocket] Socket error:", err);
        ws.close();
    };
}

function handleIncomingEvent(evt) {
    // 1. Initial State Snapshot
    if (evt.type === "INITIAL_STATE") {
        if (evt.vision) updateVisionUI(evt.vision);
        if (evt.motor) updateMotorUI(evt.motor);
        if (evt.kpis) updateKPIs(evt.kpis);
        if (evt.alerts) updateOverviewAlerts(evt.alerts);
        return;
    }

    const mod = evt.module;
    const type = evt.event_type;
    const payload = evt.data || {};

    // 2. Vision Inspection Result
    if (mod === "vision" && type === "inspection_result") {
        updateVisionUI(payload);
    }

    // 3. Motor Telemetry
    if (mod === "motor" && type === "motor_telemetry") {
        updateMotorUI(payload);
    }

    // 4. Alerts
    if (evt.severity === "CRITICAL" || evt.severity === "WARNING" || (type && type.includes("alert"))) {
        appendAlertItem(evt);
        // Refresh KPIs when new alerts arrive
        fetchKPIs();
    }
}


// -----------------------------------------------------------------------------
// 4. UI Update Handlers
// -----------------------------------------------------------------------------
function updateVisionUI(v) {
    if (!v) return;

    // Overview cards
    document.getElementById("ov-sample-id").innerText = v.sample_id || "--";
    document.getElementById("ov-source-mode").innerText = (v.source_mode || "").toUpperCase();
    document.getElementById("ov-helmet").innerText = v.helmet_detected ? `DETECTED (${Math.round(v.helmet_confidence * 100)}%)` : "NOT FOUND";
    document.getElementById("ov-gloves").innerText = v.gloves_detected ? `DETECTED (${Math.round(v.gloves_confidence * 100)}%)` : "NOT FOUND";
    document.getElementById("ov-reason").innerText = v.inspection_reason || "--";

    const st = v.inspection_status || "IDLE";
    const ovBadge = document.getElementById("overview-insp-status");
    ovBadge.innerText = st;
    ovBadge.className = `badge ${st === "PASS" ? "green" : (st === "FAIL" ? "red" : "blue")}`;

    // Vision tab detail
    const banner = document.getElementById("insp-status-banner");
    banner.innerText = st;
    banner.className = `status-banner ${st.toLowerCase()}`;

    document.getElementById("insp-reason-detail").innerText = v.inspection_reason || "--";
    document.getElementById("insp-conf-helmet").innerText = `${Math.round((v.helmet_confidence || 0) * 100)}%`;
    document.getElementById("insp-conf-gloves").innerText = `${Math.round((v.gloves_confidence || 0) * 100)}%`;
    document.getElementById("insp-lat").innerText = `${v.processing_ms || 0} ms`;

    // Update 3-LED Actuator Stack Visuals
    const led = v.led_state || {};
    const gLamp = document.getElementById("led-lamp-green");
    const yLamp = document.getElementById("led-lamp-yellow");
    const rLamp = document.getElementById("led-lamp-red");

    const isRedBlink = led.red?.blinking;
    const isRedActive = led.red?.active || isRedBlink;
    const isGreenActive = led.green?.active && !isRedBlink;
    const isYellowActive = led.yellow?.active && !isRedBlink;

    gLamp.className = `led-lamp green ${isGreenActive ? "active" : ""}`;
    yLamp.className = `led-lamp yellow ${isYellowActive ? "active" : ""}`;
    rLamp.className = `led-lamp red ${isRedBlink ? "blinking" : (isRedActive ? "active" : "")}`;

    document.getElementById("actuator-label").innerText = led.active_label || "ALL LEDS OFF";
}

function updateMotorUI(m) {
    if (!m) return;

    // Overview cards
    document.getElementById("ov-current").innerText = `${(m.current || 0).toFixed(3)} A`;
    document.getElementById("ov-voltage").innerText = `${(m.voltage || 0).toFixed(2)} V`;
    document.getElementById("ov-accel").innerText = `${m.accel_x || 0} ADC`;
    document.getElementById("ov-sound").innerText = `${m.sound_p2p || 0}`;

    const score = m.anomaly_score || 0.0;
    const isAnom = m.is_anomaly;

    const fill = document.getElementById("ov-anom-fill");
    fill.style.width = `${Math.min(100, Math.round(score * 100))}%`;

    const scoreTxt = document.getElementById("ov-anom-score-text");
    scoreTxt.innerText = `${score.toFixed(2)} / 1.00 (${isAnom ? "CRITICAL ANOMALY" : "Normal Operation"})`;

    const mBadge = document.getElementById("overview-motor-status");
    mBadge.innerText = isAnom ? "ANOMALY" : "NORMAL";
    mBadge.className = `badge ${isAnom ? "red" : "green"}`;

    // Motor Tab Badges
    document.getElementById("chart-curr-badge").innerText = `${(m.current || 0).toFixed(3)} A`;
    document.getElementById("chart-vib-badge").innerText = `${m.accel_x || 0}`;
    document.getElementById("chart-audio-badge").innerText = `${m.sound_p2p || 0}`;

    const anomBadge = document.getElementById("chart-anom-badge");
    anomBadge.innerText = score.toFixed(2);
    anomBadge.className = `badge ${isAnom ? "red" : "green"}`;

    // Push into Oscilloscope Charts
    const timeLabel = new Date().toTimeString().slice(0, 8);
    pushChartData(timeLabel, m.current || 0.0, m.accel_x || 0.0, m.sound_p2p || 0.0, score);
}

function updateKPIs(kpis) {
    if (!kpis) return;
    if (kpis.kpi1) {
        document.getElementById("kpi-acc-val").innerText = kpis.kpi1.display;
        document.getElementById("kpi-acc-detail").innerText = kpis.kpi1.detail;
    }
    if (kpis.kpi2) {
        document.getElementById("kpi-pass-val").innerText = kpis.kpi2.display;
        document.getElementById("kpi-pass-detail").innerText = kpis.kpi2.detail;
    }
    if (kpis.kpi3) {
        document.getElementById("kpi-anom-val").innerText = kpis.kpi3.display;
        document.getElementById("kpi-anom-detail").innerText = kpis.kpi3.detail;
    }
}

function fetchKPIs() {
    fetch("/api/kpis")
        .then(res => res.json())
        .then(data => updateKPIs(data))
        .catch(err => console.error("Error fetching KPIs:", err));
}

function updateOverviewAlerts(alertsList) {
    const tbody = document.querySelector("#table-overview-alerts tbody");
    if (!tbody) return;

    if (!alertsList || alertsList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-cell">No active alerts recorded.</td></tr>`;
        return;
    }

    tbody.innerHTML = alertsList.map(a => `
        <tr>
            <td>${(a.timestamp || "").slice(11, 19)}</td>
            <td><span class="badge blue">${(a.module || "").toUpperCase()}</span></td>
            <td><span class="badge ${a.severity === 'CRITICAL' ? 'red' : 'yellow'}">${a.severity}</span></td>
            <td><b>${a.title}</b></td>
            <td>${a.description}</td>
        </tr>
    `).join("");

    document.getElementById("sidebar-alert-badge").innerText = alertsList.length;
}

function appendAlertItem(evt) {
    const countEl = document.getElementById("sidebar-alert-badge");
    let c = parseInt(countEl.innerText) || 0;
    countEl.innerText = c + 1;
}


// -----------------------------------------------------------------------------
// 5. Data Tables (History & Alerts)
// -----------------------------------------------------------------------------
function loadInspectionHistory() {
    fetch("/api/history/inspections?limit=50")
        .then(r => r.json())
        .then(d => {
            const tbody = document.querySelector("#table-history-insp tbody");
            const list = d.inspections || [];
            if (list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="10" class="empty-cell">No inspections recorded.</td></tr>`;
                return;
            }
            tbody.innerHTML = list.map(r => `
                <tr>
                    <td>${r.id}</td>
                    <td><b>${r.sample_id}</b></td>
                    <td>${(r.timestamp || "").slice(11, 19)}</td>
                    <td>${r.source_mode}</td>
                    <td>${r.helmet_detected ? '✅' : '❌'} (${Math.round(r.helmet_confidence*100)}%)</td>
                    <td>${r.gloves_detected ? '✅' : '❌'} (${Math.round(r.gloves_confidence*100)}%)</td>
                    <td><span class="badge ${r.inspection_status === 'PASS' ? 'green' : 'red'}">${r.inspection_status}</span></td>
                    <td>${r.ground_truth_label || '--'}</td>
                    <td>${r.is_correct === 1 ? '✅ Yes' : (r.is_correct === 0 ? '❌ No' : '--')}</td>
                    <td>${r.processing_ms} ms</td>
                </tr>
            `).join("");
        });
}

function loadMotorHistory() {
    fetch("/api/history/motor?limit=50")
        .then(r => r.json())
        .then(d => {
            const tbody = document.querySelector("#table-history-motor tbody");
            const list = d.telemetry || [];
            if (list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="10" class="empty-cell">No telemetry recorded.</td></tr>`;
                return;
            }
            tbody.innerHTML = list.map(r => `
                <tr>
                    <td>${r.id}</td>
                    <td>${(r.timestamp || "").slice(11, 19)}</td>
                    <td>${r.sequence}</td>
                    <td>${r.servo_angle}°</td>
                    <td>${r.voltage.toFixed(2)}</td>
                    <td>${r.current.toFixed(3)}</td>
                    <td>${r.accel_x}, ${r.accel_y}, ${r.accel_z}</td>
                    <td>${r.sound_p2p}</td>
                    <td><span class="badge ${r.is_anomaly ? 'red' : 'green'}">${r.anomaly_status}</span></td>
                    <td>${r.anomaly_score.toFixed(2)}</td>
                </tr>
            `).join("");
        });
}

function loadAlertsHistory() {
    fetch("/api/history/alerts?limit=50")
        .then(r => r.json())
        .then(d => {
            const tbody = document.querySelector("#table-full-alerts tbody");
            const list = d.alerts || [];
            if (list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="empty-cell">No alerts logged.</td></tr>`;
                return;
            }
            tbody.innerHTML = list.map(a => `
                <tr>
                    <td>${a.id}</td>
                    <td>${(a.timestamp || "").slice(11, 19)}</td>
                    <td><span class="badge blue">${a.module.toUpperCase()}</span></td>
                    <td><span class="badge ${a.severity === 'CRITICAL' ? 'red' : 'yellow'}">${a.severity}</span></td>
                    <td><b>${a.title}</b></td>
                    <td>${a.description}</td>
                    <td>
                        ${a.acknowledged ? '<span class="subtext">Acknowledged</span>' : `<button class="btn btn-secondary" onclick="ackAlert(${a.id})">Acknowledge</button>`}
                    </td>
                </tr>
            `).join("");
        });
}

function ackAlert(id) {
    fetch(`/api/alerts/acknowledge/${id}`, { method: "POST" })
        .then(() => loadAlertsHistory());
}

function loadSystemHealth() {
    fetch("/api/health")
        .then(r => r.json())
        .then(d => {
            const h = d.health || {};
            document.getElementById("health-uptime").innerText = `${h.uptime_seconds || 0}s`;
            if (h.vision_adapter) document.getElementById("health-vision-mode").innerText = `${h.vision_adapter.source_mode} (Online: ${h.vision_adapter.camera_online})`;
            if (h.motor_adapter) document.getElementById("health-motor-mode").innerText = `${h.motor_adapter.source_mode} (${h.motor_adapter.total_records} buffered)`;

            const logsDiv = document.getElementById("terminal-logs");
            if (d.logs && d.logs.length > 0) {
                logsDiv.innerHTML = d.logs.map(l => `<div>[${(l.timestamp || '').slice(11,19)}] [${l.level}] ${l.message}</div>`).join("");
            }
        });
}


// -----------------------------------------------------------------------------
// 6. Action Controls: Replay, Faults, Uploads, Assessments
// -----------------------------------------------------------------------------
// Replay controls
document.getElementById("btn-replay-play").addEventListener("click", () => {
    fetch("/api/motor/replay/control", { method: "POST", body: new URLSearchParams({ action: "play" }) });
});
document.getElementById("btn-replay-pause").addEventListener("click", () => {
    fetch("/api/motor/replay/control", { method: "POST", body: new URLSearchParams({ action: "pause" }) });
});
document.getElementById("btn-replay-reset").addEventListener("click", () => {
    fetch("/api/motor/replay/control", { method: "POST", body: new URLSearchParams({ action: "reset" }) });
});

document.querySelectorAll(".speed-group .btn-pill").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".speed-group .btn-pill").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        fetch("/api/motor/replay/control", { method: "POST", body: new URLSearchParams({ action: "speed", value: btn.dataset.speed }) });
    });
});

// Fault Injection
document.getElementById("fault-select").addEventListener("change", (e) => {
    fetch("/api/motor/fault_injection", { method: "POST", body: new URLSearchParams({ fault_type: e.target.value }) });
});

// Vision Mode Switcher
document.getElementById("vision-mode-select").addEventListener("change", (e) => {
    fetch("/api/vision/mode", { method: "POST", body: new URLSearchParams({ mode: e.target.value }) });
});

// Image Upload Single-Shot Inspection
document.getElementById("btn-inspect-upload").addEventListener("click", () => {
    const fileInput = document.getElementById("file-upload-input");
    if (!fileInput.files.length) {
        alert("Please select an image file first.");
        return;
    }
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    fetch("/api/vision/inspect", { method: "POST", body: formData })
        .then(r => r.json())
        .then(res => {
            updateVisionUI(res);
            fetchKPIs();
        })
        .catch(err => alert("Inspection failed: " + err));
});

// Station 31: 20-Sample Pass/Fail Station
document.getElementById("btn-run-st31").addEventListener("click", () => {
    const btn = document.getElementById("btn-run-st31");
    btn.innerText = "Running 20 Tests...";
    btn.disabled = true;

    fetch("/api/assessment/pass_fail_20?execute=true")
        .then(r => r.json())
        .then(res => {
            btn.innerText = "Run 20-Sample Test";
            btn.disabled = false;
            document.getElementById("st31-tp").innerText = res.tp;
            document.getElementById("st31-fp").innerText = res.fp;
            document.getElementById("st31-fn").innerText = res.fn;
            document.getElementById("st31-tn").innerText = res.tn;
            document.getElementById("st31-acc").innerText = `${res.accuracy}%`;
            document.getElementById("st31-fpr").innerText = `${res.false_pass_rate}%`;
            fetchKPIs();
            alert(`Station 31 Completed!\nAccuracy: ${res.accuracy}%\nPass Rate: ${res.pass_rate}%\nFalse-Pass Rate: ${res.false_pass_rate}%`);
        })
        .catch(err => {
            btn.innerText = "Run 20-Sample Test";
            btn.disabled = false;
            alert("Test execution error: " + err);
        });
});

// Station 35: 50-Sample Headline Metric
document.getElementById("btn-run-st35").addEventListener("click", () => {
    const btn = document.getElementById("btn-run-st35");
    btn.innerText = "Benchmarking 50 Samples...";
    btn.disabled = true;

    fetch("/api/assessment/headline_50?execute=true")
        .then(r => r.json())
        .then(res => {
            btn.innerText = "Run 50-Sample Benchmark";
            btn.disabled = false;
            document.getElementById("st35-score").innerText = `${res.correct_results} / ${res.total_samples}`;
            fetchKPIs();
            alert(`Station 35 Headline Metric:\n${res.correct_results} / ${res.total_samples} Correct (${res.accuracy_pct}% Accuracy)`);
        })
        .catch(err => {
            btn.innerText = "Run 50-Sample Benchmark";
            btn.disabled = false;
            alert("Benchmark execution error: " + err);
        });
});

// Station 32: 10-Minute Full Chain Test
let chainPoller = null;
document.getElementById("btn-start-chain").addEventListener("click", () => {
    const btn = document.getElementById("btn-start-chain");
    btn.disabled = true;
    btn.innerText = "Test in Progress...";

    fetch("/api/assessment/chain_start", { method: "POST", body: new URLSearchParams({ duration: "600" }) })
        .then(r => r.json())
        .then(st => {
            if (chainPoller) clearInterval(chainPoller);
            chainPoller = setInterval(pollChainStatus, 2000);
        });
});

function pollChainStatus() {
    fetch("/api/assessment/chain_status")
        .then(r => r.json())
        .then(st => {
            document.getElementById("chain-status-label").innerText = st.status;
            document.getElementById("chain-elapsed").innerText = Math.round(st.elapsed_seconds);
            document.getElementById("chain-v-count").innerText = st.vision_inferences_processed;
            document.getElementById("chain-m-count").innerText = st.motor_records_processed;
            document.getElementById("chain-progress-fill").style.width = `${st.progress_pct}%`;

            if (st.status === "COMPLETED" || !st.is_running) {
                clearInterval(chainPoller);
                const btn = document.getElementById("btn-start-chain");
                btn.disabled = false;
                btn.innerText = "Start 10-Minute Run";
            }
        });
}


// -----------------------------------------------------------------------------
// 7. Initial Bootstrap
// -----------------------------------------------------------------------------
window.addEventListener("DOMContentLoaded", () => {
    initCharts();
    connectWebSocket();
    fetchKPIs();
    // Preload assessment current numbers
    fetch("/api/assessment/pass_fail_20")
        .then(r => r.json())
        .then(res => {
            if (res.total_samples > 0) {
                document.getElementById("st31-tp").innerText = res.true_positive;
                document.getElementById("st31-fp").innerText = res.false_positive;
                document.getElementById("st31-fn").innerText = res.false_negative;
                document.getElementById("st31-tn").innerText = res.true_negative;
                document.getElementById("st31-acc").innerText = `${res.accuracy_pct}%`;
                document.getElementById("st31-fpr").innerText = `${res.false_pass_rate_pct}%`;
            }
        });
});

