let chartInstances = {};

function getCssVar(varName) {
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

export function destroyCharts() {
    Object.values(chartInstances).forEach(chart => chart.destroy());
    chartInstances = {};
}

function createSalesChart(stats) {
    const salesCtx = document.getElementById('salesChart');
    if (salesCtx) {
        const chartData = stats.sales_chart_data;
        const salesChartOptions = commonChartOptions();
        salesChartOptions.scales.y.ticks.callback = (value) => 'Rp ' + new Intl.NumberFormat('id-ID').format(value);
        salesChartOptions.plugins.tooltip.callbacks = {
            label: (context) => `Penjualan: ${new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(context.parsed.y)}`
        };

        chartInstances.sales = new Chart(salesCtx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Total Penjualan',
                    data: chartData.data,
                    backgroundColor: 'rgba(59, 130, 246, 0.5)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 2,
                    borderRadius: 5,
                    hoverBackgroundColor: 'rgba(59, 130, 246, 0.8)'
                }]
            },
            options: salesChartOptions
        });
    }
}

function createTopProductsChart(stats) {
    const topProductsCtx = document.getElementById('topProductsChart');
    if (topProductsCtx) {
        const chartData = stats.top_products_chart;
        const topProductsOptions = commonChartOptions();
        topProductsOptions.scales.y.beginAtZero = true;
        topProductsOptions.scales.y.ticks.stepSize = 1;
        topProductsOptions.plugins.tooltip.callbacks = {
            label: (context) => `Terjual: ${context.parsed.y} unit`
        };

        chartInstances.topProducts = new Chart(topProductsCtx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Jumlah Terjual',
                    data: chartData.data,
                    backgroundColor: ['rgba(16, 185, 129, 0.6)', 'rgba(59, 130, 246, 0.6)', 'rgba(139, 92, 246, 0.6)', 'rgba(239, 68, 68, 0.6)', 'rgba(245, 158, 11, 0.6)'],
                    borderColor: ['#10b981', '#3b82f6', '#8b5cf6', '#ef4444', '#f59e0b'],
                    borderWidth: 1,
                    borderRadius: 5
                }]
            },
            options: topProductsOptions
        });
    }
}

function createLowStockChart(stats) {
    const lowStockCtx = document.getElementById('lowStockChart');
    if (lowStockCtx) {
        const chartData = stats.low_stock_chart;
        const lowStockOptions = commonChartOptions();
        lowStockOptions.indexAxis = 'y';
        lowStockOptions.scales.x.beginAtZero = true;
        lowStockOptions.scales.x.ticks.stepSize = 1;
        lowStockOptions.plugins.tooltip.callbacks = {
            label: (context) => `Sisa Stok: ${context.parsed.x}`
        };

        chartInstances.lowStock = new Chart(lowStockCtx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Sisa Stok',
                    data: chartData.data,
                    backgroundColor: 'rgba(245, 158, 11, 0.6)',
                    borderColor: 'rgba(245, 158, 11, 1)',
                    borderWidth: 1,
                    borderRadius: 5
                }]
            },
            options: lowStockOptions
        });
    }
}

export function updateAllCharts(stats) {
    destroyCharts();
    createSalesChart(stats);
    createTopProductsChart(stats);
    createLowStockChart(stats);
}

const commonChartOptions = (isDonut = false) => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: isDonut,
            position: 'bottom',
            labels: { color: getCssVar('--color-text-secondary') }
        },
        tooltip: {
            backgroundColor: getCssVar('--color-background-surface'),
            titleColor: getCssVar('--color-text-primary'),
            bodyColor: getCssVar('--color-text-secondary'),
            titleFont: { size: 14, weight: 'bold' },
            bodyFont: { size: 12 },
            padding: 10,
            cornerRadius: 5,
            displayColors: false,
            borderColor: getCssVar('--color-border-default'),
            borderWidth: 1,
        }
    },
    scales: {
        y: {
            grid: { color: getCssVar('--color-grid-line') },
            ticks: { color: getCssVar('--color-text-tertiary') }
        },
        x: {
            grid: { display: false },
            ticks: { color: getCssVar('--color-text-tertiary') }
        }
    }
});

export function initDashboardCharts() {
    const salesCtx = document.getElementById('salesChart');
    if (!salesCtx) return;

    try {
        const stats = {
            sales_chart_data: {
                labels: JSON.parse(salesCtx.dataset.labels),
                data: JSON.parse(salesCtx.dataset.data)
            },
            top_products_chart: {
                labels: JSON.parse(document.getElementById('topProductsChart').dataset.labels),
                data: JSON.parse(document.getElementById('topProductsChart').dataset.data)
            },
            low_stock_chart: {
                labels: JSON.parse(document.getElementById('lowStockChart').dataset.labels),
                data: JSON.parse(document.getElementById('lowStockChart').dataset.data)
            }
        };
        updateAllCharts(stats);
    } catch (e) {
        console.error("Gagal memuat data chart awal:", e);
    }
}

window.addEventListener('themeChanged', () => {
    if (document.getElementById('salesChart')) {
        initDashboardCharts();
    }
});