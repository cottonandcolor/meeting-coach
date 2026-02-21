/**
 * AudioPlayer - Plays PCM audio whispers from the agent.
 * Expects 16-bit PCM at 24kHz sample rate (Gemini Live API output format).
 */
class AudioPlayer {
    constructor() {
        this.audioContext = null;
        this.queue = [];
        this.isPlaying = false;
    }

    /**
     * Initialize the audio context. Must be called after a user gesture.
     */
    init() {
        if (!this.audioContext) {
            this.audioContext = new AudioContext({ sampleRate: 24000 });
        }
    }

    /**
     * Play a base64-encoded PCM audio chunk.
     * @param {string} base64Data - Base64-encoded 16-bit PCM audio.
     * @param {string} mimeType - MIME type (e.g., "audio/pcm;rate=24000").
     */
    async play(base64Data, mimeType) {
        this.init();

        try {
            // Decode base64 to ArrayBuffer
            const binaryStr = atob(base64Data);
            const bytes = new Uint8Array(binaryStr.length);
            for (let i = 0; i < binaryStr.length; i++) {
                bytes[i] = binaryStr.charCodeAt(i);
            }

            // Parse sample rate from mime type
            let sampleRate = 24000;
            const rateMatch = mimeType && mimeType.match(/rate=(\d+)/);
            if (rateMatch) {
                sampleRate = parseInt(rateMatch[1], 10);
            }

            // Convert Int16 PCM to Float32 for Web Audio API
            const int16 = new Int16Array(bytes.buffer);
            const float32 = new Float32Array(int16.length);
            for (let i = 0; i < int16.length; i++) {
                float32[i] = int16[i] / 32768.0;
            }

            // Create AudioBuffer and play
            const audioBuffer = this.audioContext.createBuffer(1, float32.length, sampleRate);
            audioBuffer.getChannelData(0).set(float32);

            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            source.start();

        } catch (err) {
            console.error('Failed to play audio whisper:', err);
        }
    }

    /**
     * Resume audio context (needed after browser autoplay policy).
     */
    async resume() {
        if (this.audioContext && this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
    }

    /**
     * Clean up resources.
     */
    destroy() {
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
    }
}
