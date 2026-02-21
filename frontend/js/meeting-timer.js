/**
 * MeetingTimer - Tracks and displays meeting duration.
 */
class MeetingTimer {
    constructor(displayId, durationMinutes) {
        this.displayEl = document.getElementById(displayId);
        this.durationMinutes = durationMinutes || 30;
        this.startTime = null;
        this.intervalId = null;
        this.isRunning = false;
    }

    /**
     * Start the timer.
     */
    start() {
        this.startTime = Date.now();
        this.isRunning = true;
        this._update();
        this.intervalId = setInterval(() => this._update(), 1000);
    }

    /**
     * Stop the timer.
     * @returns {number} Elapsed seconds.
     */
    stop() {
        this.isRunning = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        return this.getElapsedSeconds();
    }

    /**
     * Get elapsed time in seconds.
     */
    getElapsedSeconds() {
        if (!this.startTime) return 0;
        return Math.floor((Date.now() - this.startTime) / 1000);
    }

    /**
     * Get elapsed time in minutes.
     */
    getElapsedMinutes() {
        return this.getElapsedSeconds() / 60;
    }

    /**
     * Update the scheduled duration.
     */
    setDuration(minutes) {
        this.durationMinutes = minutes;
    }

    /**
     * Update the display.
     */
    _update() {
        if (!this.displayEl) return;

        const elapsed = this.getElapsedSeconds();
        const totalSeconds = this.durationMinutes * 60;
        const remaining = totalSeconds - elapsed;

        const elapsedStr = this._formatTime(elapsed);
        const totalStr = this._formatTime(totalSeconds);

        this.displayEl.textContent = `${elapsedStr} / ${totalStr}`;

        // Visual warnings
        this.displayEl.classList.remove('timer-warning', 'timer-overtime');
        if (remaining <= 0) {
            this.displayEl.classList.add('timer-overtime');
        } else if (remaining <= 300) {
            // Less than 5 minutes
            this.displayEl.classList.add('timer-warning');
        }
    }

    /**
     * Format seconds as MM:SS or H:MM:SS.
     */
    _formatTime(totalSec) {
        const absSeconds = Math.abs(Math.floor(totalSec));
        const hours = Math.floor(absSeconds / 3600);
        const minutes = Math.floor((absSeconds % 3600) / 60);
        const seconds = absSeconds % 60;

        const prefix = totalSec < 0 ? '-' : '';
        const mm = String(minutes).padStart(2, '0');
        const ss = String(seconds).padStart(2, '0');

        if (hours > 0) {
            return `${prefix}${hours}:${mm}:${ss}`;
        }
        return `${prefix}${mm}:${ss}`;
    }
}
