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
const waitingTimeEl = document.getElementById('waiting-time');
const waitingTitleEl = document.getElementById('waiting-title');
const startNowBtn = document.getElementById('start-now-btn');

const startNowUrl = startNowBtn.dataset.startNowUrl;
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

const settings = JSON.parse(document.getElementById('settings-data').textContent);
const characterBtn = document.getElementById('character');
const speechBubbleEl = document.getElementById('speech-bubble');
let voiceEnabled = false;
let previousStatus = null;
let lastRemainingMinutes = null;

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
    if (currentSchedule) {
        remainingMinutes = Math.ceil((currentSchedule.end_at - now) / 60000);
    }
    return {state, currentSchedule, nextSchedule, remainingMinutes};
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

    if (status.state === 'running') {
        runningEl.classList.remove('hidden');
        runningTimeEl.textContent = `${formatTime(status.currentSchedule.start_at)} ～ ${formatTime(status.currentSchedule.end_at)}`;
        runningTitleEl.textContent = `${status.currentSchedule.title}`;
    } else if (status.state === 'waiting') {
        waitingEl.classList.remove('hidden');
        waitingTimeEl.textContent = `${formatTime(status.nextSchedule.start_at)} ～ ${formatTime(status.nextSchedule.end_at)}`;
        waitingTitleEl.textContent = `${status.nextSchedule.title}`;
    } else if (status.state === 'finished') {
        finishedEl.classList.remove('hidden');
    } else {
        noneEl.classList.remove('hidden');
    }
}

function checkStatus() {
    const now = new Date();
    const status = getScheduleStatus(schedules, now);
    renderStatus(status);
    announceChange(previousStatus, status);
    announceRemaining(previousStatus, status);
    previousStatus = status;
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

function speak(text) {
    if (!voiceEnabled) {
        return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ja-JP';
    utterance.onstart = () => {
        speechBubbleEl.textContent = text;
    };
    speechSynthesis.speak(utterance);
}

function startVoice() {
    const now = new Date();
    const status = getScheduleStatus(schedules, now);
    if (status.state === 'finished' || status.state === 'none') {
        return;
    }
    voiceEnabled = true;
    speak('いっしょにがんばろう');
    if (status.state === 'running') {
        speak(`今は${status.currentSchedule.title}の時間だよ。残りあと${status.remainingMinutes}分だよ`);
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

setInterval(checkStatus, 1000);
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        checkStatus();
    }
});

startNowBtn.addEventListener('click', startNow);

characterBtn.addEventListener('click', startVoice);