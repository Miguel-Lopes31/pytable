document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            renderDashboard(data);
        });
});

function renderDashboard(data) {
    const labels = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

    // Calculate Summaries
    let totalAttempts = 0;
    let totalCorrect = 0;
    let accuracySum = 0;
    let tablesPracticedCount = 0;

    const accuracyData = labels.map(num => {
        const d = data[num];
        if (d && d.total > 0) {
            totalAttempts += d.total;
            totalCorrect += d.correct;
            accuracySum += d.rate;
            tablesPracticedCount++;
            return d.rate;
        }
        return 0;
    });

    const volumeData = labels.map(num => {
        const d = data[num];
        return d ? d.total : 0;
    });

    // Update Summary Cards (Mocking total games roughly or just using available stats)
    // Since API currently returns stats grouped by number, we can't easily get "Total Games" without changing API.
    // I'll stick to what we have or infer.

    document.getElementById('total-score').textContent = totalCorrect;
    document.getElementById('total-games').textContent = totalAttempts; // Actually attempts
    document.querySelector('#total-games + span').textContent = "Total de Tentativas";

    const avgAcc = tablesPracticedCount > 0 ? (accuracySum / tablesPracticedCount).toFixed(1) : 0;
    document.getElementById('avg-accuracy').textContent = avgAcc + '%';


    // Chart 1: Accuracy (Bar)
    const ctx = document.getElementById('performanceChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Acertos (%)',
                data: accuracyData,
                backgroundColor: accuracyData.map(v => v > 80 ? '#00e676' : (v > 50 ? '#ffea00' : '#ff1744')),
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: '#333' },
                    ticks: { color: '#aaa' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#aaa' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });

    // Chart 2: Volume (Line/Area)
    const ctx2 = document.getElementById('volumeChart').getContext('2d');
    new Chart(ctx2, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Tentativas',
                data: volumeData,
                borderColor: '#2962ff',
                backgroundColor: 'rgba(41, 98, 255, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: '#333' },
                    ticks: { color: '#aaa' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#aaa' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}
