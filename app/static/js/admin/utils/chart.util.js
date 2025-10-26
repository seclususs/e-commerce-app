export function getCssVar(varName) {
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}


export const commonChartOptions = (isDonut = false) => ({
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