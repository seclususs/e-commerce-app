import { commonChartOptions } from './chart-utils.js';


export function createLowStockChart(stats, chartInstances) {
    const lowStockCtx = document.getElementById('lowStockChart');
    if (!lowStockCtx) return null;

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
    return chartInstances.lowStock;
}