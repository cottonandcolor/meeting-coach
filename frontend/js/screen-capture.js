/**
 * ScreenCapture - Captures screen share frames as JPEG and sends via WebSocket.
 * Uses getDisplayMedia API and canvas for frame extraction.
 */
class ScreenCapture {
    constructor() {
        this.stream = null;
        this.intervalId = null;
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.video = document.createElement('video');
        this.ws = null;
        this.isCapturing = false;
        this.frameIntervalMs = 2000; // 1 frame every 2 seconds
    }

    /**
     * Start screen capture and begin sending frames.
     * @param {WebSocket} ws - The WebSocket connection.
     */
    async start(ws) {
        this.ws = ws;

        try {
            this.stream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    frameRate: 1,
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                },
            });

            // Handle user stopping share via browser UI
            this.stream.getVideoTracks()[0].addEventListener('ended', () => {
                this.stop();
                document.dispatchEvent(new CustomEvent('screenshare-ended'));
            });

            this.video.srcObject = this.stream;
            this.video.muted = true;
            await this.video.play();

            this.isCapturing = true;
            this.intervalId = setInterval(() => this._captureFrame(), this.frameIntervalMs);

            console.log('Screen capture started');
        } catch (err) {
            console.error('Failed to start screen capture:', err);
            throw err;
        }
    }

    /**
     * Stop screen capture and release resources.
     */
    stop() {
        this.isCapturing = false;

        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }

        this.video.srcObject = null;
        this.ws = null;
        console.log('Screen capture stopped');
    }

    /**
     * Capture a single frame and send it over WebSocket.
     */
    _captureFrame() {
        if (!this.isCapturing || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }

        try {
            // Scale to max 1280x720
            const vw = this.video.videoWidth;
            const vh = this.video.videoHeight;
            const scale = Math.min(1, 1280 / vw, 720 / vh);
            this.canvas.width = Math.round(vw * scale);
            this.canvas.height = Math.round(vh * scale);

            this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);

            // Convert to JPEG and send as base64
            this.canvas.toBlob(
                (blob) => {
                    if (!blob) return;
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const base64 = reader.result.split(',')[1];
                        this.ws.send(
                            JSON.stringify({
                                type: 'screen_frame',
                                data: base64,
                            })
                        );
                    };
                    reader.readAsDataURL(blob);
                },
                'image/jpeg',
                0.7
            );
        } catch (err) {
            console.error('Error capturing frame:', err);
        }
    }
}
