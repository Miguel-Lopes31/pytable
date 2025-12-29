document.addEventListener('DOMContentLoaded', () => {
    const dataEl = document.getElementById('game-data');
    const tableConfig = dataEl.dataset.tables;
    const timeLimitStr = dataEl.dataset.time;
    const mode = dataEl.dataset.mode || 'normal';
    const operationMode = dataEl.dataset.operationMode || 'multiply';
    const globalTimeLimit = parseInt(dataEl.dataset.globalTime) || 60;

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
    const globalTimerDisplay = document.getElementById('global-timer-display');
    const globalTimerText = document.getElementById('global-timer-text');

    let deck = [];
    let gameState = {
        score: 0,
        totalQuestions: 0,
        currentQuestion: null,
        details: [],
        active: false,
        timerInterval: null,
        globalTimerInterval: null,
        globalTimeRemaining: globalTimeLimit
    };

    // Initialize Deck (No repeats logic)
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
                if (operationMode === 'divide') {
                    // Division: (base * i) / base = i
                    // Example: Table 5, i=3 -> 15 / 5 = 3
                    deck.push({
                        base: base,
                        mult: i,
                        answer: i,
                        operation: 'divide'
                    });
                } else {
                    // Multiplication: base * i = ?
                    deck.push({
                        base: base,
                        mult: i,
                        answer: base * i,
                        operation: 'multiply'
                    });
                }
            }
        });

        // Shuffle Deck
        for (let i = deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [deck[i], deck[j]] = [deck[j], deck[i]];
        }
    }

    // Format time as MM:SS
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // Start Global Timer for Time Attack mode
    function startGlobalTimer() {
        if (mode !== 'time_attack') return;

        globalTimerDisplay.style.display = 'flex';
        gameState.globalTimeRemaining = globalTimeLimit;
        globalTimerText.textContent = formatTime(gameState.globalTimeRemaining);

        // Start clock ticking sound
        if (typeof soundManager !== 'undefined') {
            soundManager.startClockTicking(() => gameState.globalTimeRemaining);
        }

        gameState.globalTimerInterval = setInterval(() => {
            gameState.globalTimeRemaining--;
            globalTimerText.textContent = formatTime(gameState.globalTimeRemaining);

            // Add warning class when time is low
            if (gameState.globalTimeRemaining <= 10) {
                globalTimerDisplay.classList.add('warning');
            }

            if (gameState.globalTimeRemaining <= 0) {
                clearInterval(gameState.globalTimerInterval);
                if (typeof soundManager !== 'undefined') {
                    soundManager.stopClockTicking();
                    soundManager.playAlarm();
                }
                endGame();
            }
        }, 1000);
    }

    // Start Game - Refactored for Async
    const homeworkId = dataEl.dataset.homeworkId;

    if (mode === 'homework') {
        initDeck();
        const scoreDisplay = document.getElementById('score-display');
        scoreDisplay.innerHTML = '📝 Dever de Casa';
        scoreDisplay.style.color = '#4ecdc4';
        startStartCountdown();
    } else if (mode === 'time_attack') {
        initDeck();
        scoreEl.innerHTML = `⏱️ Score: 0`;
        scoreEl.style.color = '#ffaa00';
        startStartCountdown();
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

        // Play initial countdown beep
        if (typeof soundManager !== 'undefined') {
            soundManager.init();
            soundManager.playCountdown(false);
        }

        const timer = setInterval(() => {
            count--;
            if (count > 0) {
                countdownEl.textContent = count;
                // Play countdown beep (final beep is different)
                if (typeof soundManager !== 'undefined') {
                    soundManager.playCountdown(count === 1);
                }
            } else {
                clearInterval(timer);
                overlay.style.display = 'none';
                gameState.active = true;

                // Start mode-specific sounds
                if (typeof soundManager !== 'undefined') {
                    if (mode === 'zombie') {
                        soundManager.startZombieAmbient();
                    }
                    // Normal and smart modes: no ambient music, just feedback sounds
                }

                startGlobalTimer();
                nextQuestion();
            }
        }, 1000);
    }

    function nextQuestion() {
        if (!gameState.active) return;

        // Stop specific question timer if running
        if (gameState.timerInterval) clearInterval(gameState.timerInterval);

        // In time_attack mode, refill deck if empty
        if (mode === 'time_attack' && deck.length === 0) {
            initDeck();
        }

        if (deck.length === 0) {
            endGame(true);
            return;
        }

        // Pop from deck for non-repeating
        gameState.currentQuestion = deck.pop();

        // Update UI
        if (operationMode === 'divide') {
            // Display: (base * mult) ÷ base = ?
            const dividend = gameState.currentQuestion.base * gameState.currentQuestion.mult;
            questionEl.textContent = `${dividend} ÷ ${gameState.currentQuestion.base} = ?`;
        } else {
            questionEl.textContent = `${gameState.currentQuestion.base} × ${gameState.currentQuestion.mult} = ?`;
        }

        questionEl.classList.remove('visible');
        void questionEl.offsetWidth; // trigger reflow
        questionEl.classList.add('visible');

        generateOptions(gameState.currentQuestion.answer);

        // Start Question Timer (not for time_attack mode - it uses global timer)
        if (mode !== 'time_attack') {
            startQuestionTimer();
        }
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

            // For division (answers 1-10), ensure 1-10 range mostly, but definitely > 0
            if (operationMode === 'divide') {
                if (val <= 0) val = 1 + Math.abs(val); // Ensure positive
                // Try to keep within 1-20 reasonable range for division results
                if (val > 20) val = 20;
            } else {
                if (val < 0) val = Math.abs(val);
            }
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

            // Play correct sound
            if (typeof soundManager !== 'undefined') {
                soundManager.playCorrect();
            }

            if (mode === 'time_attack') {
                scoreEl.textContent = `⏱️ Score: ${gameState.score}`;
            } else if (mode === 'zombie') {
                scoreEl.textContent = `🧟 Score: ${gameState.score}`;
            } else {
                scoreEl.textContent = `Pontos: ${gameState.score}`;
            }

            setTimeout(nextQuestion, mode === 'time_attack' ? 200 : 500);
        } else {
            if (btnElement) {
                btnElement.classList.add('shake');
            } else {
                // Timeout or other error
                questionEl.classList.add('shake');
            }

            // Play incorrect sound
            if (typeof soundManager !== 'undefined') {
                soundManager.playIncorrect();
            }

            // Zombie Mode: Instant Death
            if (mode === 'zombie') {
                setTimeout(endGame, 1000);
            } else {
                setTimeout(nextQuestion, mode === 'time_attack' ? 300 : 600);
            }
        }
    }

    function endGame() {
        gameState.active = false;

        // Clear all timers
        if (gameState.timerInterval) clearInterval(gameState.timerInterval);
        if (gameState.globalTimerInterval) clearInterval(gameState.globalTimerInterval);

        // Stop all sounds and play end sound
        if (typeof soundManager !== 'undefined') {
            soundManager.stopAll();

            // Determine which end sound to play
            const isVictory = mode === 'zombie' ? gameState.score === 100 : gameState.score > 0;
            if (isVictory) {
                soundManager.playVictory();
            } else {
                soundManager.playGameOver();
            }
        }

        overlay.style.display = 'flex';

        let title = 'Fim de Jogo!';
        let message = `Pontuação: ${gameState.score} / ${gameState.totalQuestions}`;

        if (mode === 'time_attack') {
            title = '⏱️ Tempo Esgotado!';
            message = `
                <div style="font-size: 3rem; margin-bottom: 15px; color: #ffaa00;">🏆</div>
                <p style="font-size: 2rem; font-weight: bold; color: #ffaa00; margin-bottom: 10px;">${gameState.score}</p>
                <p style="color: #888;">perguntas corretas em ${globalTimeLimit} segundos</p>
            `;
        } else if (mode === 'zombie') {
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

    function saveSession() {
        if (gameState.score === 0 && gameState.totalQuestions === 0) return Promise.resolve();

        return fetch('/api/submit_game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                details: gameState.details,
                mode: mode,
                operation: operationMode,
                homework_id: dataEl.dataset.homeworkId,
                score: gameState.score,
                total_questions: gameState.totalQuestions
            })
        }).then(res => res.json())
            .then(data => {
                console.log('Session saved', data);
            })
            .catch(err => console.error('Error saving session:', err));
    }

    window.saveAndExit = function () {
        const btn = document.querySelector('.auth-box .btn');
        if (btn) btn.textContent = 'Salvando...';

        saveSession().then(() => {
            window.location.href = '/dashboard';
        });
    };
});
