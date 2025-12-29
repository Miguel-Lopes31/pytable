/**
 * Pytable Audio Manager
 * Uses Web Audio API for sound synthesis - no external files needed
 */

class SoundManager {
    constructor() {
        this.audioContext = null;
        this.muted = localStorage.getItem('pytable_muted') === 'true';
        this.masterVolume = 0.3; // 30% max volume
        this.ambientNode = null;
        this.ambientGain = null;
        this.tickInterval = null;
        this.initialized = false;
    }

    // Initialize audio context (must be called after user interaction)
    init() {
        if (this.initialized) return;

        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.initialized = true;
            console.log('🔊 Audio system initialized');
        } catch (e) {
            console.warn('Audio not supported:', e);
        }
    }

    // Ensure context is running (browsers pause it sometimes)
    ensureContext() {
        if (!this.audioContext) this.init();
        if (this.audioContext && this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
    }

    // Toggle mute
    toggleMute() {
        this.muted = !this.muted;
        localStorage.setItem('pytable_muted', this.muted);

        // Stop ambient if muting
        if (this.muted) {
            this.stopAmbient();
        }

        return this.muted;
    }

    isMuted() {
        return this.muted;
    }

    // ========== SOUND EFFECTS ==========

    // Correct answer - pleasant rising chime
    playCorrect() {
        if (this.muted || !this.audioContext) return;
        this.ensureContext();

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        // Two-note ascending chime
        [523.25, 659.25].forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = 'sine';
            osc.frequency.value = freq;

            gain.gain.setValueAtTime(0, now + i * 0.08);
            gain.gain.linearRampToValueAtTime(this.masterVolume * 0.4, now + i * 0.08 + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.08 + 0.3);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start(now + i * 0.08);
            osc.stop(now + i * 0.08 + 0.3);
        });
    }

    // Incorrect answer - soft low buzz
    playIncorrect() {
        if (this.muted || !this.audioContext) return;
        this.ensureContext();

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sawtooth';
        osc.frequency.value = 150;

        gain.gain.setValueAtTime(this.masterVolume * 0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + 0.25);
    }

    // Clock tick
    playTick(fast = false) {
        if (this.muted || !this.audioContext) return;
        this.ensureContext();

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'square';
        osc.frequency.value = fast ? 1200 : 800;

        const vol = fast ? this.masterVolume * 0.25 : this.masterVolume * 0.15;
        gain.gain.setValueAtTime(vol, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + 0.05);
    }

    // Alarm (time's up)
    playAlarm() {
        if (this.muted || !this.audioContext) return;
        this.ensureContext();

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        // Three descending beeps
        [880, 660, 440].forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = 'square';
            osc.frequency.value = freq;

            gain.gain.setValueAtTime(this.masterVolume * 0.3, now + i * 0.15);
            gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.15 + 0.12);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start(now + i * 0.15);
            osc.stop(now + i * 0.15 + 0.15);
        });
    }

    // Victory fanfare
    playVictory() {
        if (this.muted || !this.audioContext) return;
        this.ensureContext();

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        // Ascending arpeggio
        const notes = [523.25, 659.25, 783.99, 1046.50];
        notes.forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = 'sine';
            osc.frequency.value = freq;

            gain.gain.setValueAtTime(0, now + i * 0.12);
            gain.gain.linearRampToValueAtTime(this.masterVolume * 0.35, now + i * 0.12 + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.12 + 0.4);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start(now + i * 0.12);
            osc.stop(now + i * 0.12 + 0.5);
        });
    }

    // Game over sound
    playGameOver() {
        if (this.muted || !this.audioContext) return;
        this.ensureContext();

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        // Descending notes
        const notes = [392, 349.23, 293.66, 261.63];
        notes.forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = 'triangle';
            osc.frequency.value = freq;

            gain.gain.setValueAtTime(this.masterVolume * 0.25, now + i * 0.2);
            gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.2 + 0.3);

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.start(now + i * 0.2);
            osc.stop(now + i * 0.2 + 0.4);
        });
    }

    // Countdown beep
    playCountdown(final = false) {
        if (this.muted || !this.audioContext) return;
        this.ensureContext();

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.value = final ? 880 : 440;

        gain.gain.setValueAtTime(this.masterVolume * 0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + (final ? 0.3 : 0.15));

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + (final ? 0.35 : 0.2));
    }

    // Button click
    playClick() {
        if (this.muted || !this.audioContext) return;
        this.ensureContext();

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.value = 600;

        gain.gain.setValueAtTime(this.masterVolume * 0.1, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + 0.06);
    }

    // ========== AMBIENT SOUNDS ==========

    // Start zombie ambient - Halloween style with spooky minor key melody
    startZombieAmbient() {
        if (this.muted || !this.audioContext) return;
        this.ensureContext();
        this.stopAmbient();

        const ctx = this.audioContext;

        // Store references for cleanup
        this.ambientNodes = [];
        this.ambientGain = ctx.createGain();
        this.ambientGain.gain.value = this.masterVolume * 0.12;
        this.ambientGain.connect(ctx.destination);

        // Halloween minor key notes - higher octave, no bass
        const halloweenNotes = [
            440,    // A4
            466.16, // Bb4
            523.25, // C5
            554.37, // Db5 (spooky diminished)
            659.25, // E5
            698.46, // F5
            783.99, // G5
            880     // A5
        ];

        let noteIndex = 0;

        // Play spooky arpeggio pattern
        const playSpookyNote = () => {
            if (this.muted || !this.ambientGain) return;

            const osc = ctx.createOscillator();
            const noteGain = ctx.createGain();
            const now = ctx.currentTime;

            // Light spooky melody note
            osc.type = 'sine';
            const note = halloweenNotes[Math.floor(Math.random() * halloweenNotes.length)];
            osc.frequency.value = note;

            noteGain.gain.setValueAtTime(0, now);
            noteGain.gain.linearRampToValueAtTime(0.15, now + 0.15);
            noteGain.gain.exponentialRampToValueAtTime(0.01, now + 1.2);

            osc.connect(noteGain);
            noteGain.connect(this.ambientGain);
            osc.start(now);
            osc.stop(now + 1.3);

            noteIndex++;

            // Random timing (1 to 2 seconds)
            const nextTime = 1000 + Math.random() * 1000;
            this.ambientInterval = setTimeout(playSpookyNote, nextTime);
        };

        // Start the pattern
        playSpookyNote();
    }

    // Start normal/smart ambient - Warm, low-frequency engaging pad
    startNormalAmbient() {
        if (this.muted || !this.audioContext) return;
        this.ensureContext();
        this.stopAmbient();

        const ctx = this.audioContext;

        this.ambientGain = ctx.createGain();
        this.ambientGain.gain.value = this.masterVolume * 0.08;
        this.ambientGain.connect(ctx.destination);

        // Create light chord pad (C major, higher octave - no bass)
        const chordFreqs = [
            523.25, // C5
            659.25, // E5
            783.99  // G5
        ];

        this.ambientNodes = [];

        chordFreqs.forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const oscGain = ctx.createGain();

            // All sine waves for soft sound
            osc.type = 'sine';
            osc.frequency.value = freq;

            // Equal quiet volumes
            oscGain.gain.value = 0.15;

            osc.connect(oscGain);
            oscGain.connect(this.ambientGain);
            osc.start();

            this.ambientNodes.push({ osc, gain: oscGain });
        });

        // Gentle shimmer effect
        let shimmerPhase = 0;
        const shimmer = () => {
            if (!this.ambientGain || this.muted) return;

            // Soft volume shimmer on all notes
            this.ambientNodes.forEach((node, i) => {
                const wave = 0.12 + Math.sin(shimmerPhase + i * 0.5) * 0.03;
                node.gain.gain.value = wave;
            });

            shimmerPhase += 0.08;
            this.ambientInterval = setTimeout(shimmer, 100);
        };

        shimmer();

        // Slow chord evolution for interest
        let chordPhase = 0;
        const evolveChord = () => {
            if (!this.ambientGain || this.muted) return;

            // Slightly detune for warmth and movement
            if (this.ambientNodes[1]) {
                const detune = Math.sin(chordPhase) * 5;
                this.ambientNodes[1].osc.detune.value = detune;
            }
            if (this.ambientNodes[2]) {
                const detune = Math.sin(chordPhase * 0.7) * 8;
                this.ambientNodes[2].osc.detune.value = detune;
            }

            chordPhase += 0.02;
            this.ambientEvolveInterval = setTimeout(evolveChord, 100);
        };

        evolveChord();
    }

    // Start clock ticking for time attack
    startClockTicking(getTimeRemaining) {
        if (this.muted) return;
        this.ensureContext();
        this.stopClockTicking();

        // Tick based on remaining time
        const tick = () => {
            const remaining = getTimeRemaining();
            if (remaining <= 0) {
                this.stopClockTicking();
                return;
            }

            const fast = remaining <= 10;
            this.playTick(fast);

            // Accelerate ticking in last 10 seconds
            let interval = 1000;
            if (remaining <= 5) {
                interval = 250;
            } else if (remaining <= 10) {
                interval = 500;
            }

            this.tickInterval = setTimeout(tick, interval);
        };

        // Start after a short delay
        this.tickInterval = setTimeout(tick, 500);
    }

    stopClockTicking() {
        if (this.tickInterval) {
            clearTimeout(this.tickInterval);
            this.tickInterval = null;
        }
    }

    // Stop ambient sounds
    stopAmbient() {
        // Clear all intervals
        if (this.ambientInterval) {
            clearTimeout(this.ambientInterval);
            this.ambientInterval = null;
        }
        if (this.ambientEvolveInterval) {
            clearTimeout(this.ambientEvolveInterval);
            this.ambientEvolveInterval = null;
        }

        // Stop main ambient node
        if (this.ambientNode) {
            try {
                if (this.ambientNode._lfo) {
                    this.ambientNode._lfo.stop();
                }
                this.ambientNode.stop();
            } catch (e) { }
            this.ambientNode = null;
        }

        // Stop additional ambient nodes (for chord pads)
        if (this.ambientNodes && this.ambientNodes.length) {
            this.ambientNodes.forEach(node => {
                try {
                    if (node.osc) node.osc.stop();
                } catch (e) { }
            });
            this.ambientNodes = [];
        }

        // Disconnect gain
        if (this.ambientGain) {
            try {
                this.ambientGain.disconnect();
            } catch (e) { }
            this.ambientGain = null;
        }
    }

    // Stop all sounds
    stopAll() {
        this.stopAmbient();
        this.stopClockTicking();
    }
}

// Global instance
const soundManager = new SoundManager();

// Initialize on first user interaction
document.addEventListener('click', () => soundManager.init(), { once: true });
document.addEventListener('keydown', () => soundManager.init(), { once: true });
