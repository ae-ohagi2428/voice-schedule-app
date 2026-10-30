const schedules = JSON.parse(document.getElementById('schedules-data').textContent);
for (const schedule of schedules) {
    schedule.start_at = new Date(schedule.start_at);
    schedule.end_at = new Date(schedule.end_at);
}

const runningEl = document.getElementById('state-running');
const waitingEl = document.getElementById('state-waiting');
const finishedEl = document.getElementById('state-finished');
const noneEl = document.getElementById('state-none');
const runningTimeEl = document.getElementById('running-time');
const runningTitleEl = document.getElementById('running-title');
const runningRemainingEl = document.getElementById('running-remaining');
const runningProgressEl = document.getElementById('running-progress');
const timelineRows = document.querySelectorAll('.run-row');
const gapRows = document.querySelectorAll('.run-gap');
const timelineEl = document.getElementById('timeline');
const waitingTimeEl = document.getElementById('waiting-time');
const waitingTitleEl = document.getElementById('waiting-title');
const startNowBtn = document.getElementById('start-now-btn');
const characterBtn = document.getElementById('character');
const speechBubbleEl = document.getElementById('speech-bubble');
const volumeNoteEl = document.getElementById('volume-note');
const watchingEl = document.getElementById('watching');
const actionsTopEl = document.getElementById('actions-top');
const actionsBottomEl = document.getElementById('actions-bottom');

const startNowUrl = startNowBtn.dataset.startNowUrl;
const speechUrl = characterBtn.dataset.speechUrl;
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
const settings = JSON.parse(document.getElementById('settings-data').textContent);

const BUBBLE_HIDE_AFTER = 10000;
const ANNOUNCE_GAP_LIMIT = 90000;

let voiceEnabled = false;
let previousStatus = null;
let bubbleTimer = null;
let wakeLock = null;
let lastCheckedAt = null;
const audio = new Audio();
const speechQueue = [];
let isSpeaking = false;

function getScheduleStatus(schedules, now) {
    const currentSchedule = schedules.find((schedule) =>
        schedule.start_at <= now && schedule.end_at > now
    );
    const nextSchedule = schedules.find((schedule) =>
        schedule.start_at > now
    );
    let state;
    if (currentSchedule) {
        state = 'running';
    } else if (nextSchedule) {
        state = 'waiting';
    } else if (schedules.length > 0) {
        state = 'finished';
    } else {
        state = 'none';
    }
    let remainingMinutes = null;
    let remainingSeconds = null;
    if (currentSchedule) {
        remainingMinutes = Math.ceil((currentSchedule.end_at - now) / 60000);
        remainingSeconds = Math.ceil((currentSchedule.end_at - now) / 1000);
    }
    return {state, currentSchedule, nextSchedule, remainingMinutes, remainingSeconds};
}

function formatTime(date) {
    const hours = date.getHours();
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
}

function formatSpokenTime(date) {
    const hours = date.getHours();
    const minutes = date.getMinutes();
    if (minutes === 0) {
        return `${hours}時`;
    }
    return `${hours}時${minutes}分`;
}

function renderStatus(status) {
    runningEl.classList.add('hidden');
    waitingEl.classList.add('hidden');
    finishedEl.classList.add('hidden');
    noneEl.classList.add('hidden');

    if (status.state !== 'finished' && status.state !== 'none') {
        setRandomEnabled(true);
        actionsTopEl.classList.add('hidden');
        actionsBottomEl.classList.remove('hidden');
    } else {
        setRandomEnabled(false);
        actionsTopEl.classList.remove('hidden');
        actionsBottomEl.classList.add('hidden');
    }
    if (status.state === 'running') {
        runningEl.classList.remove('hidden');
        runningTimeEl.textContent = `${formatTime(status.currentSchedule.start_at)} ～ ${formatTime(status.currentSchedule.end_at)}`;
        runningTitleEl.textContent = `${status.currentSchedule.title}`;
        const minutes = Math.floor(status.remainingSeconds / 60);
        const seconds = String(status.remainingSeconds % 60).padStart(2, '0');
        runningRemainingEl.textContent = `${minutes}:${seconds}`;
        const totalSeconds = (status.currentSchedule.end_at - status.currentSchedule.start_at) / 1000;
        const progressPercentage = (totalSeconds - status.remainingSeconds) / totalSeconds * 100;
        runningProgressEl.style.width = `${progressPercentage}%`;
        if (voiceEnabled) {
            watchingEl.classList.remove('hidden');
        }
    } else if (status.state === 'waiting') {
        waitingEl.classList.remove('hidden');
        waitingTimeEl.textContent = `${formatTime(status.nextSchedule.start_at)} ～ ${formatTime(status.nextSchedule.end_at)}`;
        waitingTitleEl.textContent = `${status.nextSchedule.title}`;
        watchingEl.classList.add('hidden');
    } else if (status.state === 'finished') {
        finishedEl.classList.remove('hidden');
        watchingEl.classList.add('hidden');
    } else {
        noneEl.classList.remove('hidden');
        watchingEl.classList.add('hidden');
    }
}

function updateTimeline(status, now) {
    for (const row of timelineRows) {
        const rowId = Number(row.dataset.id);
        const schedule = schedules.find((schedule) => schedule.id === rowId);
        row.classList.toggle('is-now', schedule === status.currentSchedule);
        row.classList.toggle('is-done', schedule.end_at <= now);
        row.querySelector('.run-time').textContent = formatTime(schedule.start_at);
        const runDuration = `${Math.round((schedule.end_at - schedule.start_at) / 60000)}分`;
        row.querySelector('.run-duration').textContent = runDuration;
    }
    for (const row of gapRows) {
        const rowId = Number(row.dataset.id);
        const schedule = schedules.find((schedule) => schedule.id === rowId);
        const nextSchedule = schedules[schedules.indexOf(schedule) + 1];
        const gapMinutes = Math.floor((nextSchedule.start_at - schedule.end_at) / 60000);
        row.classList.toggle('hidden', gapMinutes <= 0);
        row.querySelector('.run-gap-minutes').textContent = `あき ${gapMinutes}分`;
    }
}

function scrollTimeline(previous, current) {
    if (previous && previous.currentSchedule === current.currentSchedule) {
        return;
    }
    const targetSchedule = current.currentSchedule ?? current.nextSchedule;
    if (!targetSchedule) {
        return;
    }
    const rowEl = timelineEl.querySelector(`[data-id="${targetSchedule.id}"]`);
    timelineEl.scrollTop = rowEl.offsetTop - (timelineEl.clientHeight - rowEl.offsetHeight) / 2;
}

function checkStatus() {
    const now = new Date();
    const status = getScheduleStatus(schedules, now);
    const isLate = lastCheckedAt !== null && now - lastCheckedAt > ANNOUNCE_GAP_LIMIT;
    if (isLate) {
        speechSynthesis.cancel();
    }
    renderStatus(status);
    updateTimeline(status, now);
    scrollTimeline(previousStatus, status);
    if (!isLate) {
        announceChange(previousStatus, status);
        announceRemaining(previousStatus, status);
    }
    previousStatus = status;
    lastCheckedAt = now;
}

async function startNow() {
    const status = getScheduleStatus(schedules, new Date());
    if (!status.nextSchedule) {
        location.reload();
        return;
    }
    try {
        const response = await fetch(startNowUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ id: status.nextSchedule.id })
        });
        if (!response.ok) {
            location.reload();
            return;
        }
        const data = await response.json();
        status.nextSchedule.start_at = new Date(data.start_at);
        checkStatus();
    } catch (error) {
        showToast('通信がうまくいかなかったよ。もう一度押してみてね');
    }
}
function showBubble(text) {
    clearTimeout(bubbleTimer);
    speechBubbleEl.textContent = text;
    speechBubbleEl.classList.remove('hidden');
    volumeNoteEl.classList.add('hidden');
}

function hideBubble() {
    clearTimeout(bubbleTimer);
    speechBubbleEl.classList.add('hidden');
}

function hideBubbleLater() {
    clearTimeout(bubbleTimer);
    bubbleTimer = setTimeout(() => {
    speechBubbleEl.classList.add('hidden');
    }, BUBBLE_HIDE_AFTER);
}

function speak(text) {
    if (!voiceEnabled) {
        return;
    }
    speechQueue.push(text);
    if (!isSpeaking) {
        playNext();
    }
}

async function playNext() {
    if (speechQueue.length === 0) {
        isSpeaking = false;
        return;
    } else {
        isSpeaking = true;
        const text = speechQueue.shift();
        const response = await fetch(speechUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ text: text })
        });
        if (!response.ok) {
            playNext();
            return;
        } else {
            const blob = await response.blob();
            audio.src = URL.createObjectURL(blob);
            audio.play();
        }
    }
}

function speakWithBrowser(text) {
    if (!voiceEnabled) {
        return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ja-JP';
    utterance.onstart = () => {
        showBubble(text);
        startOnce('notice', NOTICE_LENGTH);
    };
    utterance.onend = () => {
        hideBubbleLater();
    };
    speechSynthesis.speak(utterance);
}

async function requestWakeLock() {
    if (!('wakeLock' in navigator)) {
        return;
    }
    try {
        wakeLock = await navigator.wakeLock.request('screen');
    } catch (error) {
        // 何もしない（画面ONロックはかからない）
    }
}

function startVoice() {
    const now = new Date();
    const status = getScheduleStatus(schedules, now);
    if (status.state === 'finished') {
        showBubble('今日もおつかれさま！');
        hideBubbleLater();
        reactToTap();
        return;
    } else if (status.state === 'none') {
        showBubble('今日の計画を立てよう！');
        hideBubbleLater();
        reactToTap();
        return;
    } else if (voiceEnabled) {
        reactToTap();
        if (state === 'laugh') {
            showBubble('一緒に進めるとたのしいね～♪');
            hideBubbleLater();
        }
        return;
    }
    voiceEnabled = true;
    requestWakeLock();
    renderStatus(status);
    speak('いっしょにがんばろう');
    if (status.state === 'running') {
        speak(`今は${status.currentSchedule.title}の時間だよ。残りあと${status.remainingMinutes}分くらいだよ`);
    } else if (status.state === 'waiting') {
        speak(`次の予定は${formatSpokenTime(status.nextSchedule.start_at)}から${status.nextSchedule.title}だよ`);
    }
}

function announceChange(previous, current) {
    if (previous == null) {
        return;
    } else if (previous.currentSchedule && previous.currentSchedule !== current.currentSchedule ) {
        if (current.state === 'running') {
            speak(`${previous.currentSchedule.title}の終了時間だよ。次は${current.currentSchedule.title}のタスクをはじめるよ！`);
        } else if (current.state === 'waiting') {
            speak(`${previous.currentSchedule.title}の終了時間だよ。次は${formatSpokenTime(current.nextSchedule.start_at)}から${current.nextSchedule.title}だよ`);
        } else if (current.state === 'finished') {
            speak(`${previous.currentSchedule.title}の終了時間だよ！今日のタスクはこれでおしまい。おつかれさまでした`);
        }
        return;
    } else if (!previous.currentSchedule && current.currentSchedule) {
        speak(`${current.currentSchedule.title}をはじめるよ`);
    }
}

function announceRemaining(previous, current) {
    if (!settings.time_left_alert) {
        return;
    } else if (previous == null) {
        return;
    } else if (current.state !== 'running') {
        return;
    } else if (previous.currentSchedule !== current.currentSchedule) {
        return;
    } else if (previous.remainingMinutes === current.remainingMinutes) {
        return;
    }
    if (current.remainingMinutes % settings.alert_interval === 0) {
        speak(`${current.currentSchedule.title}の残り時間はあと${current.remainingMinutes}分だよ`);
    }
}

checkStatus();

setInterval(checkStatus, 1000);
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        if (voiceEnabled) {
            requestWakeLock();
        }
        checkStatus();
    }
});

startNowBtn.addEventListener('click', startNow);

characterBtn.addEventListener('click', startVoice);

chara.addEventListener('statechange', (event) => {
    if (!voiceEnabled) {
        return;
    }
    if (event.detail.state === 'sleep') {
        bubbleTimer = showBubble('むにゃむにゃ……');
        setTimeout(() => {
            showBubble('ぐぅ……ぐぅ……みまもってるよぉ……');
            hideBubbleLater();
        }, 4500);
    } else if (event.detail.state === 'breath') {
        showBubble('深呼吸、深呼吸～！');
        hideBubbleLater();
    } else if (event.detail.state === 'sing') {
        showBubble('～～♪');
        hideBubbleLater();
    } else if (event.detail.state === 'wake') {
        hideBubble();
    } else if (event.detail.state === 'nod') {
        showBubble('疲れたら、ちょっと休憩しようね～！');
        hideBubbleLater();
    }
});