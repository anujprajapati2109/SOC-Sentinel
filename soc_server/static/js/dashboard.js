const dashboardState = {
    data: null,
    timelineRange: "last_hour",
    chart: null,
};

const refreshIntervalMs = window.socSentinelConfig?.refreshIntervalMs || 5000;

document.addEventListener("DOMContentLoaded", () => {
    initializeGlobalSearch();
    initializeTables();
    initializeClickableRows();
    initializeTelemetryOffcanvas();
    initializeFilterForms();
    initializeConfirmations();
    initializeLiveSectionPolling();
    initializeCloudStatusToggle();

    if (document.querySelector("[data-dashboard-value]")) {
        initializeTimelineControls();
        refreshDashboard();
        window.setInterval(refreshDashboard, refreshIntervalMs);
    }
});

function initializeCloudStatusToggle() {
    const section = document.getElementById("cloudStatusSection");
    const button = document.getElementById("cloudStatusToggle");
    const details = document.getElementById("cloud-status-grid");

    if (!section || !button || !details) {
        return;
    }

    button.addEventListener("click", () => {
        const isExpanded = button.getAttribute("aria-expanded") === "true";
        const nextExpanded = !isExpanded;

        button.setAttribute("aria-expanded", String(nextExpanded));
        details.hidden = !nextExpanded;
        section.classList.toggle("is-expanded", nextExpanded);
        section.classList.toggle("is-collapsed", !nextExpanded);
    });
}

async function refreshDashboard() {
    try {
        const response = await fetch("/api/v1/dashboard", {
            headers: { Accept: "application/json" },
        });
        if (!response.ok) {
            throw new Error(`Dashboard API returned ${response.status}`);
        }

        dashboardState.data = await response.json();
        renderDashboard(dashboardState.data);
    } catch (error) {
        const updated = document.getElementById("dashboard-updated");
        if (updated) {
            updated.textContent = "Dashboard data unavailable";
        }
        console.error(error);
    }
}

function renderDashboard(data) {
    updateScalarValues(data);
    renderEndpointHealth(data.endpoint_health || []);
    renderMitre(data.mitre || []);
    renderRuleTables(data);
    renderTopEndpoints(data.top_endpoints || []);
    renderSystemHealth(data.system_health || {});
    renderCloudStatus(data.cloud_status || {});
    renderTimeline(data.attack_timeline || {});
    updateGeneratedAt(data.generated_at);
}

function updateScalarValues(data) {
    document.querySelectorAll("[data-dashboard-value]").forEach((element) => {
        const path = element.dataset.dashboardValue;
        const value = getPath(data, path);
        element.textContent = formatValue(value);
    });
}

function renderEndpointHealth(rows) {
    const body = document.getElementById("endpoint-health-body");
    if (!body) {
        return;
    }

    if (!rows.length) {
        body.innerHTML = emptyRow(6, "bi-pc-display", "No endpoint data");
        return;
    }

    body.innerHTML = rows.map((row) => `
        <tr class="clickable-row" data-href="/endpoints/${encodeURIComponent(row.endpoint_id)}">
            <td><a class="table-link" href="/endpoints/${encodeURIComponent(row.endpoint_id)}">${escapeHtml(row.hostname || row.endpoint_id || "Unknown")}</a></td>
            <td>${statusBadge(row.status)}</td>
            <td>${formatPercent(row.cpu)}</td>
            <td>${formatPercent(row.ram)}</td>
            <td>${formatValue(row.telemetry_count)}</td>
            <td>${formatDate(row.last_heartbeat)}</td>
        </tr>
    `).join("");
}

function renderMitre(rows) {
    const target = document.getElementById("mitre-list");
    if (!target) {
        return;
    }

    const maxCount = Math.max(...rows.map((row) => row.count), 1);
    target.innerHTML = rows.map((row) => {
        const width = Math.round((row.count / maxCount) * 100);
        return `
            <div class="mitre-row">
                <div class="mitre-meta">
                    <a class="table-link" href="/incidents?mitre=${encodeURIComponent(row.tactic)}">${escapeHtml(row.tactic)}</a>
                    <strong>${formatValue(row.count)}</strong>
                </div>
                <div class="mitre-bar"><span style="width: ${width}%"></span></div>
            </div>
        `;
    }).join("");
}

function renderRuleTables(data) {
    renderDetectionRules(data.detection_rules || []);
    renderCorrelationRules(data.correlation_rules || []);
}

function renderDetectionRules(rows) {
    const body = document.getElementById("detection-rules-body");
    if (!body) {
        return;
    }

    if (!rows.length) {
        body.innerHTML = emptyRow(4, "bi-bullseye", "No detection rules");
        return;
    }

    body.innerHTML = rows.map((row) => `
        <tr>
            <td>
                <a class="table-title table-link" href="/alerts?rule=${encodeURIComponent(row.rule_id)}">${escapeHtml(row.name)}</a>
                <span class="table-subtitle">${escapeHtml(row.rule_id)}</span>
            </td>
            <td>${formatValue(row.triggered)}</td>
            <td>${formatValue(row.suppressed)}</td>
            <td>${formatValue(row.average_evaluation_time_ms)} ms</td>
        </tr>
    `).join("");
}

function renderCorrelationRules(rows) {
    const body = document.getElementById("correlation-rules-body");
    if (!body) {
        return;
    }

    if (!rows.length) {
        body.innerHTML = emptyRow(3, "bi-diagram-3", "No correlation rules");
        return;
    }

    body.innerHTML = rows.map((row) => `
        <tr>
            <td>
                <a class="table-title table-link" href="/incidents?rule=${encodeURIComponent(row.rule_id)}">${escapeHtml(row.name)}</a>
                <span class="table-subtitle">${escapeHtml(row.rule_id)}</span>
            </td>
            <td>${formatValue(row.incidents)}</td>
            <td>${formatValue(row.average_correlation_time_ms)} ms</td>
        </tr>
    `).join("");
}

function renderTopEndpoints(rows) {
    const body = document.getElementById("top-endpoints-body");
    if (!body) {
        return;
    }

    if (!rows.length) {
        body.innerHTML = emptyRow(4, "bi-hdd-network", "No endpoint activity");
        return;
    }

    body.innerHTML = rows.map((row) => `
        <tr class="clickable-row" data-href="/endpoints/${encodeURIComponent(row.endpoint_id)}">
            <td>
                <a class="table-title table-link" href="/endpoints/${encodeURIComponent(row.endpoint_id)}">${escapeHtml(row.hostname || "Unknown")}</a>
                <span class="table-subtitle">${escapeHtml(row.endpoint_id || "")}</span>
            </td>
            <td>${formatValue(row.telemetry)}</td>
            <td>${formatValue(row.alerts)}</td>
            <td>${formatValue(row.incidents)}</td>
        </tr>
    `).join("");
}

function renderSystemHealth(health) {
    const target = document.getElementById("system-health-grid");
    if (!target) {
        return;
    }

    const rows = [
        ["Telemetry Queue", health.telemetry_queue],
        ["Detection Engine", health.detection_engine],
        ["Correlation Engine", health.correlation_engine],
        ["Database Status", health.database_status],
        ["Average Processing Time", `${formatValue(health.average_processing_time_ms)} ms`],
        ["Dropped Events", health.dropped_events],
        ["Memory Usage", formatPercent(health.memory_usage)],
        ["CPU Usage", formatPercent(health.cpu_usage)],
    ];

    target.innerHTML = rows.map(([label, value]) => `
        <div class="health-item">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(formatValue(value))}</strong>
        </div>
    `).join("");
}

function renderCloudStatus(status) {
    const target = document.getElementById("cloud-status-grid");
    if (!target) {
        return;
    }

    const rows = [
        ["Application Mode", status.application_mode],
        ["Public URL", status.public_url],
        ["Server IP", status.server_ip],
        ["Hostname", status.hostname],
        ["Operating System", status.operating_system],
        ["Gunicorn Status", status.gunicorn_status],
        ["Nginx Status", status.nginx_status],
        ["Database", status.database],
        ["Server Uptime", status.server_uptime],
        ["Connected Endpoints", status.connected_endpoints],
        ["Health Status", status.health_status],
    ];

    target.innerHTML = rows.map(([label, value]) => `
        <div class="health-item">
            <span>${escapeHtml(label)}</span>
            <strong>${formatCloudValue(label, value)}</strong>
        </div>
    `).join("");
}

function formatCloudValue(label, value) {
    const formatted = formatValue(value);
    if (label === "Public URL" && formatted !== "N/A") {
        const href = formatted.startsWith("http") ? formatted : `https://${formatted}`;
        return `<a class="table-link" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(formatted)}</a>`;
    }
    return escapeHtml(formatted);
}

function initializeTimelineControls() {
    document.querySelectorAll("[data-timeline-range]").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll("[data-timeline-range]").forEach((item) => {
                item.classList.remove("active");
            });
            button.classList.add("active");
            dashboardState.timelineRange = button.dataset.timelineRange;
            if (dashboardState.data) {
                renderTimeline(dashboardState.data.attack_timeline || {});
            }
        });
    });
}

function renderTimeline(timeline) {
    const canvas = document.getElementById("attackTimelineChart");
    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const range = timeline[dashboardState.timelineRange] || {
        labels: [],
        telemetry: [],
        alerts: [],
        incidents: [],
    };

    const chartData = {
        labels: range.labels,
        datasets: [
            lineDataset("Telemetry", range.telemetry, "#22d3ee"),
            lineDataset("Alerts", range.alerts, "#f97316"),
            lineDataset("Incidents", range.incidents, "#f43f5e"),
        ],
    };

    if (!dashboardState.chart) {
        dashboardState.chart = new Chart(canvas, {
            type: "line",
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: () => {
                    const rangeTarget = {
                        last_hour: "/telemetry",
                        "24_hours": "/alerts",
                        "7_days": "/incidents",
                    }[dashboardState.timelineRange] || "/telemetry";
                    window.location.href = rangeTarget;
                },
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: { labels: { color: "#cbd5e1" } },
                },
                scales: {
                    x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148, 163, 184, 0.12)" } },
                    y: { beginAtZero: true, ticks: { color: "#94a3b8", precision: 0 }, grid: { color: "rgba(148, 163, 184, 0.12)" } },
                },
            },
        });
        return;
    }

    dashboardState.chart.data = chartData;
    dashboardState.chart.update("none");
}

function lineDataset(label, data, color) {
    return {
        label,
        data,
        borderColor: color,
        backgroundColor: `${color}24`,
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.32,
        fill: true,
    };
}

function updateGeneratedAt(value) {
    const target = document.getElementById("dashboard-updated");
    if (!target) {
        return;
    }
    target.textContent = `Updated ${formatDate(value)}`;
}

function getPath(object, path) {
    return path.split(".").reduce((value, key) => {
        if (value === undefined || value === null) {
            return undefined;
        }
        return value[key];
    }, object);
}

function formatValue(value) {
    if (value === undefined || value === null || value === "") {
        return "N/A";
    }
    if (typeof value === "number") {
        return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
    }
    return String(value);
}

function formatPercent(value) {
    if (value === undefined || value === null) {
        return "N/A";
    }
    return `${formatValue(value)}%`;
}

function formatDate(value) {
    if (!value) {
        return "Never";
    }
    return new Date(value).toLocaleString();
}

function statusBadge(status) {
    const normalized = String(status || "Unknown");
    const badgeClass = normalized === "Online" ? "text-bg-success" : "text-bg-secondary";
    return `<span class="badge rounded-pill ${badgeClass}">${escapeHtml(normalized)}</span>`;
}

function emptyRow(columns, icon, text) {
    return `<tr class="empty-row"><td colspan="${columns}"><i class="bi ${icon}"></i>${escapeHtml(text)}</td></tr>`;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function initializeGlobalSearch() {
    const input = document.getElementById("globalSearchInput");
    const results = document.getElementById("globalSearchResults");
    if (!input || !results) {
        return;
    }

    let timer = null;
    input.addEventListener("input", () => {
        window.clearTimeout(timer);
        const query = input.value.trim();
        if (query.length < 2) {
            results.innerHTML = "";
            results.classList.remove("visible");
            return;
        }
        timer = window.setTimeout(async () => {
            const response = await fetch(`/api/v1/search?q=${encodeURIComponent(query)}`);
            const payload = await response.json();
            renderGlobalSearchResults(results, payload.results);
        }, 180);
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".global-search")) {
            results.classList.remove("visible");
        }
    });
}

function renderGlobalSearchResults(container, groupedResults) {
    const sections = Object.entries(groupedResults || {}).filter(([, rows]) => rows.length);
    if (!sections.length) {
        container.innerHTML = `<div class="search-empty">No matches</div>`;
        container.classList.add("visible");
        return;
    }

    container.innerHTML = sections.map(([group, rows]) => `
        <div class="search-group">
            <strong>${escapeHtml(group)}</strong>
            ${rows.map((row) => `
                <a href="${escapeHtml(row.url)}">
                    <span>${escapeHtml(row.label)}</span>
                    <small>${escapeHtml(row.meta || "")}</small>
                </a>
            `).join("")}
        </div>
    `).join("");
    container.classList.add("visible");
}

function initializeTables() {
    document.querySelectorAll(".soc-table").forEach((table) => {
        const state = {
            page: 1,
            pageSize: Number(table.dataset.pageSize || 25),
            search: "",
            sortIndex: -1,
            sortDirection: 1,
        };
        const toolbar = findToolbar(table);
        if (toolbar) {
            toolbar.innerHTML = `
                <div class="table-tools">
                    <input class="form-control form-control-sm" type="search" placeholder="Search table">
                    <select class="form-select form-select-sm">
                        ${[10, 25, 50, 100].map((size) => `<option value="${size}" ${size === state.pageSize ? "selected" : ""}>${size}</option>`).join("")}
                    </select>
                    <span class="table-count"></span>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-light" type="button" data-page-prev>Prev</button>
                        <button class="btn btn-outline-light" type="button" data-page-next>Next</button>
                    </div>
                </div>
            `;
            toolbar.querySelector("input").addEventListener("input", (event) => {
                state.search = event.target.value.toLowerCase();
                state.page = 1;
                applyTableState(table, state, toolbar);
            });
            toolbar.querySelector("select").addEventListener("change", (event) => {
                state.pageSize = Number(event.target.value);
                state.page = 1;
                applyTableState(table, state, toolbar);
            });
            toolbar.querySelector("[data-page-prev]").addEventListener("click", () => {
                state.page = Math.max(1, state.page - 1);
                applyTableState(table, state, toolbar);
            });
            toolbar.querySelector("[data-page-next]").addEventListener("click", () => {
                state.page += 1;
                applyTableState(table, state, toolbar);
            });
        }
        table.querySelectorAll("thead th").forEach((header, index) => {
            header.addEventListener("click", () => {
                state.sortDirection = state.sortIndex === index ? state.sortDirection * -1 : 1;
                state.sortIndex = index;
                applyTableState(table, state, toolbar);
            });
        });
        applyTableState(table, state, toolbar);
    });
}

function findToolbar(table) {
    const panel = table.closest(".panel");
    return panel ? panel.querySelector("[data-table-toolbar]") : null;
}

function applyTableState(table, state, toolbar) {
    const body = table.querySelector("tbody");
    const rows = Array.from(body.querySelectorAll("tr")).filter((row) => !row.classList.contains("empty-row"));
    let visibleRows = rows.filter((row) => row.textContent.toLowerCase().includes(state.search));

    if (state.sortIndex >= 0) {
        visibleRows = visibleRows.sort((left, right) => {
            const a = left.children[state.sortIndex]?.textContent.trim() || "";
            const b = right.children[state.sortIndex]?.textContent.trim() || "";
            return a.localeCompare(b, undefined, { numeric: true }) * state.sortDirection;
        });
        visibleRows.forEach((row) => body.appendChild(row));
    }

    const totalPages = Math.max(1, Math.ceil(visibleRows.length / state.pageSize));
    state.page = Math.min(state.page, totalPages);
    const start = (state.page - 1) * state.pageSize;
    const end = start + state.pageSize;
    rows.forEach((row) => {
        row.style.display = visibleRows.includes(row) && visibleRows.indexOf(row) >= start && visibleRows.indexOf(row) < end ? "" : "none";
    });

    if (toolbar) {
        const count = toolbar.querySelector(".table-count");
        if (count) {
            count.textContent = `${visibleRows.length} rows | page ${state.page}/${totalPages}`;
        }
    }
}

function initializeClickableRows() {
    document.addEventListener("click", (event) => {
        const row = event.target.closest(".clickable-row");
        if (!row || event.target.closest("a, button, input, select")) {
            return;
        }
        if (row.classList.contains("telemetry-row")) {
            openTelemetryDetails(row);
            return;
        }
        if (row.dataset.href) {
            window.location.href = row.dataset.href;
        }
    });
}

function initializeConfirmations() {
    document.addEventListener("click", (event) => {
        const trigger = event.target.closest("[data-confirm]");
        if (!trigger) {
            return;
        }

        const message = trigger.dataset.confirm || "Apply this action?";
        if (!window.confirm(message)) {
            event.preventDefault();
            event.stopPropagation();
        }
    });
}

function initializeTelemetryOffcanvas() {
    document.querySelectorAll(".telemetry-row").forEach((row) => {
        row.addEventListener("click", (event) => {
            if (!event.target.closest("a")) {
                openTelemetryDetails(row);
            }
        });
    });

    const selected = new URLSearchParams(window.location.search).get("telemetry_id");
    if (selected) {
        const row = Array.from(document.querySelectorAll(".telemetry-row"))
            .find((candidate) => candidate.dataset.telemetryId === selected);
        if (row) {
            openTelemetryDetails(row);
        }
    }
}

function openTelemetryDetails(row) {
    const rawJson = row.dataset.json || "{}";
    document.getElementById("telemetryDetailId").textContent = row.dataset.telemetryId;
    document.getElementById("telemetryDetailEndpoint").innerHTML = `<a class="table-link" href="${escapeHtml(row.dataset.endpointUrl)}">${escapeHtml(row.dataset.endpoint)}</a>`;
    document.getElementById("telemetryDetailCollector").textContent = row.dataset.collector;
    document.getElementById("telemetryDetailSeverity").textContent = row.dataset.severity;
    document.getElementById("telemetryDetailEventType").textContent = row.dataset.eventType;
    document.getElementById("telemetryDetailTimestamp").textContent = row.dataset.timestamp;
    document.getElementById("telemetryRawJson").textContent = JSON.stringify(JSON.parse(rawJson), null, 2);
    document.getElementById("openTelemetryEndpoint").href = row.dataset.endpointUrl;

    document.getElementById("copyTelemetryJson").onclick = async () => {
        await navigator.clipboard.writeText(document.getElementById("telemetryRawJson").textContent);
        showNotification("Telemetry JSON copied.", "success");
    };
    document.getElementById("downloadTelemetryJson").onclick = () => {
        const blob = new Blob([document.getElementById("telemetryRawJson").textContent], { type: "application/json" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `telemetry-${row.dataset.telemetryId}.json`;
        link.click();
        URL.revokeObjectURL(link.href);
    };

    bootstrap.Offcanvas.getOrCreateInstance(document.getElementById("telemetryOffcanvas")).show();
}

function initializeFilterForms() {
    document.querySelectorAll(".filter-bar").forEach((form) => {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const params = new URLSearchParams(new FormData(form));
            [...params.entries()].forEach(([key, value]) => {
                if (!value) {
                    params.delete(key);
                }
            });
            const url = `${window.location.pathname}?${params.toString()}`;
            await replaceLiveSection(url);
            window.history.pushState({}, "", url);
        });
    });
}

function initializeLiveSectionPolling() {
    const section = document.getElementById("live-table-section");
    if (!section) {
        return;
    }
    window.setInterval(async () => {
        if (!document.querySelector(".offcanvas.show")) {
            await replaceLiveSection(window.location.href);
        }
    }, refreshIntervalMs);
}

async function replaceLiveSection(url) {
    const section = document.getElementById("live-table-section");
    if (!section) {
        return;
    }
    const response = await fetch(url, { headers: { "X-Requested-With": "fetch" } });
    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const fresh = doc.getElementById("live-table-section");
    if (!fresh) {
        return;
    }
    section.innerHTML = fresh.innerHTML;
    initializeTables();
    initializeTelemetryOffcanvas();
    initializeFilterForms();
}

function showNotification(message, category) {
    const stack = document.querySelector(".toast-stack") || document.createElement("div");
    stack.className = "toast-stack";
    if (!stack.parentElement) {
        document.querySelector(".main-content").prepend(stack);
    }
    const alert = document.createElement("div");
    alert.className = `alert alert-${category} alert-dismissible fade show`;
    alert.innerHTML = `${escapeHtml(message)}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
    stack.appendChild(alert);
    window.setTimeout(() => alert.remove(), 3000);
}
