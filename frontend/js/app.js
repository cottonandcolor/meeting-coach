/**
 * MeetingCoachApp - Main application orchestrator.
 * Manages WebSocket connection, audio capture, screen share, nudges, and views.
 */
class MeetingCoachApp {
    constructor() {
        this.ws = null;
        this.audioCapture = new AudioCapture();
        this.audioPlayer = new AudioPlayer();
        this.screenCapture = new ScreenCapture();
        this.nudgeDisplay = new NudgeDisplay('nudge-container');
        this.summaryView = new SummaryView('summary-container');
        this.meetingTimer = null;

        this.meetingId = null;
        this.isConnected = false;
        this.isMicActive = false;
        this.isScreenSharing = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;

        this._bindEvents();
    }

    /**
     * Bind UI event listeners.
     */
    _bindEvents() {
        // Setup form
        document.getElementById('start-meeting-btn').addEventListener('click', () => {
            this._startMeeting();
        });

        // Meeting controls
        document.getElementById('toggle-mic-btn').addEventListener('click', () => {
            this._toggleMic();
        });

        document.getElementById('toggle-screen-btn').addEventListener('click', () => {
            this._toggleScreenShare();
        });

        document.getElementById('end-meeting-btn').addEventListener('click', () => {
            this._endMeeting();
        });

        document.getElementById('new-meeting-btn').addEventListener('click', () => {
            this._resetToSetup();
        });

        // Handle screen share ended by user via browser chrome
        document.addEventListener('screenshare-ended', () => {
            this.isScreenSharing = false;
            this._updateScreenShareBtn(false);
        });

        // Agenda item management
        document.getElementById('add-agenda-btn').addEventListener('click', () => {
            this._addAgendaItem();
        });

        document.getElementById('agenda-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this._addAgendaItem();
            }
        });
    }

    /**
     * Start a new meeting session.
     */
    async _startMeeting() {
        const userName = document.getElementById('user-name').value.trim() || 'User';
        const duration = parseInt(document.getElementById('meeting-duration').value, 10) || 30;
        const agendaItems = this._getAgendaItems();

        // Generate meeting ID
        this.meetingId = 'mtg_' + Date.now().toString(36);

        // Initialize timer
        this.meetingTimer = new MeetingTimer('meeting-timer', duration);

        // Connect WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/meeting/${this.meetingId}`;

        try {
            await this._connectWebSocket(wsUrl);

            // Send configuration
            this.ws.send(
                JSON.stringify({
                    type: 'config',
                    config: {
                        user_name: userName,
                        meeting_duration_minutes: duration,
                        agenda_items: agendaItems,
                    },
                })
            );

            // Start audio capture
            await this.audioCapture.start(this.ws);
            this.isMicActive = true;

            // Initialize audio player (needs user gesture context)
            this.audioPlayer.init();
            await this.audioPlayer.resume();

            // Start timer
            this.meetingTimer.start();

            // Switch to active meeting view
            this._showView('active-meeting-view');
            this._updateMicBtn(true);

            // Display meeting info
            document.getElementById('meeting-name-display').textContent = userName + "'s Meeting";
            document.getElementById('meeting-agenda-display').innerHTML = agendaItems.length
                ? agendaItems.map((a) => `<li>${this._esc(a)}</li>`).join('')
                : '<li class="empty-state">No agenda set</li>';

        } catch (err) {
            console.error('Failed to start meeting:', err);
            this._showError('Failed to start meeting: ' + err.message);
        }
    }

    /**
     * Connect to WebSocket with retry logic.
     */
    _connectWebSocket(url) {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                resolve();
            };

            this.ws.onmessage = (event) => {
                this._handleServerMessage(event.data);
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                this.isConnected = false;
                if (this.meetingTimer && this.meetingTimer.isRunning) {
                    this._attemptReconnect(url);
                }
            };

            this.ws.onerror = (err) => {
                console.error('WebSocket error:', err);
                reject(new Error('WebSocket connection failed'));
            };
        });
    }

    /**
     * Attempt to reconnect after connection loss.
     */
    async _attemptReconnect(url) {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this._showError('Connection lost. Please end the meeting and start a new one.');
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`);

        setTimeout(async () => {
            try {
                await this._connectWebSocket(url);
                // Restart audio capture with new WebSocket
                if (this.isMicActive) {
                    this.audioCapture.stop();
                    await this.audioCapture.start(this.ws);
                }
                if (this.isScreenSharing) {
                    this.screenCapture.stop();
                    await this.screenCapture.start(this.ws);
                }
            } catch (err) {
                console.error('Reconnection failed:', err);
            }
        }, delay);
    }

    /**
     * Handle incoming server messages.
     */
    _handleServerMessage(data) {
        try {
            const msg = JSON.parse(data);

            switch (msg.type) {
                case 'connection_ready':
                    console.log('Session established:', msg.meeting_id);
                    break;

                case 'nudge':
                    this.nudgeDisplay.show(msg.nudge);
                    break;

                case 'audio_whisper':
                    this.audioPlayer.play(msg.data, msg.mime_type);
                    break;

                case 'summary':
                    this.summaryView.render(msg.summary);
                    this._showView('summary-view');
                    break;

                case 'state_update':
                    this._updateStateDisplay(msg);
                    break;

                case 'error':
                    console.error('Server error:', msg.message);
                    this._showError(msg.message);
                    break;

                default:
                    console.log('Unknown message type:', msg.type);
            }
        } catch (err) {
            console.error('Failed to parse server message:', err);
        }
    }

    /**
     * Toggle microphone on/off.
     */
    async _toggleMic() {
        if (this.isMicActive) {
            this.audioCapture.stop();
            this.isMicActive = false;
        } else {
            await this.audioCapture.start(this.ws);
            this.isMicActive = true;
        }
        this._updateMicBtn(this.isMicActive);
    }

    /**
     * Toggle screen sharing.
     */
    async _toggleScreenShare() {
        if (this.isScreenSharing) {
            this.screenCapture.stop();
            this.isScreenSharing = false;
        } else {
            try {
                await this.screenCapture.start(this.ws);
                this.isScreenSharing = true;
            } catch (err) {
                console.error('Screen share failed:', err);
                return;
            }
        }
        this._updateScreenShareBtn(this.isScreenSharing);
    }

    /**
     * End the current meeting.
     */
    _endMeeting() {
        // Stop timer
        if (this.meetingTimer) {
            this.meetingTimer.stop();
        }

        // Tell server to generate summary
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'end_meeting' }));
        }

        // Stop capture
        this.audioCapture.stop();
        this.screenCapture.stop();
        this.isMicActive = false;
        this.isScreenSharing = false;

        // Show loading state in summary view
        document.getElementById('summary-container').innerHTML =
            '<div class="loading">Generating summary...</div>';
        this._showView('summary-view');

        // Close WebSocket after a delay to allow summary to arrive
        setTimeout(() => {
            if (this.ws) {
                this.ws.close();
            }
        }, 10000);
    }

    /**
     * Reset to setup view for a new meeting.
     */
    _resetToSetup() {
        if (this.ws) {
            this.ws.close();
        }
        this.audioCapture.stop();
        this.screenCapture.stop();
        this.audioPlayer.destroy();
        this.nudgeDisplay.clear();
        this.summaryView.clear();

        this.meetingId = null;
        this.isConnected = false;
        this.isMicActive = false;
        this.isScreenSharing = false;

        this._showView('setup-view');
    }

    // --- UI helpers ---

    _showView(viewId) {
        document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
        document.getElementById(viewId).classList.add('active');
    }

    _updateMicBtn(active) {
        const btn = document.getElementById('toggle-mic-btn');
        btn.classList.toggle('active', active);
        btn.textContent = active ? 'Mute Mic' : 'Unmute Mic';
    }

    _updateScreenShareBtn(active) {
        const btn = document.getElementById('toggle-screen-btn');
        btn.classList.toggle('active', active);
        btn.textContent = active ? 'Stop Sharing' : 'Share Screen';
    }

    _updateStateDisplay(state) {
        const topicEl = document.getElementById('current-topic');
        if (topicEl && state.current_topic) {
            topicEl.textContent = state.current_topic;
        }

        const actionCountEl = document.getElementById('action-items-count');
        if (actionCountEl) {
            actionCountEl.textContent = state.action_items_count || 0;
        }
    }

    _addAgendaItem() {
        const input = document.getElementById('agenda-input');
        const value = input.value.trim();
        if (!value) return;

        const list = document.getElementById('agenda-list');
        const li = document.createElement('li');
        li.textContent = value;

        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-agenda-btn';
        removeBtn.textContent = '\u00d7';
        removeBtn.onclick = () => li.remove();
        li.appendChild(removeBtn);

        list.appendChild(li);
        input.value = '';
        input.focus();
    }

    _getAgendaItems() {
        const items = [];
        document.querySelectorAll('#agenda-list li').forEach((li) => {
            // Get text content without the remove button text
            const text = li.firstChild.textContent.trim();
            if (text) items.push(text);
        });
        return items;
    }

    _showError(message) {
        const errorEl = document.getElementById('error-display');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.add('visible');
            setTimeout(() => errorEl.classList.remove('visible'), 5000);
        }
    }

    _esc(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MeetingCoachApp();
});
