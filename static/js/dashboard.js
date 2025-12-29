document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/stats')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            renderDashboard(data);
        })
        .catch(err => {
            console.error('Error loading stats:', err);
            document.querySelector('.container').innerHTML += `<div class="alert alert-error">Erro ao carregar estatísticas. Verifique se você rodou a migração do banco de dados (SQL).</div>`;
        });

    // Fetch and render heatmap
    fetch('/api/heatmap')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            renderHeatmap(data);
        })
        .catch(err => console.error('Error loading heatmap:', err));
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
                borderColor: '#e11d48',
                backgroundColor: 'rgba(225, 29, 72, 0.1)',
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

// Render the Error Heatmap
function renderHeatmap(data) {
    const grid = document.getElementById('heatmap-grid');
    if (!grid) return;

    grid.innerHTML = '';

    // Generate 10 rows (for bases 1-10)
    for (let base = 1; base <= 10; base++) {
        const row = document.createElement('div');
        row.className = 'heatmap-row';

        // Row label
        const label = document.createElement('div');
        label.className = 'heatmap-cell heatmap-label';
        label.textContent = base;
        row.appendChild(label);

        // Cells for each multiplier
        for (let mult = 1; mult <= 10; mult++) {
            const key = `${base}x${mult}`;
            const cellData = data[key];

            const cell = document.createElement('div');
            cell.className = 'heatmap-cell';

            // Display the answer
            const answer = base * mult;
            cell.textContent = answer;

            if (cellData && cellData.total > 0) {
                const rate = cellData.rate;

                // Color based on accuracy
                if (rate >= 80) {
                    cell.classList.add('high');
                } else if (rate >= 50) {
                    cell.classList.add('medium');
                } else {
                    cell.classList.add('low');
                }

                // Tooltip/title with details
                cell.title = `${base} × ${mult} = ${answer}\nPrecisão: ${rate}%\nAcertos: ${cellData.correct}/${cellData.total}\nErros: ${cellData.errors}`;

                // Click handler
                cell.onclick = () => {
                    if (typeof ui !== 'undefined') {
                        ui.alert(
                            `Precisão: ${rate}%\nAcertos: ${cellData.correct} de ${cellData.total}\nErros: ${cellData.errors}`,
                            `${base} × ${mult} = ${answer}`
                        );
                    }
                };
            } else {
                cell.classList.add('no-data');
                cell.title = `${base} × ${mult} = ${answer}\nSem dados`;
            }

            row.appendChild(cell);
        }

        grid.appendChild(row);
    }
}
