/**
 * SummaryView - Renders the post-meeting summary.
 */
class SummaryView {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    /**
     * Render the meeting summary.
     * @param {Object} summary - Summary data from the agent.
     */
    render(summary) {
        if (!this.container) return;

        const html = `
            <div class="summary-content">
                <h2>Meeting Summary</h2>

                <div class="summary-section summary-overview">
                    <h3>Overview</h3>
                    <div class="summary-stats">
                        <div class="stat">
                            <span class="stat-value">${summary.duration_actual_minutes || 0}</span>
                            <span class="stat-label">Minutes</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">${(summary.action_items || []).length}</span>
                            <span class="stat-label">Action Items</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">${(summary.topics || []).length}</span>
                            <span class="stat-label">Topics</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">${summary.coaching_stats?.total_nudges || 0}</span>
                            <span class="stat-label">Nudges</span>
                        </div>
                    </div>
                    ${!summary.on_time ? '<p class="overtime-note">Meeting ran over the scheduled time.</p>' : ''}
                </div>

                <div class="summary-section summary-topics">
                    <h3>Topics Discussed</h3>
                    ${this._renderTopics(summary.topics || [])}
                </div>

                <div class="summary-section summary-actions">
                    <h3>Action Items</h3>
                    ${this._renderActionItems(summary.action_items || [])}
                </div>

                <div class="summary-section summary-participation">
                    <h3>Your Participation</h3>
                    ${this._renderParticipation(summary.participation || {})}
                </div>

                <div class="summary-section summary-coaching">
                    <h3>Coaching Stats</h3>
                    ${this._renderCoachingStats(summary.coaching_stats || {})}
                </div>
            </div>
        `;

        this.container.innerHTML = html;
    }

    _renderTopics(topics) {
        if (topics.length === 0) {
            return '<p class="empty-state">No topics were tracked.</p>';
        }
        const items = topics
            .map(
                (t) => `
            <li>
                <span class="topic-name">${this._esc(t.topic)}</span>
                <span class="topic-duration">${t.duration_minutes || 0} min</span>
            </li>`
            )
            .join('');
        return `<ul class="topic-list">${items}</ul>`;
    }

    _renderActionItems(items) {
        if (items.length === 0) {
            return '<p class="empty-state">No action items were captured.</p>';
        }
        const rows = items
            .map(
                (item) => `
            <tr>
                <td>${this._esc(item.assignee)}</td>
                <td>${this._esc(item.description)}</td>
                <td>${this._esc(item.deadline)}</td>
            </tr>`
            )
            .join('');
        return `
            <table class="action-items-table">
                <thead>
                    <tr><th>Assignee</th><th>Task</th><th>Deadline</th></tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>`;
    }

    _renderParticipation(participation) {
        const pct = participation.user_participation_pct || 0;
        return `
            <div class="participation-bar-container">
                <div class="participation-bar" style="width: ${Math.min(pct, 100)}%"></div>
            </div>
            <p>You spoke <strong>${participation.user_turns || 0}</strong> times
            out of <strong>${participation.total_speaker_turns || 0}</strong> total turns
            (<strong>${pct}%</strong>).</p>
        `;
    }

    _renderCoachingStats(stats) {
        const breakdown = stats.breakdown || {};
        const entries = Object.entries(breakdown);
        if (entries.length === 0) {
            return '<p class="empty-state">No coaching nudges were given.</p>';
        }
        const items = entries
            .map(([type, count]) => `<li>${type.replace(/_/g, ' ')}: <strong>${count}</strong></li>`)
            .join('');
        return `
            <p>Total nudges: <strong>${stats.total_nudges || 0}</strong></p>
            <ul class="coaching-breakdown">${items}</ul>
        `;
    }

    _esc(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    /**
     * Clear the summary view.
     */
    clear() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}
