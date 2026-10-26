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
const timelineEl = document.getElementById('timeline');
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
    renderStatus(status);
    updateTimeline(status, now);
    announceChange(previousStatus, status);
    announceRemaining(previousStatus, status);
    scrollTimeline(previousStatus, status);
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

checkStatus();

setInterval(checkStatus, 1000);
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        checkStatus();
    }
});

startNowBtn.addEventListener('click', startNow);

characterBtn.addEventListener('click', startVoice);