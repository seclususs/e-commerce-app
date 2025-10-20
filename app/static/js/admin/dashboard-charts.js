/**
 * Menginisialisasi semua chart di halaman dashboard admin.
 * Membaca data dari atribut data-* pada elemen canvas.
 */
export function initDashboardCharts() {
    // Opsi umum untuk semua chart agar konsisten
    const commonChartOptions = (isDonut = false) => ({
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: isDonut,
                position: 'bottom',
                labels: { color: '#94a3b8' }
            },
            tooltip: {
                backgroundColor: '#1e293b',
                titleFont: { size: 14, weight: 'bold' },
                bodyFont: { size: 12 },
                padding: 10,
                cornerRadius: 5,
                displayColors: false,
            }
        },
        scales: {
            y: {
                grid: { color: 'rgba(203, 213, 225, 0.1)' },
                ticks: { color: '#94a3b8' }
            },
            x: {
                grid: { display: false },
                ticks: { color: '#94a3b8' }
            }
        }
    });

    // Grafik Penjualan Harian (Bar Chart)
    const salesCtx = document.getElementById('salesChart');
    if (salesCtx) {
        try {
            const chartLabels = JSON.parse(salesCtx.dataset.labels);
            const chartData = JSON.parse(salesCtx.dataset.data);

            const salesChartOptions = commonChartOptions();
            salesChartOptions.scales.y.ticks.callback = (value) => 'Rp ' + new Intl.NumberFormat('id-ID').format(value);
            salesChartOptions.plugins.tooltip.callbacks = {
                label: (context) => `Penjualan: ${new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(context.parsed.y)}`
            };

            new Chart(salesCtx, {
                type: 'bar',
                data: {
                    labels: chartLabels,
                    datasets: [{
                        label: 'Total Penjualan',
                        data: chartData,
                        backgroundColor: 'rgba(59, 130, 246, 0.5)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 2,
                        borderRadius: 5,
                        hoverBackgroundColor: 'rgba(59, 130, 246, 0.8)'
                    }]
                },
                options: salesChartOptions
            });
        } catch (e) {
            console.error("Gagal memuat Sales Chart:", e);
            salesCtx.parentElement.innerHTML = '<p style="color: #94a3b8; text-align: center;">Gagal memuat data grafik penjualan.</p>';
        }
    }

    // Grafik Produk Terlaris (Bar Chart)
    const topProductsCtx = document.getElementById('topProductsChart');
    if (topProductsCtx) {
        try {
            const topProductsLabels = JSON.parse(topProductsCtx.dataset.labels);
            const topProductsData = JSON.parse(topProductsCtx.dataset.data);

            const topProductsOptions = commonChartOptions();
            topProductsOptions.scales.y.beginAtZero = true;
            topProductsOptions.scales.y.ticks.stepSize = 1;
             topProductsOptions.plugins.tooltip.callbacks = {
                label: (context) => `Terjual: ${context.parsed.y} unit`
            };

            new Chart(topProductsCtx, {
                type: 'bar',
                data: {
                    labels: topProductsLabels,
                    datasets: [{
                        label: 'Jumlah Terjual',
                        data: topProductsData,
                        backgroundColor: [
                            'rgba(16, 185, 129, 0.6)',
                            'rgba(59, 130, 246, 0.6)',
                            'rgba(139, 92, 246, 0.6)',
                            'rgba(239, 68, 68, 0.6)',
                            'rgba(245, 158, 11, 0.6)'
                        ],
                        borderColor: [
                            '#10b981', '#3b82f6', '#8b5cf6', '#ef4444', '#f59e0b'
                        ],
                        borderWidth: 1,
                        borderRadius: 5
                    }]
                },
                options: topProductsOptions
            });
        } catch (e) {
            console.error("Gagal memuat Top Products Chart:", e);
            topProductsCtx.parentElement.innerHTML = '<p style="color: #94a3b8; text-align: center;">Gagal memuat data produk terlaris.</p>';
        }
    }

    // Grafik Stok Segera Habis (Horizontal Bar Chart)
    const lowStockCtx = document.getElementById('lowStockChart');
    if (lowStockCtx) {
        try {
            const lowStockLabels = JSON.parse(lowStockCtx.dataset.labels);
            const lowStockData = JSON.parse(lowStockCtx.dataset.data);

            const lowStockOptions = commonChartOptions();
            lowStockOptions.indexAxis = 'y';
            lowStockOptions.scales.x.beginAtZero = true;
            lowStockOptions.scales.x.ticks.stepSize = 1;
            lowStockOptions.plugins.tooltip.callbacks = {
                label: (context) => `Sisa Stok: ${context.parsed.x}`
            };

            new Chart(lowStockCtx, {
                type: 'bar',
                data: {
                    labels: lowStockLabels,
                    datasets: [{
                        label: 'Sisa Stok',
                        data: lowStockData,
                        backgroundColor: 'rgba(245, 158, 11, 0.6)',
                        borderColor: 'rgba(245, 158, 11, 1)',
                        borderWidth: 1,
                        borderRadius: 5
                    }]
                },
                options: lowStockOptions
            });
        } catch (e) {
            console.error("Gagal memuat Low Stock Chart:", e);
            lowStockCtx.parentElement.innerHTML = '<p style="color: #94a3b8; text-align: center;">Gagal memuat data stok produk.</p>';
        }
    }
}