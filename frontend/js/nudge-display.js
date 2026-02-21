/**
 * NudgeDisplay - Renders coaching nudges as toast notifications.
 */
class NudgeDisplay {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.nudgeCount = 0;
    }

    /**
     * Display a nudge as a toast notification.
     * @param {Object} nudge - { type, message, priority, timestamp }
     */
    show(nudge) {
        this.nudgeCount++;

        const card = document.createElement('div');
        card.className = `nudge-card nudge-${nudge.priority} nudge-type-${nudge.type}`;
        card.setAttribute('role', 'alert');

        const icon = this._getIcon(nudge.type);
        const typeLabel = nudge.type.replace(/_/g, ' ');
        const timeStr = new Date(nudge.timestamp * 1000).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
        });

        card.innerHTML = `
            <div class="nudge-header">
                <span class="nudge-icon">${icon}</span>
                <span class="nudge-type-label">${typeLabel}</span>
                <span class="nudge-time">${timeStr}</span>
            </div>
            <p class="nudge-message">${this._escapeHtml(nudge.message)}</p>
        `;

        // Add dismiss button
        const dismissBtn = document.createElement('button');
        dismissBtn.className = 'nudge-dismiss';
        dismissBtn.textContent = '\u00d7';
        dismissBtn.onclick = () => this._dismiss(card);
        card.querySelector('.nudge-header').appendChild(dismissBtn);

        // Insert at top of container
        this.container.prepend(card);

        // Animate in
        requestAnimationFrame(() => {
            card.classList.add('nudge-visible');
        });

        // Auto-dismiss: 15s for high priority, 8s for others
        const timeout = nudge.priority === 'high' ? 15000 : 8000;
        setTimeout(() => this._dismiss(card), timeout);

        // Update counter if element exists
        const counter = document.getElementById('nudge-count');
        if (counter) {
            counter.textContent = this.nudgeCount;
        }
    }

    /**
     * Dismiss a nudge card with animation.
     */
    _dismiss(card) {
        if (!card.parentNode) return;
        card.classList.remove('nudge-visible');
        card.classList.add('nudge-dismissing');
        setTimeout(() => card.remove(), 300);
    }

    /**
     * Get icon for nudge type.
     */
    _getIcon(type) {
        const icons = {
            participation: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>',
            time: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
            action_item: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
            topic: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
            decision: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
            summary_suggestion: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
        };
        return icons[type] || icons['summary_suggestion'];
    }

    /**
     * Escape HTML to prevent XSS.
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Clear all nudges from the display.
     */
    clear() {
        this.container.innerHTML = '';
        this.nudgeCount = 0;
    }
}
