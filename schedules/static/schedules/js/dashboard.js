const timelineEl = document.getElementById('timeline');
const nowRowEl = document.getElementById('timeline-now');

if (timelineEl) {
    if (nowRowEl) {
        timelineEl.scrollTop = nowRowEl.offsetTop - (timelineEl.clientHeight - nowRowEl.offsetHeight) / 2;
    } else {
        timelineEl.scrollTop = timelineEl.scrollHeight;
    }
}