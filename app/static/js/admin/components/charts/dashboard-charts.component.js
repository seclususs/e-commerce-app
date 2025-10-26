import { createSalesChart } from './sales-chart.component.js';
import { createTopProductsChart } from './top-products-chart.component.js';
import { createLowStockChart } from './low-stock-chart.component.js';


let chartInstances = {};

export function destroyCharts() {
    Object.values(chartInstances).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    chartInstances = {};
}


export function updateAllCharts(stats) {
    destroyCharts();

    createSalesChart(stats, chartInstances);
    createTopProductsChart(stats, chartInstances);
    createLowStockChart(stats, chartInstances);
}


export function initDashboardCharts() {
    const salesCtx = document.getElementById('salesChart');
    const topProductsCtx = document.getElementById('topProductsChart');
    const lowStockCtx = document.getElementById('lowStockChart');

    if (!salesCtx || !topProductsCtx || !lowStockCtx) return;

    try {
        const stats = {
            sales_chart_data: {
                labels: JSON.parse(salesCtx.dataset.labels || '[]'),
                data: JSON.parse(salesCtx.dataset.data || '[]')
            },
            top_products_chart: {
                labels: JSON.parse(topProductsCtx.dataset.labels || '[]'),
                data: JSON.parse(topProductsCtx.dataset.data || '[]')
            },
            low_stock_chart: {
                labels: JSON.parse(lowStockCtx.dataset.labels || '[]'),
                data: JSON.parse(lowStockCtx.dataset.data || '[]')
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