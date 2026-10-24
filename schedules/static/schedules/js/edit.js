window.addEventListener('pageshow', (event) => {
  if (event.persisted) {
    location.reload();
  }
});

function toMinutes(time) {
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
}
function toTimeString(minutes) {
  const total = ((minutes % 1440) + 1440) % 1440;
  const h = Math.floor(total / 60);
  const m = total % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}
function getShiftTargets(base, excludeRow) {
  const rows = document.querySelectorAll('.schedule-row:not(.hidden)');
  const targets = Array.from(rows).filter((row) => {
    const startInput = row.querySelector('input[name$="-start_time"]');
    return row !== excludeRow && startInput.value && toMinutes(startInput.value) >= base;
  });
  return targets;
}
function shiftRows(base, minutes, excludeRow) {
  const targets = getShiftTargets(base, excludeRow);
  const outOfRange = targets.some((row) => {
    const startInput = row.querySelector('input[name$="-start_time"]');
    const newStart = toMinutes(startInput.value) + minutes;
    return newStart < 0 || newStart >= 1440;
  });
  if (outOfRange) {
    showToast('日付が変わっちゃうから、ずらせないよ', 'error');
    return false;
  }
  targets.forEach((row) => {
    const startInput = row.querySelector('input[name$="-start_time"]');
    const endInput = row.querySelector('input[name$="-end_time"]');
    startInput.value = toTimeString(toMinutes(startInput.value) + minutes);
    if (endInput.value) {
      endInput.value = toTimeString(toMinutes(endInput.value) + minutes);
    }
    startInput.defaultValue = startInput.value;
    endInput.defaultValue = endInput.value;
    row.querySelector('.shift-notice').classList.add('hidden');
    updateSummary(row);
  });
  return true;
}

function updateShiftNotice(row) {
  const startInput = row.querySelector('input[name$="-start_time"]');
  const endInput = row.querySelector('input[name$="-end_time"]');
  const shiftNotice = row.querySelector('.shift-notice');
  const shiftNoticeText = row.querySelector('.shift-notice-text');
  const autoShiftBtn = row.querySelector('.auto-shift-btn');
  if (!endInput.defaultValue || !startInput.value || !endInput.value) {
    shiftNotice.classList.add('hidden');
    return;
  }
  const startDiff = toMinutes(startInput.value) - toMinutes(startInput.defaultValue);
  const endDiff = toMinutes(endInput.value) - toMinutes(endInput.defaultValue);
  let minutes;
  if (endDiff !== 0) {
    minutes = endDiff;
  } else {
    minutes = startDiff;
  }
  if (minutes === 0) {
    shiftNotice.classList.add('hidden');
    return;
  }
  const base = toMinutes(endInput.defaultValue);
  const targets = getShiftTargets(base, row);
  if (targets.length === 0) {
    shiftNotice.classList.add('hidden');
    return;
  }
  autoShiftBtn.dataset.minutes = minutes;
  if (minutes > 0) {
    shiftNoticeText.textContent = `このあとの${targets.length}件も${minutes}分うしろにずらす？`;
  } else if (minutes < 0) {
    shiftNoticeText.textContent = `このあとの${targets.length}件も${-minutes}分まえにずらす？`;
  }
  shiftNotice.classList.remove('hidden');
}

function updateSummary(row) {
  const titleEl = row.querySelector('input[name$="-title"]');
  const startTimeEl = row.querySelector('input[name$="-start_time"]');
  const endTimeEl = row.querySelector('input[name$="-end_time"]');
  const timeText = `${startTimeEl.value} - ${endTimeEl.value}`;

  let durationText = '';
  if (startTimeEl.value && endTimeEl.value) {
    let durationMinutes = toMinutes(endTimeEl.value) - toMinutes(startTimeEl.value);
    if (durationMinutes < 0) {
      durationMinutes += 1440;
    }
    durationText = `${durationMinutes}分`;
  }
  row.querySelector('.summary-time').textContent = timeText;
  row.querySelector('.summary-title').textContent = titleEl.value;
  row.querySelector('.summary-duration').textContent = durationText;
  row.querySelector('.editor-duration').textContent = durationText;
}

function openRow(row) {
  const rows = document.querySelectorAll('.schedule-row.is-open');
  for (const el of rows) {
    if (!closeRow(el)) {
      return;
    }
  }
  row.querySelector('.row-summary').classList.add('hidden');
  row.querySelector('.row-editor').classList.remove('hidden');
  row.classList.add('is-open');      
}

function validateRow(row) {
  const titleInput = row.querySelector('input[name$="-title"]');
  const startInput = row.querySelector('input[name$="-start_time"]');
  const endInput = row.querySelector('input[name$="-end_time"]');
  const errors = [];
  if (!titleInput.value.trim()) {
    errors.push('タスク名を入れてね');
  }
  if (!startInput.value) {
    errors.push('開始時刻を入れてね');
  }
  if (!endInput.value) {
    errors.push('終了時刻を入れてね');
  }
  if (startInput.value && endInput.value && startInput.value === endInput.value) {
    errors.push('開始時刻と終了時刻は一緒にはできないよ');
  }
  return errors;
}

function closeRow(row) {
  const errors = validateRow(row);
  const rowErrors = row.querySelector('.row-errors');
  if (errors.length > 0) {
    rowErrors.replaceChildren();
    errors.forEach((error) => {
      const p = document.createElement('p');
      p.className = 'field-error';
      p.textContent = error;
      rowErrors.append(p);
    });
    return false;
  }
  rowErrors.replaceChildren();
  row.removeAttribute('data-error');
  const rowCard = row.querySelector('.row-card')
  rowCard.classList.remove('border-rose-mark');
  rowCard.classList.add('border-[#E2DAEE]');
  const summaryError = row.querySelector('.summary-error');
  if (summaryError) {
    summaryError.remove();
  }
  updateSummary(row);
  updateShiftNotice(row);
  row.querySelector('.row-editor').classList.add('hidden');
  row.querySelector('.row-summary').classList.remove('hidden');
  row.classList.remove('is-open');
  sortRows();
  return true;
}

function sortRows() {
  const rows = Array.from(document.querySelectorAll('.schedule-row'));

  rows.sort((a, b) => {
    const aStart = a.querySelector('input[name$="-start_time"]').value;
    const bStart = b.querySelector('input[name$="-start_time"]').value;
    if (!aStart && !bStart) {
      return 0;
    } else if (!aStart) {
      return 1;
    } else if (!bStart) {
      return -1;
    } else {
      return toMinutes(aStart) - toMinutes(bStart);
    }
  });
  const addBtn = document.querySelector('.add-btn');
  rows.forEach((row)=> {
    addBtn.before(row);
  });
}

const form = document.getElementById('edit-form');

form.addEventListener('click', (event) => {
  const addBtn = event.target.closest('.add-btn');
  const summaryBtn = event.target.closest('.row-summary');
  const closeBtn = event.target.closest('.close-btn');
  const deleteBtn = event.target.closest('.delete-btn');
  const autoShiftBtn = event.target.closest('.auto-shift-btn');
  const keepBtn = event.target.closest('.keep-btn');
  if (addBtn) {
    const totalInput = document.getElementById('id_form-TOTAL_FORMS');
    const index = Number(totalInput.value);
    const emptyHtml = document.getElementById('empty-form').innerHTML;
    const html = emptyHtml.replaceAll('__prefix__', index);
    addBtn.insertAdjacentHTML('beforebegin', html);
    totalInput.value = index + 1;
    const newRow = addBtn.previousElementSibling;
    const emptyMessageEl = document.getElementById('empty-message');
    if (emptyMessageEl) {
      emptyMessageEl.classList.add('hidden');
    }
    openRow(newRow);

  }
  if (summaryBtn) {
    const row = summaryBtn.closest('.schedule-row');
    openRow(row);
  }
  if (closeBtn) {
    const row = closeBtn.closest('.schedule-row');
    closeRow(row);
  }
  if (deleteBtn) {
    const ok = confirm('本当に削除しますか？');
    if (ok) {
      const row = deleteBtn.closest('.schedule-row');
      const deleteInput = row.querySelector('input[name$="-DELETE"]');
      deleteInput.checked = true;
      row.classList.add('hidden');
    }
  }
  if (autoShiftBtn) {
    const row = autoShiftBtn.closest('.schedule-row');
    const startInput = row.querySelector('input[name$="-start_time"]');
    const endInput = row.querySelector('input[name$="-end_time"]');
    const minutes = Number(autoShiftBtn.dataset.minutes);
    const base = toMinutes(endInput.defaultValue);
    const ok = shiftRows(base, minutes, row);
    const shiftNotice = row.querySelector('.shift-notice');
    if (ok) {
      startInput.defaultValue = startInput.value;
      endInput.defaultValue = endInput.value;
      shiftNotice.classList.add('hidden');
    }
  }
  if (keepBtn) {
    const row = keepBtn.closest('.schedule-row');
    const startInput = row.querySelector('input[name$="-start_time"]');
    const endInput = row.querySelector('input[name$="-end_time"]');
    startInput.defaultValue = startInput.value;
    endInput.defaultValue = endInput.value;
    keepBtn.closest('.shift-notice').classList.add('hidden');
  }
});

const restartBtn = document.getElementById('restart-btn');
const restartDialog = document.getElementById('restart-dialog');
const restartNewBtn = document.getElementById('restart-new-btn');
const clearForm = document.getElementById('clear-form');
const restartCancelBtn = document.getElementById('restart-cancel-btn');
if (restartBtn) {
  restartBtn.addEventListener('click', () => {
    const num = Number(restartBtn.dataset.savedCount);
    if (num >= 1) {
      restartDialog.showModal();
    } else {
      const ok = confirm('予定を保存せずに入力ページに戻ってよいですか？');
      if (ok) {
        location.href=restartBtn.dataset.restartUrl;
      }
    }
  });
}
clearForm.addEventListener('submit', (event) => {
  const ok = confirm('今日の予定を全て削除して、入力ページに戻ってよいですか？');
  if (!ok) {
    event.preventDefault();
    restartDialog.close();
  }
});
restartNewBtn.addEventListener('click', () => {
  const ok = confirm('今入れた予定を保存せずに入力ページに戻ってよいですか？');
  if (ok) {
    location.href=restartBtn.dataset.restartUrl;
  } else {
    restartDialog.close();
  }
});
restartCancelBtn.addEventListener('click', () => {
  restartDialog.close();
});

document.addEventListener('click', (event) => {
  if (!event.target.closest('.row-card') && !event.target.closest('.add-btn')) {
    document.querySelectorAll('.schedule-row.is-open').forEach((row) => {
      closeRow(row);
    });
  }
});
document.querySelectorAll('.schedule-row').forEach((row) => {
  updateSummary(row);
});
sortRows();

const rows = document.querySelectorAll('.schedule-row:not(.hidden)');
const firstRow = Array.from(rows).filter((row) => {
  const endInput = row.querySelector('input[name$="-end_time"]');
  return row.hasAttribute('data-error') || !endInput.value;
});

if (firstRow) {
  openRow(firstRow);
}