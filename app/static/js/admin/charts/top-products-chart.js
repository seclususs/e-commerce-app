import { commonChartOptions } from './chart-utils.js';


export function createTopProductsChart(stats, chartInstances) {
    const topProductsCtx = document.getElementById('topProductsChart');
    if (!topProductsCtx) return null;

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
    return chartInstances.topProducts;
}