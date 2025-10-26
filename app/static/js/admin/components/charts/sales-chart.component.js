import { commonChartOptions } from '../../utils/chart.util.js';


export function createSalesChart(stats, chartInstances) {
    const salesCtx = document.getElementById('salesChart');
    if (!salesCtx) return null;

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
    return chartInstances.sales;
}