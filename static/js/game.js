document.addEventListener('DOMContentLoaded', () => {
    const dataEl = document.getElementById('game-data');
    const tableConfig = dataEl.dataset.tables;
    const timeLimitStr = dataEl.dataset.time;
    const mode = dataEl.dataset.mode || 'normal';

    // Zombie Mode overrides
    let timeLimit = parseInt(timeLimitStr) || 5;
    if (mode === 'zombie') {
        timeLimit = 5;
    }

    const questionEl = document.getElementById('question');
    const optionsContainer = document.getElementById('options-container');
    const overlay = document.getElementById('overlay');
    const countdownEl = document.getElementById('countdown');
    const scoreEl = document.getElementById('score-display');
    const progressBar = document.getElementById('progress-bar');

    let deck = [];
    let gameState = {
        score: 0,
        totalQuestions: 0,
        currentQuestion: null,
        details: [],
        active: false,
        timerInterval: null
    };

    // Initialize Deck (No repeats logic)
    // Tables selected: e.g. "2,3" -> Deck: 2x1...2x10, 3x1...3x10
    function initDeck() {
        let tables = [];

        if (mode === 'zombie' || mode === 'time_attack') {
            tables = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
        } else if (tableConfig.toLowerCase() === 'all') {
            tables = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
        } else {
            tables = tableConfig.split(',').map(Number);
        }

        tables.forEach(base => {
            for (let i = 1; i <= 10; i++) {
                deck.push({ base: base, mult: i, answer: base * i });
            }
        });

        // Shuffle Deck
        for (let i = deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [deck[i], deck[j]] = [deck[j], deck[i]];
        }
    }

    // Start Game
    // Start Game - Refactored for Async
    if (mode === 'smart') {
        const scoreDisplay = document.getElementById('score-display');
        scoreDisplay.innerHTML = '🧠 Carregando seus erros...';

        // Fetch smart deck
        fetch('/api/smart_deck')
            .then(r => r.json())
            .then(data => {
                deck = data;
                scoreDisplay.innerHTML = '🧠 Treino Inteligente';
                scoreDisplay.style.color = '#9b59b6';
                startStartCountdown();
            })
            .catch(err => {
                console.error(err);
                alert("Erro ao carregar treino inteligente. Voltando ao modo normal.");
                // Fallback
                mode = 'normal';
                initDeck();
                startStartCountdown();
            });

    } else {
        initDeck();
        if (mode === 'zombie') {
            scoreEl.innerHTML = '🧟 ZOMBIE MODE <br> Survive!';
            scoreEl.style.color = '#50aa50';
        }
        startStartCountdown();
    }

    function startStartCountdown() {
        let count = 5;
        countdownEl.textContent = count;

        const timer = setInterval(() => {
            count--;
            if (count > 0) {
                countdownEl.textContent = count;
            } else {
                clearInterval(timer);
                overlay.style.display = 'none';
                gameState.active = true;
                nextQuestion();
            }
        }, 1000);
    }

    function nextQuestion() {
        if (!gameState.active) return;

        // Stop specific question timer if running
        if (gameState.timerInterval) clearInterval(gameState.timerInterval);

        if (deck.length === 0) {
            // If smart mode, maybe loop again? Or just end? Let's end for now as it's a "set" of training.
            endGame(true);
            return;
        }

        // Pop from deck for non-repeating
        gameState.currentQuestion = deck.pop();

        // Update UI
        questionEl.textContent = `${gameState.currentQuestion.base} x ${gameState.currentQuestion.mult} = ?`;
        questionEl.classList.remove('visible');
        void questionEl.offsetWidth; // trigger reflow
        questionEl.classList.add('visible');

        generateOptions(gameState.currentQuestion.answer);

        // Start Question Timer
        startQuestionTimer();
    }

    function startQuestionTimer() {
        let timeLeft = timeLimit;
        progressBar.style.width = '100%';
        progressBar.style.background = 'var(--success)';

        // Update frequently for smooth bar
        const totalMs = timeLimit * 1000;
        const intervalMs = 100;
        let elapsed = 0;

        gameState.timerInterval = setInterval(() => {
            elapsed += intervalMs;
            timeLeft = timeLimit - (elapsed / 1000);

            const pct = 100 - ((elapsed / totalMs) * 100);
            progressBar.style.width = `${pct}%`;

            // Color change
            if (pct < 30) progressBar.style.background = 'var(--danger)';
            else if (pct < 60) progressBar.style.background = '#ffd700';

            if (elapsed >= totalMs) {
                clearInterval(gameState.timerInterval);
                timeExpired();
            }
        }, intervalMs);
    }

    function timeExpired() {
        handleAnswer(null, null, true); // True for timeout
    }

    function generateOptions(correctAnswer) {
        optionsContainer.innerHTML = '';

        let options = new Set([correctAnswer]);
        while (options.size < 4) {
            let offset = Math.floor(Math.random() * 10) - 5;
            if (offset === 0) offset = 1;
            let val = correctAnswer + offset;
            if (val < 0) val = Math.abs(val);
            options.add(val);
        }

        const optionsArray = Array.from(options).sort(() => Math.random() - 0.5);

        optionsArray.forEach(val => {
            const btn = document.createElement('div');
            btn.className = 'option-btn';
            btn.textContent = val;
            btn.onclick = () => handleAnswer(val, btn);
            optionsContainer.appendChild(btn);
        });
    }

    function handleAnswer(val, btnElement, timeout = false) {
        if (!gameState.active && !timeout) return;
        if (gameState.timerInterval) clearInterval(gameState.timerInterval); // Stop timer immediately

        let isCorrect = false;
        if (!timeout) {
            isCorrect = (val === gameState.currentQuestion.answer);
        }

        // Record Stat
        gameState.details.push({
            base: gameState.currentQuestion.base,
            mult: gameState.currentQuestion.mult,
            correct: isCorrect
        });

        gameState.totalQuestions++;

        if (isCorrect) {
            gameState.score++;
            if (btnElement) btnElement.classList.add('correct-anim');
            scoreEl.textContent = mode === 'zombie' ? `🧟 Score: ${gameState.score}` : `Pontos: ${gameState.score}`;
            setTimeout(nextQuestion, 500);
        } else {
            if (btnElement) {
                btnElement.classList.add('shake');
            } else {
                // Timeout or other error
                questionEl.classList.add('shake');
            }

            // Zombie Mode: Instant Death
            if (mode === 'zombie') {
                setTimeout(endGame, 1000);
            } else {
                setTimeout(nextQuestion, 600);
            }
        }
    }

    function endGame() {
        gameState.active = false;
        overlay.style.display = 'flex';

        let title = 'Fim de Jogo!';
        let message = `Pontuação: ${gameState.score} / ${gameState.totalQuestions}`;

        if (mode === 'zombie') {
            if (gameState.score === 100) { // 10x10 tables = 100 questions
                title = '🧟 VICTORY! 🧟';
                message = '<p style="color: #50aa50; font-size: 1.2rem; font-weight: bold;">VOCÊ SOBREVIVEU AO APOCALIPSE!</p><p>Você ganhou o emblema Zumbi!</p>';
            } else {
                title = '🧟 GAME OVER 🧟';
                message = `<p style="color: var(--danger);">Os zumbis te pegaram!</p><p>Você sobreviveu por ${gameState.score} rodadas.</p>`;
            }
        }

        overlay.innerHTML = `
            <div class="auth-box">
                <h2>${title}</h2>
                <div>${message}</div>
                <div style="margin-top: 20px;">
                    <button class="btn" onclick="saveAndExit()">Finalizar</button>
                    <button class="btn" style="background: #333; margin-top: 10px;" onclick="window.location.reload()">Jogar Novamente</button>
                </div>
            </div>
        `;
    }

    window.saveAndExit = function () {
        fetch('/api/submit_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tables: tableConfig, // Will serve as record, even if mode overridden
                mode: mode, // SEND MODE TO SERVER
                score: gameState.score,
                total_questions: gameState.totalQuestions,
                details: gameState.details
            })
        }).then(res => res.json())
            .then(data => {
                window.location.href = '/dashboard';
            });
    };
});
