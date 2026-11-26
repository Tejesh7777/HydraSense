/**
 * HydraSense - Main Application Controller (SIH26023)
 * Handles SPA navigation, API requests, Chart.js visualizations, and UI events.
 */

const AppState = {
    currentView: 'dashboard',
    overviewData: null,
    samplesData: [],
    edaData: null,
    distanceData: null,
    clusteringData: null,
    validationData: null,
    comparisonData: null,
    historyData: [],
    selectedSampleForRec: null,
    visualizer3D: null,
    charts: {}
};

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initGlobalControls();
    loadView('dashboard');
});

// ==========================================
// Navigation & View Routing
// ==========================================
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link[data-view]');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const viewName = link.getAttribute('data-view');
            loadView(viewName);
        });
    });
}

function loadView(viewName) {
    AppState.currentView = viewName;

    // Update active nav link
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const activeLink = document.querySelector(`.nav-link[data-view="${viewName}"]`);
    if (activeLink) activeLink.classList.add('active');

    // Update view sections
    document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
    const activeSection = document.getElementById(`view-${viewName}`);
    if (activeSection) activeSection.classList.add('active');

    // Update Topbar View Badge
    const viewBadge = document.getElementById('topbar-view-name');
    if (viewBadge) {
        viewBadge.textContent = viewName.toUpperCase().replace('-', ' ');
    }

    // Trigger view-specific loader
    switch (viewName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'data-mgmt':
            loadDataManagement();
            break;
        case 'eda':
            loadEDA();
            break;
        case 'distance':
            loadDistanceEngine();
            break;
        case 'clustering3d':
            loadClustering3D();
            break;
        case 'comparison':
            loadComparison();
            break;
        case 'treatment':
            loadTreatment();
            break;
        case 'validation':
            loadValidation();
            break;
        case 'history':
            loadHistory();
            break;
    }
}

function initGlobalControls() {
    // Clear Database buttons (both topbar and data management section)
    const handleClear = () => {
        if (confirm("Are you sure you want to CLEAR ALL DATA?\n\nThis will remove all current samples so you can add your custom dataset on a clean slate.")) {
            fetch('/api/clear_data', { method: 'POST' })
                .then(r => r.json())
                .then(res => {
                    showToast(res.message || "All samples cleared.");
                    const topCount = document.getElementById('topbar-sample-count');
                    if (topCount) topCount.textContent = '0';
                    loadView(AppState.currentView);
                })
                .catch(err => showToast("Error clearing database", "error"));
        }
    };

    const clearBtn1 = document.getElementById('btn-clear-db-topbar');
    if (clearBtn1) clearBtn1.addEventListener('click', handleClear);

    const clearBtn2 = document.getElementById('btn-clear-db-mgmt');
    if (clearBtn2) clearBtn2.addEventListener('click', handleClear);

    // Reset Database buttons (restore 270 standard reference samples)
    const handleReset = () => {
        if (confirm("Restore the standard reference scientific dataset (270 samples)?")) {
            fetch('/api/reset_database', { method: 'POST' })
                .then(r => r.json())
                .then(res => {
                    showToast(res.message || "Database reset successfully.");
                    loadView(AppState.currentView);
                })
                .catch(err => showToast("Error resetting database", "error"));
        }
    };

    const resetBtn1 = document.getElementById('btn-reset-db');
    if (resetBtn1) resetBtn1.addEventListener('click', handleReset);

    const resetBtn2 = document.getElementById('btn-reset-db-mgmt');
    if (resetBtn2) resetBtn2.addEventListener('click', handleReset);

    // Auto-Classify Unlabeled Samples button
    const autoClassifyBtn = document.getElementById('btn-auto-classify');
    if (autoClassifyBtn) {
        autoClassifyBtn.addEventListener('click', () => {
            fetch('/api/auto_classify', { method: 'POST' })
                .then(r => r.json())
                .then(res => {
                    showToast(res.message);
                    loadView(AppState.currentView);
                })
                .catch(err => showToast("Error during auto-classification", "error"));
        });
    }

    // Export full CSV
    const exportCsvBtn = document.getElementById('btn-export-csv-global');
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', () => {
            window.location.href = '/api/export/csv';
        });
    }
}

// ==========================================
// 1. Dashboard View
// ==========================================
async function loadDashboard() {
    try {
        const res = await fetch('/api/overview');
        const data = await res.json();
        AppState.overviewData = data;

        // Total count pill
        document.getElementById('dash-total-samples').textContent = data.total_samples || 0;
        document.getElementById('topbar-sample-count').textContent = data.total_samples || 0;

        // Parameter mini cards
        renderParameterCards(data.parameter_averages);

        // Water Quality Index Gauge
        renderWQIGauge(data.average_wqi, data.water_health_index);

        // Category breakdown chart
        renderCategoryDoughnut(data.category_distribution);

        // Water Quality Trends line chart
        renderTrendsChart();

        // Recent samples list
        renderRecentSamples(data.recent_samples);

    } catch (err) {
        showToast("Failed to load dashboard data", "error");
    }
}

function renderParameterCards(paramAverages) {
    const container = document.getElementById('dashboard-param-grid');
    if (!container || !paramAverages) return;

    container.innerHTML = '';
    for (const [param, val] of Object.entries(paramAverages)) {
        let badgeClass = 'badge-safe';
        let statusText = 'Normal';

        // Contextual rule
        if (param === 'COD' && val.mean > 150) { badgeClass = 'badge-warn'; statusText = 'Elevated'; }
        else if (param === 'BOD' && val.mean > 50) { badgeClass = 'badge-warn'; statusText = 'Elevated'; }
        else if (param === 'Oil_and_Grease' && val.mean > 20) { badgeClass = 'badge-danger'; statusText = 'High Lipids'; }
        else if (param === 'Turbidity' && val.mean > 40) { badgeClass = 'badge-warn'; statusText = 'Turbid'; }

        const card = document.createElement('div');
        card.className = 'param-card';
        card.innerHTML = `
            <div class="param-label">
                <span>${param.replace('_', ' ')}</span>
                <span class="param-badge ${badgeClass}">${statusText}</span>
            </div>
            <div class="param-value-box">
                <span class="param-value">${val.mean}</span>
                <span class="param-unit">${val.unit}</span>
            </div>
            <div style="font-size:0.7rem; color:var(--text-muted); display:flex; justify-content:space-between; margin-top:2px;">
                <span>Min: ${val.min}</span>
                <span>Max: ${val.max}</span>
            </div>
        `;
        container.appendChild(card);
    }
}

function renderWQIGauge(avgWqi, healthIndex) {
    const canvas = document.getElementById('wqi-gauge-chart');
    if (!canvas) return;

    if (AppState.charts['wqiGauge']) {
        AppState.charts['wqiGauge'].destroy();
    }

    // Set numbers in UI
    const numEl = document.getElementById('wqi-display-value');
    const labelEl = document.getElementById('wqi-display-status');
    if (numEl) numEl.textContent = healthIndex;

    let statusStr = 'Excellent';
    let statusColor = '#00f0ff';
    if (healthIndex < 40) { statusStr = 'Poor'; statusColor = '#ff0055'; }
    else if (healthIndex < 70) { statusStr = 'Fair'; statusColor = '#ffb703'; }
    else if (healthIndex < 85) { statusStr = 'Good'; statusColor = '#00ff88'; }

    if (labelEl) {
        labelEl.textContent = statusStr;
        labelEl.style.color = statusColor;
    }

    const ctx = canvas.getContext('2d');
    AppState.charts['wqiGauge'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [healthIndex, 100 - healthIndex],
                backgroundColor: [statusColor, 'rgba(10, 25, 55, 0.45)'],
                borderWidth: 0,
                circumference: 260,
                rotation: 230,
                borderRadius: 8
            }]
        },
        options: {
            cutout: '80%',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: { enabled: false },
                legend: { display: false }
            }
        }
    });
}

function renderCategoryDoughnut(catDist) {
    const canvas = document.getElementById('category-doughnut-chart');
    if (!canvas || !catDist) return;

    if (AppState.charts['categoryDoughnut']) {
        AppState.charts['categoryDoughnut'].destroy();
    }

    const labels = Object.keys(catDist);
    const data = Object.values(catDist);
    const colors = ['#00f0ff', '#00ff88', '#ffb703', '#ff0055'];

    const ctx = canvas.getContext('2d');
    AppState.charts['categoryDoughnut'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 1,
                borderColor: 'rgba(0, 240, 255, 0.25)'
            }]
        },
        options: {
            cutout: '65%',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#9bb1d0', font: { size: 11 } }
                }
            }
        }
    });
}

function renderTrendsChart() {
    const canvas = document.getElementById('trends-line-chart');
    if (!canvas) return;

    if (AppState.charts['trendsLine']) {
        AppState.charts['trendsLine'].destroy();
    }

    const labels = ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00', '24:00'];
    const ctx = canvas.getContext('2d');

    AppState.charts['trendsLine'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'pH (x10)',
                    data: [72, 73, 71, 74, 76, 75, 74, 73, 72],
                    borderColor: '#00f0ff',
                    backgroundColor: 'rgba(0, 240, 255, 0.08)',
                    tension: 0.4,
                    fill: false,
                    borderWidth: 2
                },
                {
                    label: 'COD (mg/L)',
                    data: [120, 95, 110, 180, 240, 210, 195, 160, 130],
                    borderColor: '#0088ff',
                    backgroundColor: 'rgba(0, 136, 255, 0.08)',
                    tension: 0.4,
                    fill: false,
                    borderWidth: 2
                },
                {
                    label: 'BOD (mg/L)',
                    data: [45, 38, 42, 75, 95, 82, 78, 60, 50],
                    borderColor: '#00ffc8',
                    backgroundColor: 'rgba(0, 255, 200, 0.08)',
                    tension: 0.4,
                    fill: false,
                    borderWidth: 2
                },
                {
                    label: 'TSS (mg/L)',
                    data: [35, 28, 30, 65, 85, 70, 64, 52, 40],
                    borderColor: '#ffb703',
                    tension: 0.4,
                    fill: false,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: 'rgba(0, 240, 255, 0.06)' },
                    ticks: { color: '#597399' }
                },
                y: {
                    grid: { color: 'rgba(0, 240, 255, 0.06)' },
                    ticks: { color: '#597399' }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: '#9bb1d0', font: { size: 11 } }
                }
            }
        }
    });
}

function renderRecentSamples(samples) {
    const tbody = document.getElementById('dashboard-recent-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';
    if (!samples || samples.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align:center; color:var(--text-muted); padding:24px;">
                    No samples currently in database. Navigate to <strong>"Data & Upload"</strong> to import your custom dataset.
                </td>
            </tr>
        `;
        return;
    }

    samples.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${s.sample_id}</strong></td>
            <td>${s.source}</td>
            <td>${s.pH}</td>
            <td>${s.TDS}</td>
            <td>${s.BOD}</td>
            <td>${s.COD}</td>
            <td><span class="param-badge badge-safe">${s.Lab_Suitability_Category}</span></td>
            <td>
                <button class="btn-outline" style="padding:4px 8px; font-size:0.75rem;" onclick="inspectSample('${s.sample_id}')">
                    Inspect
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// ==========================================
// 2. Data Management View
// ==========================================
async function loadDataManagement() {
    initCSVUpload();
    initManualEntryForm();
    await fetchAndRenderSamplesTable();
}

function initCSVUpload() {
    const dropzone = document.getElementById('csv-dropzone');
    const fileInput = document.getElementById('csv-file-input');
    if (!dropzone || !fileInput) return;

    dropzone.onclick = () => fileInput.click();

    dropzone.ondragover = (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    };
    dropzone.ondragleave = () => dropzone.classList.remove('dragover');
    dropzone.ondrop = (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    };

    fileInput.onchange = () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    };
}

async function handleFileUpload(file) {
    const statusEl = document.getElementById('upload-status-msg');
    const replaceToggle = document.getElementById('csv-replace-toggle');
    const isReplace = replaceToggle ? replaceToggle.checked : false;

    if (statusEl) {
        statusEl.textContent = `${isReplace ? 'Clearing old data & uploading' : 'Uploading & Validating'}: ${file.name}...`;
        statusEl.style.color = 'var(--cyan-primary)';
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('replace_existing', isReplace ? 'true' : 'false');

    try {
        const res = await fetch('/api/upload_csv', {
            method: 'POST',
            body: formData
        });
        const json = await res.json();
        if (res.ok) {
            showToast(json.message || "CSV Uploaded successfully!");
            if (statusEl) {
                statusEl.textContent = `Success: ${json.message}`;
                statusEl.style.color = 'var(--emerald-safe)';
            }
            await fetchAndRenderSamplesTable();
            
            // Refresh topbar sample count
            const ovRes = await fetch('/api/overview');
            const ovData = await ovRes.json();
            const topCount = document.getElementById('topbar-sample-count');
            if (topCount) topCount.textContent = ovData.total_samples || 0;
            const dashCount = document.getElementById('dash-total-samples');
            if (dashCount) dashCount.textContent = ovData.total_samples || 0;
        } else {
            showToast(json.error || "Upload failed", "error");
            if (statusEl) {
                statusEl.textContent = `Error: ${json.error}`;
                statusEl.style.color = 'var(--coral-danger)';
            }
        }
    } catch (err) {
        showToast("Network error uploading file", "error");
    }
}

function initManualEntryForm() {
    const form = document.getElementById('manual-sample-form');
    if (!form) return;

    form.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const payload = {};
        formData.forEach((val, key) => {
            payload[key] = val;
        });

        try {
            const res = await fetch('/api/samples', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (res.ok) {
                showToast(`Sample ${data.sample_id} recorded & analyzed!`);
                form.reset();
                fetchAndRenderSamplesTable();

                // Show instant result summary modal
                showSampleModal(data.sample, data.treatment, data.wqi);
            } else {
                showToast(data.error || "Failed to add sample", "error");
            }
        } catch (err) {
            showToast("Network error submitting sample", "error");
        }
    };
}

async function fetchAndRenderSamplesTable(search = '', category = 'All') {
    try {
        const res = await fetch(`/api/samples?search=${encodeURIComponent(search)}&category=${encodeURIComponent(category)}`);
        const data = await res.json();
        AppState.samplesData = data.samples || [];

        const tbody = document.getElementById('samples-data-tbody');
        const countSpan = document.getElementById('table-count-label');
        if (countSpan) countSpan.textContent = `Showing ${AppState.samplesData.length} records`;

        if (!tbody) return;
        tbody.innerHTML = '';

        if (AppState.samplesData.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="13" style="text-align:center; color:var(--text-muted); padding:32px;">
                        No samples found in database. Drag & drop your custom CSV file above or use the manual profiler to add your data.
                    </td>
                </tr>
            `;
            return;
        }

        AppState.samplesData.forEach(s => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${s.sample_id}</strong></td>
                <td>${s.source}</td>
                <td>${s.pH}</td>
                <td>${s.TDS}</td>
                <td>${s.BOD}</td>
                <td>${s.COD}</td>
                <td>${s.Turbidity}</td>
                <td>${s.EC}</td>
                <td>${s.TSS}</td>
                <td>${s.Oil_and_Grease}</td>
                <td>${s.Temperature}</td>
                <td><span class="param-badge badge-safe">${s.Lab_Suitability_Category}</span></td>
                <td>
                    <button class="btn-outline" style="padding:3px 8px; font-size:0.75rem;" onclick="inspectSample('${s.sample_id}')">
                        Inspect
                    </button>
                    <button class="btn-outline" style="padding:3px 8px; font-size:0.75rem; color:var(--coral-danger); border-color:rgba(255,0,85,0.3);" onclick="deleteSample('${s.sample_id}')">
                        ✕
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Search & Filter event handlers
        const searchInput = document.getElementById('sample-search-input');
        const catFilter = document.getElementById('sample-cat-filter');

        if (searchInput && !searchInput.dataset.bound) {
            searchInput.dataset.bound = "true";
            searchInput.addEventListener('input', () => {
                fetchAndRenderSamplesTable(searchInput.value, catFilter ? catFilter.value : 'All');
            });
        }
        if (catFilter && !catFilter.dataset.bound) {
            catFilter.dataset.bound = "true";
            catFilter.addEventListener('change', () => {
                fetchAndRenderSamplesTable(searchInput ? searchInput.value : '', catFilter.value);
            });
        }

    } catch (err) {
        showToast("Failed to fetch samples table", "error");
    }
}

async function deleteSample(sampleId) {
    if (!confirm(`Delete sample ${sampleId}?`)) return;
    try {
        const res = await fetch(`/api/samples/${sampleId}`, { method: 'DELETE' });
        if (res.ok) {
            showToast(`Deleted ${sampleId}`);
            fetchAndRenderSamplesTable();
        } else {
            showToast("Failed to delete", "error");
        }
    } catch (e) {
        showToast("Error deleting sample", "error");
    }
}

// ==========================================
// 3. Exploratory Data Analysis (EDA) View
// ==========================================
async function loadEDA() {
    try {
        const res = await fetch('/api/eda');
        const data = await res.json();
        AppState.edaData = data;

        renderSummaryStatsTable(data.summary_statistics);
        renderCorrelationHeatmap(data.correlation_matrix);
        renderDistributionChart(data.distributions, 'BOD');
        renderPCAAnalysis(data.pca_summary);

        // Bind dropdown for distribution parameter picker
        const distPicker = document.getElementById('eda-dist-param-picker');
        if (distPicker && !distPicker.dataset.bound) {
            distPicker.dataset.bound = "true";
            distPicker.addEventListener('change', (e) => {
                renderDistributionChart(data.distributions, e.target.value);
            });
        }

        // Bind correlation matrix type toggle
        const corrToggle = document.getElementById('eda-corr-toggle');
        if (corrToggle && !corrToggle.dataset.bound) {
            corrToggle.dataset.bound = "true";
            corrToggle.addEventListener('change', (e) => {
                renderCorrelationHeatmap(data.correlation_matrix, e.target.value);
            });
        }

    } catch (err) {
        showToast("Failed to load EDA analytics", "error");
    }
}

function renderSummaryStatsTable(stats) {
    const tbody = document.getElementById('eda-summary-tbody');
    if (!tbody || !stats) return;

    tbody.innerHTML = '';
    for (const [col, s] of Object.entries(stats)) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${s.name}</strong></td>
            <td>${s.unit}</td>
            <td>${s.mean}</td>
            <td>${s.std}</td>
            <td>${s.min}</td>
            <td>${s.q25}</td>
            <td><strong>${s.median}</strong></td>
            <td>${s.q75}</td>
            <td>${s.max}</td>
            <td>${s.iqr}</td>
            <td><span class="param-badge ${s.outliers_count > 0 ? 'badge-warn' : 'badge-safe'}">${s.outliers_count}</span></td>
        `;
        tbody.appendChild(tr);
    }
}

function renderCorrelationHeatmap(corrData, type = 'pearson') {
    const container = document.getElementById('eda-correlation-container');
    if (!container || !corrData) return;

    const matrix = corrData[type] || corrData['pearson'];
    const params = corrData.parameters;

    let html = `<div style="overflow-x:auto;"><table class="cyber-table" style="text-align:center;"><thead><tr><th>Param</th>`;
    params.forEach(p => { html += `<th>${p}</th>`; });
    html += `</tr></thead><tbody>`;

    params.forEach(r => {
        html += `<tr><td><strong>${r}</strong></td>`;
        params.forEach(c => {
            const val = matrix[r][c];
            // Color scale: -1 (blue) to 0 (dark) to +1 (cyan)
            let color = 'rgba(0, 240, 255, 0.05)';
            if (val > 0.7) color = 'rgba(0, 240, 255, 0.45)';
            else if (val > 0.4) color = 'rgba(0, 240, 255, 0.25)';
            else if (val > 0.1) color = 'rgba(0, 240, 255, 0.12)';
            else if (val < -0.3) color = 'rgba(255, 0, 85, 0.25)';

            html += `<td style="background:${color}; font-family:var(--font-mono); font-size:0.75rem;">${val}</td>`;
        });
        html += `</tr>`;
    });
    html += `</tbody></table></div>`;
    container.innerHTML = html;
}

function renderDistributionChart(distData, parameter = 'BOD') {
    const canvas = document.getElementById('eda-dist-chart');
    if (!canvas || !distData || !distData[parameter]) return;

    if (AppState.charts['edaDist']) {
        AppState.charts['edaDist'].destroy();
    }

    const pData = distData[parameter];
    const ctx = canvas.getContext('2d');

    AppState.charts['edaDist'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: pData.labels,
            datasets: [{
                label: `Frequency Distribution: ${parameter} (${pData.unit})`,
                data: pData.counts,
                backgroundColor: 'rgba(0, 240, 255, 0.45)',
                borderColor: '#00f0ff',
                borderWidth: 1.5,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: 'rgba(0, 240, 255, 0.06)' },
                    ticks: { color: '#8fa6c8', font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(0, 240, 255, 0.06)' },
                    ticks: { color: '#8fa6c8' }
                }
            },
            plugins: {
                legend: { labels: { color: '#f0f6fc' } }
            }
        }
    });
}

function renderPCAAnalysis(pcaSummary) {
    if (!pcaSummary) return;

    // Explained variance text
    const varEl = document.getElementById('pca-cumulative-var');
    if (varEl) varEl.textContent = `${pcaSummary.cumulative_variance}%`;

    // Loadings Table
    const tbody = document.getElementById('pca-loadings-tbody');
    if (!tbody || !pcaSummary.loadings) return;

    tbody.innerHTML = '';
    pcaSummary.loadings.forEach(l => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${l.parameter}</strong></td>
            <td>${l.name}</td>
            <td style="font-family:var(--font-mono);">${l.PC1}</td>
            <td style="font-family:var(--font-mono);">${l.PC2}</td>
            <td style="font-family:var(--font-mono);">${l.PC3}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ==========================================
// 4. Distance & Similarity Engine (Objective 2)
// ==========================================
async function loadDistanceEngine(queryId = null) {
    try {
        const payload = { k_neighbors: 5 };
        if (queryId) payload.query_sample_id = queryId;

        const res = await fetch('/api/distance_analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        AppState.distanceData = data;

        // Metric stats cards
        renderDistanceStats(data.stats);

        // Matrix preview table
        renderDistanceMatrixTable(data.preview_sample_ids, data.euclidean_matrix_preview, 'euclidean');

        // Nearest neighbors comparison
        renderNearestNeighbors(data.nearest_neighbors, data.query_info);

        // Dimension contribution breakdown
        renderDimensionBreakdown(data.dimension_breakdown);

        // Populate query sample picker dropdown
        populateDistanceSamplePicker(queryId || (data.query_info ? data.query_info.sample_id : null));

        // Distance matrix toggle (Euclidean vs Manhattan)
        const toggle = document.getElementById('dist-matrix-metric-toggle');
        if (toggle && !toggle.dataset.bound) {
            toggle.dataset.bound = "true";
            toggle.addEventListener('change', (e) => {
                const metric = e.target.value;
                const mat = (metric === 'manhattan') ? data.manhattan_matrix_preview : data.euclidean_matrix_preview;
                renderDistanceMatrixTable(data.preview_sample_ids, mat, metric);
            });
        }

    } catch (err) {
        showToast("Failed to run distance analysis", "error");
    }
}

function renderDistanceStats(stats) {
    if (!stats) return;

    document.getElementById('dist-p-corr').textContent = stats.pearson_correlation;
    document.getElementById('dist-s-corr').textContent = stats.spearman_rank_correlation;

    document.getElementById('dist-euc-mean').textContent = stats.euclidean.mean;
    document.getElementById('dist-euc-max').textContent = stats.euclidean.max;

    document.getElementById('dist-man-mean').textContent = stats.manhattan.mean;
    document.getElementById('dist-man-max').textContent = stats.manhattan.max;
}

function renderDistanceMatrixTable(ids, matrix, metricName) {
    const container = document.getElementById('distance-matrix-container');
    if (!container || !ids || !matrix) return;

    let html = `<div style="overflow-x:auto;"><table class="cyber-table" style="text-align:center;"><thead><tr><th>${metricName.toUpperCase()}</th>`;
    ids.forEach(id => { html += `<th>${id}</th>`; });
    html += `</tr></thead><tbody>`;

    for (let i = 0; i < ids.length; i++) {
        html += `<tr><td><strong>${ids[i]}</strong></td>`;
        for (let j = 0; j < ids.length; j++) {
            const val = matrix[i][j];
            let bg = (i === j) ? 'rgba(0, 240, 255, 0.15)' : 'transparent';
            html += `<td style="background:${bg}; font-family:var(--font-mono); font-size:0.75rem;">${val}</td>`;
        }
        html += `</tr>`;
    }
    html += `</tbody></table></div>`;
    container.innerHTML = html;
}

function renderNearestNeighbors(nnData, queryInfo) {
    const eucTbody = document.getElementById('nn-euclidean-tbody');
    const manTbody = document.getElementById('nn-manhattan-tbody');
    if (!nnData) return;

    if (eucTbody && nnData.euclidean) {
        eucTbody.innerHTML = '';
        nnData.euclidean.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>#${item.rank}</td>
                <td><strong>${item.sample_id}</strong></td>
                <td>${item.source}</td>
                <td style="font-family:var(--font-mono); color:var(--cyan-primary);">${item.distance}</td>
                <td><strong>${item.similarity_pct}%</strong></td>
                <td><span class="param-badge badge-safe">${item.Lab_Suitability_Category}</span></td>
            `;
            eucTbody.appendChild(tr);
        });
    }

    if (manTbody && nnData.manhattan) {
        manTbody.innerHTML = '';
        nnData.manhattan.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>#${item.rank}</td>
                <td><strong>${item.sample_id}</strong></td>
                <td>${item.source}</td>
                <td style="font-family:var(--font-mono); color:var(--aqua-accent);">${item.distance}</td>
                <td><strong>${item.similarity_pct}%</strong></td>
                <td><span class="param-badge badge-safe">${item.Lab_Suitability_Category}</span></td>
            `;
            manTbody.appendChild(tr);
        });
    }
}

function renderDimensionBreakdown(breakdownData) {
    const tbody = document.getElementById('dimension-breakdown-tbody');
    const targetEl = document.getElementById('dim-target-id');
    if (!tbody || !breakdownData) return;

    if (targetEl) targetEl.textContent = breakdownData.target_sample_id || 'Nearest Sample';

    tbody.innerHTML = '';
    breakdownData.breakdown.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${row.parameter}</strong></td>
            <td>${row.u_val}</td>
            <td>${row.v_val}</td>
            <td>${row.delta}</td>
            <td style="font-family:var(--font-mono); color:var(--cyan-primary);">${row.manhattan_contrib_pct}%</td>
            <td style="font-family:var(--font-mono); color:var(--blue-accent);">${row.euclidean_sq_contrib_pct}%</td>
        `;
        tbody.appendChild(tr);
    });
}

function populateDistanceSamplePicker(currentId) {
    const picker = document.getElementById('dist-sample-select');
    if (!picker || !AppState.samplesData || AppState.samplesData.length === 0) return;

    picker.innerHTML = '';
    AppState.samplesData.slice(0, 100).forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.sample_id;
        opt.textContent = `${s.sample_id} - ${s.source}`;
        if (s.sample_id === currentId) opt.selected = true;
        picker.appendChild(opt);
    });

    if (!picker.dataset.bound) {
        picker.dataset.bound = "true";
        picker.addEventListener('change', (e) => {
            loadDistanceEngine(e.target.value);
        });
    }
}

// ==========================================
// 5. 3D Clustering Visualizer View
// ==========================================
async function loadClustering3D() {
    if (!AppState.visualizer3D) {
        AppState.visualizer3D = new Greywater3DVisualizer('threejs-canvas-wrapper');

        // Hook sample selection
        window.onSelect3DSample = (sampleData) => {
            showToast(`Inspecting ${sampleData.id} (${sampleData.category})`);
            inspectSample(sampleData.id);
        };
    }

    await runClusteringExecution();
    initClusteringControls();
}

async function runClusteringExecution() {
    const algoSelect = document.getElementById('cluster-algo-select');
    const kSelect = document.getElementById('cluster-k-select');
    const linkageSelect = document.getElementById('cluster-linkage-select');

    const payload = {
        algorithm: algoSelect ? algoSelect.value : 'kmeans',
        n_clusters: kSelect ? parseInt(kSelect.value) : 4,
        linkage: linkageSelect ? linkageSelect.value : 'average'
    };

    try {
        const res = await fetch('/api/clustering', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        AppState.clusteringData = data;

        // Feed 3D visualizer
        if (AppState.visualizer3D && data.threejs_payload) {
            AppState.visualizer3D.loadData(data.threejs_payload);
        }

        // Render clustering score metrics
        renderClusteringMetrics(data);

    } catch (err) {
        showToast("Failed to run clustering", "error");
    }
}

function renderClusteringMetrics(data) {
    document.getElementById('c-metric-algo').textContent = data.algorithm;
    document.getElementById('c-metric-sil-euc').textContent = data.silhouette_euclidean;
    document.getElementById('c-metric-sil-man').textContent = data.silhouette_manhattan;
    document.getElementById('c-metric-db').textContent = data.davies_bouldin_index;
    document.getElementById('c-metric-ch').textContent = data.calinski_harabasz_index;
    document.getElementById('c-metric-time').textContent = `${data.execution_time_ms} ms`;
}

function initClusteringControls() {
    const runBtn = document.getElementById('btn-run-clustering');
    if (runBtn && !runBtn.dataset.bound) {
        runBtn.dataset.bound = "true";
        runBtn.addEventListener('click', () => runClusteringExecution());
    }

    const resetCamBtn = document.getElementById('btn-3d-reset-cam');
    if (resetCamBtn && !resetCamBtn.dataset.bound) {
        resetCamBtn.dataset.bound = "true";
        resetCamBtn.addEventListener('click', () => {
            if (AppState.visualizer3D) AppState.visualizer3D.resetCamera();
        });
    }

    const autoRotBtn = document.getElementById('btn-3d-autorotate');
    if (autoRotBtn && !autoRotBtn.dataset.bound) {
        autoRotBtn.dataset.bound = "true";
        autoRotBtn.addEventListener('click', () => {
            if (AppState.visualizer3D) {
                const isActive = AppState.visualizer3D.toggleAutoRotate();
                autoRotBtn.classList.toggle('active', isActive);
            }
        });
    }
}

// ==========================================
// 6. Algorithm Comparison View (Objective 2)
// ==========================================
async function loadComparison() {
    try {
        const res = await fetch('/api/algorithm_comparison');
        const data = await res.json();
        AppState.comparisonData = data;

        renderComparisonBenchmarkTable(data.benchmarks);
        renderComparisonBarCharts(data.benchmarks);

    } catch (err) {
        showToast("Failed to load algorithm comparison", "error");
    }
}

function renderComparisonBenchmarkTable(benchmarks) {
    const tbody = document.getElementById('comparison-benchmarks-tbody');
    if (!tbody || !benchmarks) return;

    tbody.innerHTML = '';
    benchmarks.forEach(b => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${b.algorithm}</strong></td>
            <td><span class="param-badge badge-safe">${b.distance_metric}</span></td>
            <td style="font-family:var(--font-mono);">${b.silhouette_euclidean}</td>
            <td style="font-family:var(--font-mono);">${b.silhouette_manhattan}</td>
            <td style="font-family:var(--font-mono);">${b.davies_bouldin_index}</td>
            <td style="font-family:var(--font-mono); color:var(--cyan-primary);"><strong>${Math.round(b.accuracy * 1000) / 10}%</strong></td>
            <td style="font-family:var(--font-mono);">${Math.round(b.f1_macro * 1000) / 10}%</td>
            <td style="font-family:var(--font-mono);">${b.execution_time_ms} ms</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderComparisonBarCharts(benchmarks) {
    const canvas1 = document.getElementById('comp-chart-quality');
    const canvas2 = document.getElementById('comp-chart-accuracy');
    if (!benchmarks) return;

    const labels = benchmarks.map(b => b.algorithm.replace('Hierarchical', 'H.'));

    if (canvas1) {
        if (AppState.charts['compQuality']) AppState.charts['compQuality'].destroy();
        const ctx1 = canvas1.getContext('2d');
        AppState.charts['compQuality'] = new Chart(ctx1, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Silhouette (Euclidean)',
                        data: benchmarks.map(b => b.silhouette_euclidean),
                        backgroundColor: 'rgba(0, 240, 255, 0.65)'
                    },
                    {
                        label: 'Silhouette (Manhattan)',
                        data: benchmarks.map(b => b.silhouette_manhattan),
                        backgroundColor: 'rgba(0, 255, 200, 0.65)'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: '#8fa6c8', font: { size: 10 } } },
                    y: { ticks: { color: '#8fa6c8' } }
                },
                plugins: { legend: { labels: { color: '#ffffff' } } }
            }
        });
    }

    if (canvas2) {
        if (AppState.charts['compAccuracy']) AppState.charts['compAccuracy'].destroy();
        const ctx2 = canvas2.getContext('2d');
        AppState.charts['compAccuracy'] = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Validation Accuracy (%)',
                        data: benchmarks.map(b => Math.round(b.accuracy * 1000) / 10),
                        backgroundColor: 'rgba(0, 136, 255, 0.75)'
                    },
                    {
                        label: 'Macro F1-Score (%)',
                        data: benchmarks.map(b => Math.round(b.f1_macro * 1000) / 10),
                        backgroundColor: 'rgba(157, 78, 221, 0.75)'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: '#8fa6c8', font: { size: 10 } } },
                    y: { max: 100, ticks: { color: '#8fa6c8' } }
                },
                plugins: { legend: { labels: { color: '#ffffff' } } }
            }
        });
    }
}

// ==========================================
// 7. Treatment Recommendations View
// ==========================================
async function loadTreatment(sampleId = null) {
    try {
        const payload = sampleId ? { sample_id: sampleId } : {};
        const res = await fetch('/api/recommendation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        AppState.selectedSampleForRec = data;

        // Render Sample Info Banner
        renderTreatmentHeader(data.sample, data.wqi, data.treatment.category);

        // Render Radar Chart
        renderContaminationRadar(data.profile);

        // Render Treatment Train Steps
        renderTreatmentTrain(data.treatment.stages);

        // Render Dosing Schedule
        renderDosingSchedule(data.treatment.chemical_dosing);

        // Render Reuse Suitability Matrix
        renderReuseMatrix(data.treatment.suitability_matrix);

        // Populate sample picker
        populateTreatmentSamplePicker(data.sample.sample_id);

        // PDF Download Button
        const pdfBtn = document.getElementById('btn-download-pdf-rec');
        if (pdfBtn && !pdfBtn.dataset.bound) {
            pdfBtn.dataset.bound = "true";
            pdfBtn.addEventListener('click', () => {
                downloadSamplePDF(AppState.selectedSampleForRec.sample.sample_id);
            });
        }

    } catch (err) {
        showToast("Failed to load treatment recommendation", "error");
    }
}

function renderTreatmentHeader(sample, wqi, category) {
    document.getElementById('rec-sample-id').textContent = sample.sample_id || 'Sample';
    document.getElementById('rec-source-name').textContent = sample.source || 'General';
    document.getElementById('rec-wqi-score').textContent = `${wqi.wqi} (${wqi.status})`;
    document.getElementById('rec-category-label').textContent = category;
}

function renderContaminationRadar(profile) {
    const canvas = document.getElementById('rec-radar-chart');
    if (!canvas || !profile || !profile.parameters) return;

    if (AppState.charts['treatmentRadar']) {
        AppState.charts['treatmentRadar'].destroy();
    }

    const labels = profile.parameters.map(p => p.parameter.replace('_', ' '));
    const excessRatios = profile.parameters.map(p => p.excess_ratio);
    const standardLine = profile.parameters.map(() => 1.0); // Baseline limit

    const ctx = canvas.getContext('2d');
    AppState.charts['treatmentRadar'] = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Sample Excess vs Limit (Ratio)',
                    data: excessRatios,
                    borderColor: '#00f0ff',
                    backgroundColor: 'rgba(0, 240, 255, 0.25)',
                    pointBackgroundColor: '#00f0ff',
                    borderWidth: 2
                },
                {
                    label: 'Permissible Standard Limit (1.0x)',
                    data: standardLine,
                    borderColor: '#ff0055',
                    borderDash: [4, 4],
                    backgroundColor: 'transparent',
                    pointRadius: 0,
                    borderWidth: 1.5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: 'rgba(0, 240, 255, 0.12)' },
                    grid: { color: 'rgba(0, 240, 255, 0.1)' },
                    pointLabels: { color: '#9bb1d0', font: { size: 10 } },
                    ticks: { color: '#597399', backdropColor: 'transparent' }
                }
            },
            plugins: {
                legend: { labels: { color: '#f0f6fc' } }
            }
        }
    });
}

function renderTreatmentTrain(stages) {
    const container = document.getElementById('treatment-timeline-container');
    if (!container || !stages) return;

    container.innerHTML = '';
    for (const [key, stage] of Object.entries(stages)) {
        const step = document.createElement('div');
        step.className = 'stage-step';

        let listHtml = '';
        stage.units.forEach(u => {
            listHtml += `<li>${u}</li>`;
        });

        step.innerHTML = `
            <div class="stage-step-dot"></div>
            <div class="stage-title">${stage.title}</div>
            <ul class="stage-units-list">${listHtml}</ul>
        `;
        container.appendChild(step);
    }
}

function renderDosingSchedule(dosing) {
    document.getElementById('dose-pac').textContent = `${dosing.pac_dose_mg_l} mg/L`;
    document.getElementById('dose-alum').textContent = `${dosing.alum_alt_dose_mg_l} mg/L`;
    document.getElementById('dose-poly').textContent = `${dosing.polymer_dose_mg_l} mg/L`;
    document.getElementById('dose-uv').textContent = dosing.uv_dose;
    document.getElementById('dose-chlorine').textContent = dosing.chlorine_dose;
}

function renderReuseMatrix(matrix) {
    const tbody = document.getElementById('reuse-matrix-tbody');
    if (!tbody || !matrix) return;

    tbody.innerHTML = '';
    for (const [key, app] of Object.entries(matrix)) {
        const tr = document.createElement('tr');
        const badge = app.suitable ? 'badge-safe' : 'badge-warn';
        tr.innerHTML = `
            <td><strong>${app.title}</strong></td>
            <td><span class="param-badge ${badge}">${app.suitable ? 'Approved' : 'Restricted'}</span></td>
            <td>${app.status}</td>
            <td style="font-size:0.75rem; color:var(--text-muted);">${app.requirement}</td>
        `;
        tbody.appendChild(tr);
    }
}

function populateTreatmentSamplePicker(currentId) {
    const picker = document.getElementById('treatment-sample-picker');
    if (!picker || !AppState.samplesData || AppState.samplesData.length === 0) return;

    picker.innerHTML = '';
    AppState.samplesData.slice(0, 80).forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.sample_id;
        opt.textContent = `${s.sample_id} - ${s.source}`;
        if (s.sample_id === currentId) opt.selected = true;
        picker.appendChild(opt);
    });

    if (!picker.dataset.bound) {
        picker.dataset.bound = "true";
        picker.addEventListener('change', (e) => {
            loadTreatment(e.target.value);
        });
    }
}

// ==========================================
// 8. Laboratory Validation (Objective 3)
// ==========================================
async function loadValidation() {
    const algoSelect = document.getElementById('val-algo-select');
    const algo = algoSelect ? algoSelect.value : 'kmeans';

    try {
        const res = await fetch('/api/validation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ algorithm: algo })
        });
        const data = await res.json();
        AppState.validationData = data;

        // KPI Badges
        renderValidationKPIs(data.overall);

        // Confusion Matrix Heatmap
        renderConfusionMatrixGrid(data.confusion_matrix);

        // Per-Class Breakdown Table
        renderClassMetricsTable(data.class_breakdown);

        // Cluster Mapping text
        renderClusterMappingList(data.mapping);

        // Algorithm switcher
        if (algoSelect && !algoSelect.dataset.bound) {
            algoSelect.dataset.bound = "true";
            algoSelect.addEventListener('change', () => loadValidation());
        }

    } catch (err) {
        showToast("Failed to load laboratory validation", "error");
    }
}

function renderValidationKPIs(overall) {
    if (!overall) return;
    document.getElementById('val-kpi-acc').textContent = `${Math.round(overall.accuracy * 1000) / 10}%`;
    document.getElementById('val-kpi-prec').textContent = `${Math.round(overall.precision_macro * 1000) / 10}%`;
    document.getElementById('val-kpi-rec').textContent = `${Math.round(overall.recall_macro * 1000) / 10}%`;
    document.getElementById('val-kpi-f1').textContent = `${Math.round(overall.f1_macro * 1000) / 10}%`;
    document.getElementById('val-kpi-total').textContent = overall.total_samples;
}

function renderConfusionMatrixGrid(cm) {
    const container = document.getElementById('val-cm-container');
    if (!container || !cm) return;

    const labels = cm.labels;
    const matrix = cm.matrix;

    let html = `<div class="cm-grid">`;
    // Top-left blank
    html += `<div class="cm-header">Ground \\ Pred</div>`;
    labels.forEach(l => {
        html += `<div class="cm-header">${l.replace(' Contamination', '')}</div>`;
    });

    for (let i = 0; i < labels.length; i++) {
        html += `<div class="cm-row-label">${labels[i].replace(' Contamination', '')}</div>`;
        for (let j = 0; j < labels.length; j++) {
            const count = matrix[i][j];
            const isDiagonal = (i === j);

            // Calculate opacity based on row total
            const rowTotal = matrix[i].reduce((a, b) => a + b, 0);
            const intensity = rowTotal > 0 ? (count / rowTotal) : 0;

            let bgColor = isDiagonal
                ? `rgba(0, 240, 255, ${0.15 + intensity * 0.7})`
                : (count > 0 ? `rgba(255, 0, 85, ${0.15 + intensity * 0.6})` : 'rgba(8, 16, 36, 0.5)');

            let textColor = (count > 0 && isDiagonal) ? '#ffffff' : (count > 0 ? '#ff88aa' : 'var(--text-muted)');

            html += `
                <div class="cm-cell" style="background:${bgColor}; color:${textColor}; border: 1px solid rgba(0, 240, 255, 0.15);">
                    <span style="font-size:1.1rem;">${count}</span>
                    <span style="font-size:0.65rem; opacity:0.8;">${Math.round(intensity * 100)}%</span>
                </div>
            `;
        }
    }
    html += `</div>`;
    container.innerHTML = html;
}

function renderClassMetricsTable(breakdown) {
    const tbody = document.getElementById('val-classes-tbody');
    if (!tbody || !breakdown) return;

    tbody.innerHTML = '';
    breakdown.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${row.category}</strong></td>
            <td style="color:var(--emerald-safe); font-weight:700;">${row.true_positives}</td>
            <td style="color:var(--coral-danger);">${row.false_positives}</td>
            <td style="color:var(--amber-warning);">${row.false_negatives}</td>
            <td><strong>${Math.round(row.precision * 1000) / 10}%</strong></td>
            <td><strong>${Math.round(row.recall * 1000) / 10}%</strong></td>
            <td style="color:var(--cyan-primary); font-weight:700;">${Math.round(row.f1_score * 1000) / 10}%</td>
            <td>${row.support}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderClusterMappingList(mapping) {
    const el = document.getElementById('val-mapping-text');
    if (!el || !mapping) return;

    let items = [];
    for (const [cid, cat] of Object.entries(mapping)) {
        items.push(`Cluster ${cid} ➔ <strong>${cat}</strong>`);
    }
    el.innerHTML = items.join(' | ');
}

// ==========================================
// 9. History & Export View
// ==========================================
async function loadHistory() {
    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        AppState.historyData = data.history || [];

        const tbody = document.getElementById('history-data-tbody');
        if (!tbody) return;

        tbody.innerHTML = '';
        AppState.historyData.forEach(h => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${h.analysis_id}</strong></td>
                <td>${h.sample_id || 'N/A'}</td>
                <td>${h.analyzed_at}</td>
                <td>${h.wqi}</td>
                <td><span class="param-badge badge-safe">${h.mapped_category || h.contamination_level}</span></td>
                <td>${h.source || 'Manual'}</td>
                <td>
                    <button class="btn-outline" style="padding:3px 8px; font-size:0.75rem;" onclick="inspectSample('${h.sample_id}')">
                        Inspect
                    </button>
                    <button class="btn-cyber" style="padding:3px 8px; font-size:0.75rem;" onclick="downloadSamplePDF('${h.sample_id}')">
                        PDF
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

    } catch (err) {
        showToast("Failed to load analysis history", "error");
    }
}

// ==========================================
// Utility: Inspect Sample & PDF Download
// ==========================================
function inspectSample(sampleId) {
    loadView('treatment');
    loadTreatment(sampleId);
}

async function downloadSamplePDF(sampleId) {
    try {
        showToast(`Generating laboratory PDF certificate for ${sampleId}...`);
        const res = await fetch('/api/export/pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sample_id: sampleId })
        });
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `HydraSense_Analysis_${sampleId}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            showToast("PDF downloaded successfully!");
        } else {
            showToast("Failed to generate PDF", "error");
        }
    } catch (err) {
        showToast("Error downloading PDF", "error");
    }
}

function showSampleModal(sample, treatment, wqi) {
    const modal = document.getElementById('sample-result-modal');
    if (!modal) return;

    document.getElementById('modal-sample-id').textContent = sample.sample_id;
    document.getElementById('modal-wqi').textContent = `${wqi.wqi} (${wqi.status})`;
    document.getElementById('modal-category').textContent = treatment.category;
    document.getElementById('modal-pac-dose').textContent = `${treatment.chemical_dosing.pac_dose_mg_l} mg/L`;

    modal.classList.add('open');
}

function closeSampleModal() {
    const modal = document.getElementById('sample-result-modal');
    if (modal) modal.classList.remove('open');
}

// Toast notification helper
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const borderColor = type === 'error' ? 'var(--coral-danger)' : 'var(--cyan-primary)';
    toast.style.cssText = `
        background: rgba(8, 18, 42, 0.95);
        backdrop-filter: blur(12px);
        border: 1px solid ${borderColor};
        border-radius: var(--radius-sm);
        padding: 12px 18px;
        color: #ffffff;
        font-size: 0.85rem;
        box-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
        animation: fadeIn 0.3s ease;
        max-width: 320px;
    `;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.4s ease';
        setTimeout(() => toast.remove(), 400);
    }, 3500);
}
