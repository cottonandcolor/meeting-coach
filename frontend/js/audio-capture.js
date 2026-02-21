/**
 * AudioCapture - Captures microphone audio as 16-bit PCM at 16kHz.
 * Sends raw PCM bytes over the WebSocket as binary frames.
 */
class AudioCapture {
    constructor() {
        this.audioContext = null;
        this.processor = null;
        this.stream = null;
        this.ws = null;
        this.isCapturing = false;
    }

    /**
     * Start capturing microphone audio.
     * @param {WebSocket} ws - The WebSocket connection to send audio to.
     */
    async start(ws) {
        this.ws = ws;

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });

            // Create AudioContext at 16kHz for direct PCM capture
            this.audioContext = new AudioContext({ sampleRate: 16000 });
            const source = this.audioContext.createMediaStreamSource(this.stream);

            // ScriptProcessor with 4096 buffer, mono input, mono output
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

            this.processor.onaudioprocess = (event) => {
                if (!this.isCapturing || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
                    return;
                }
                const float32 = event.inputBuffer.getChannelData(0);
                const int16 = this._float32ToInt16(float32);
                this.ws.send(int16.buffer);
            };

            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);
            this.isCapturing = true;

            console.log('Audio capture started: 16kHz, 16-bit PCM, mono');
        } catch (err) {
            console.error('Failed to start audio capture:', err);
            throw err;
        }
    }

    /**
     * Stop capturing audio and release resources.
     */
    stop() {
        this.isCapturing = false;

        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }

        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        this.ws = null;
        console.log('Audio capture stopped');
    }

    /**
     * Convert Float32Array audio samples to Int16Array (16-bit PCM).
     * @param {Float32Array} float32Array
     * @returns {Int16Array}
     */
    _float32ToInt16(float32Array) {
        const int16 = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        return int16;
    }
}
