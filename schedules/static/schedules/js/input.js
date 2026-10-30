const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = 'ja-JP';
recognition.interimResults = true;
recognition.continuous = true;

const resultEl = document.getElementById('result');
const resultCardEl = document.getElementById('result-card');
const resultPlaceholder = '<span class="text-[#736D87]">ここに話した言葉が出るよ</span>';

const pageEl = document.getElementById('input-page');
const mode = pageEl.dataset.mode;
let finalText = '';
let endedBy = null;
const remainingEl = document.getElementById('remaining');
const remainingTextEl = document.getElementById('remaining-text');
const listeningHintEl = document.getElementById('listening-hint');
const subBubbleEl = document.getElementById('sub-bubble');
let remaining = Number(remainingEl.textContent);
const startBtn = document.getElementById('start-btn');
updateRemaining(remaining);

recognition.onresult = (event) => {
    let interimText = '';
    for (let i = event.resultIndex; i < event.results.length; i++){
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
            finalText += transcript;
        } else {
            interimText += transcript;
        }
    }
    resultEl.textContent = finalText + interimText;
    resultCardEl.scrollTop = resultCardEl.scrollHeight;
};

recognition.onend  = () => {
    if (endedBy === 'confirm') {
        sendText();
    } else if (endedBy === null) {
        showState('stopped');
    }
};

recognition.onerror = (event) => {
    if (event.error === 'aborted') {
        return;
    }
    endedBy = 'error';
    const message = errorMessages[event.error] || '音声入力がうまくいかなかったよ。もう一度試してね';
    showToast(message, 'error');
    finalText = '';
    resultEl.innerHTML = resultPlaceholder;
    showState('before');
};

const states = {
    before: document.getElementById('state-before'),
    listening: document.getElementById('state-listening'),
    stopped: document.getElementById('state-stopped'),
    sending: document.getElementById('state-sending'),
};

const bubbleTexts = {
    before: 'マイクボタンをおして予定を教えてね',
    listening: 'うんうん、聞いてるよ〜。',
    stopped: '続きを話す？それとも編集画面に進む？',
    sending: 'かんがえ中……',
};

const errorMessages = {
    'not-allowed': 'マイクが使えないよ。ブラウザの設定でマイクを許可してね',
    'audio-capture': 'マイクが見つからないよ。つながっているか確かめてね',
    'no-speech': '声が聞こえなかったよ。もう一度話してね',
    network: '音声入力につながらなかったよ。インターネットにつながっているか確かめるか、ChromeやSafariなどほかのブラウザで開いてみてね',
    'service-not-allowed': '音声入力につながらなかったよ。インターネットにつながっているか確かめるか、ChromeやSafariなどほかのブラウザで開いてみてね',
};

const bubbleEl = document.getElementById('input-bubble');

function showState(name) {
    for (const key in states) {
        if (key !== name) {
            states[key].classList.add('hidden');
        } else {
            states[key].classList.remove('hidden');
        }
    }
    bubbleEl.textContent = bubbleTexts[name];
    if (name === 'listening') {
        listeningHintEl.classList.remove('hidden');
        remainingTextEl.classList.add('hidden');
    } else {
        remainingTextEl.classList.remove('hidden');
        listeningHintEl.classList.add('hidden');
    }
    subBubbleEl.classList.toggle('invisible', name === 'sending');
}

function updateRemaining(value) {
    remaining = value;
    remainingEl.textContent = value;
    if (value === 0) {
        startBtn.classList.add('opacity-50');
        startBtn.setAttribute('aria-disabled', 'true');
        remainingTextEl.textContent = 'きょうの音声入力はおしまいだよ。また明日話してね';
    }
}

async function sendText() {
    if (finalText === '') {
        showState('before');
        return;
    }
    showState('sending');
    try {
        const response = await fetch(pageEl.dataset.transcriptUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': pageEl.dataset.csrfToken,
            },
            body: JSON.stringify({ text:finalText, mode: mode }),
        });
        const data = await response.json();
        if (data.remaining !== undefined) {
            updateRemaining(data.remaining);
        }
        if (!response.ok) {
            showToast(data.error || 'うまくいかなかったよ。もう一度話してね', 'error');
        } else {
            window.location.href = data.redirect_url;
            return;
        }
    } catch (error) {
        showToast('うまくいかなかったよ。もう一度話してね', 'error');
    }
    showState('before');
};

document.getElementById('start-btn').addEventListener('click', () => {
    if (remaining === 0) {
        showToast('今日は既に5回使ったよ。また明日話してね。', 'error');
        return;
    }
    endedBy = null;
    recognition.start();
    showState('listening');
});
document.getElementById('cancel-btn').addEventListener('click', () => {
    endedBy = 'cancel';
    recognition.abort();
    showState('before');
    finalText = '';
    resultEl.innerHTML = resultPlaceholder;
});
document.getElementById('confirm-btn').addEventListener('click', () => {
    endedBy = 'confirm';
    recognition.stop();
    showState('sending');
});
document.getElementById('restart-btn').addEventListener('click', () => {
    finalText = '';
    endedBy = null;
    recognition.start();
    showState('listening');
    resultEl.innerHTML = resultPlaceholder;
});
document.getElementById('resume-btn').addEventListener('click', () => {
    endedBy = null;
    recognition.start();
    showState('listening');
});
document.getElementById('stopped-cancel-btn').addEventListener('click', () => {
    finalText = '';
    showState('before');
    resultEl.innerHTML = resultPlaceholder;
});
document.getElementById('stopped-confirm-btn').addEventListener('click', () => {
    sendText();
});

window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        location.reload();
    }
});