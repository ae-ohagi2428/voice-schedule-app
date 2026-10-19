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
    return {state, currentSchedule, nextSchedule};
}

function formatTime(date) {
    const hours = date.getHours();
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
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
    return renderStatus(status);
}

setInterval(checkStatus, 1000);
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        checkStatus();
    }
});

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
startNowBtn.addEventListener('click', startNow);