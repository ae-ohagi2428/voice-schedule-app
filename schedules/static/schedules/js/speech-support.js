const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const unsupportedEl = document.getElementById('speech-unsupported');
if (!SpeechRecognition && unsupportedEl) {
    unsupportedEl.classList.remove('hidden');
}