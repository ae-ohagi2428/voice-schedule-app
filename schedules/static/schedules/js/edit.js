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

function getRange(row) {
  const startInput = row.querySelector('input[name$="-start_time"]');
  const endInput = row.querySelector('input[name$="-end_time"]');
  if (!startInput.value || !endInput.value) {
    return null;
  }
  const startMinutes = toMinutes(startInput.value);
  let endMinutes = toMinutes(endInput.value);
  if (endMinutes < startMinutes) {
    endMinutes += 1440;
  }
  return {start: startMinutes, end: endMinutes};
}

function getDuration(startValue, endValue) {
  if (!startValue || !endValue) {
    return null;
  }
  let minutes = toMinutes(endValue) - toMinutes(startValue);
  if (minutes < 0) {
    minutes += 1440;
  }
  return minutes;
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
  const timeText = `${startTimeEl.value} ～ ${endTimeEl.value}`;
  let durationText = '';
  const minutes = getDuration(startTimeEl.value, endTimeEl.value);
  if (minutes !== null) {
    durationText = `${minutes}分`;
  }
  row.querySelector('.summary-time').textContent = timeText;
  row.querySelector('.summary-title').textContent = titleEl.value;
  row.querySelector('.summary-duration').textContent = durationText;
  updateEditorDuration(row);
}

function updateEditorDuration(row) {
  const startInput = row.querySelector('input[name$="-start_time"]');
  const endInput = row.querySelector('input[name$="-end_time"]');
  const editorDuration = row.querySelector('.editor-duration');
  const duration = getDuration(startInput.value, endInput.value);
  const defaultDuration = getDuration(startInput.defaultValue, endInput.defaultValue);
  editorDuration.replaceChildren();
  if (!duration) {
    return;
  }
  if (defaultDuration === null || duration === defaultDuration) {
    editorDuration.textContent = `${duration}分`;
  } else {
    const diff = duration - defaultDuration;
    let diffText = '';
    if (diff > 0) {
      diffText = `（+${diff}分）`;
    } else {
      diffText = `（-${-diff}分）`;
    }
    const span = document.createElement('span');
    span.className = 'text-rose-mark font-bold';
    span.textContent = diffText;
    editorDuration.append(`${duration}分`, ' ', span);
  }
}

function shakeRow(row) {
  const rowCard = row.querySelector('.row-card');
  row.scrollIntoView({ behavior: 'smooth', block: 'center' });
  setTimeout(() => {
    rowCard.classList.add('is-shaking');
    setTimeout(() => {
      rowCard.classList.remove('is-shaking');
    }, 400);
  }, 300);
  
}

function openRow(row) {
  const openedRow = document.querySelector('.schedule-row.is-open');
  if (openedRow) {
    shakeRow(openedRow);
    return;
  }
  const titleInput = row.querySelector('input[name$="-title"]');
  const startInput = row.querySelector('input[name$="-start_time"]');
  const endInput = row.querySelector('input[name$="-end_time"]');
  row.dataset.openTitle = titleInput.value;
  row.dataset.openStart = startInput.value;
  row.dataset.openEnd = endInput.value;
  row.querySelector('.row-summary').classList.add('hidden');
  row.querySelector('.row-editor').classList.remove('hidden');
  row.classList.add('is-open');
}

function setErrorMark(row, on) {
  const rowCard = row.querySelector('.row-card');
  const summaryError = row.querySelector('.summary-error');
  if (on) {
    rowCard.classList.add('border-rose-mark');
    rowCard.classList.remove('border-[#E2DAEE]');
    summaryError.classList.remove('hidden');
  } else {
    rowCard.classList.remove('border-rose-mark');
    rowCard.classList.add('border-[#E2DAEE]');
    summaryError.classList.add('hidden');
  }
}

function updateOverlapMarks() {
  const rows = Array.from(document.querySelectorAll('.schedule-row:not(.hidden)'));
  rows.forEach((row) => {
    const overlapTexts = [];
    const overlapError = row.querySelector('.overlap-error');
    const rowRange = getRange(row);
    rows.forEach((other) => {
      if (other === row) {
        return;
      }
      const otherRange = getRange(other);
      const otherTitle = other.querySelector('input[name$="-title"]');
      const otherStart = other.querySelector('input[name$="-start_time"]');
      const otherEnd = other.querySelector('input[name$="-end_time"]');
      if ((rowRange !== null && otherRange !== null) && (
        rowRange.start < otherRange.end && otherRange.start < rowRange.end)) {
        overlapTexts.push(`${otherTitle.value}(${otherStart.value}～${otherEnd.value})`);
      }
    });
    if (overlapTexts.length > 0) {
      overlapError.textContent = `${overlapTexts.join('、')}と時間が重なってるみたい。重ならない時間に直してね`;
      overlapError.classList.remove('hidden');
    } else {
      overlapError.classList.add('hidden');
    }
    setErrorMark(row, overlapTexts.length > 0 || row.hasAttribute('data-error'));
  });
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

function collapseRow(row) {
  updateSummary(row);
  updateShiftNotice(row);
  row.querySelector('.row-editor').classList.add('hidden');
  row.querySelector('.row-summary').classList.remove('hidden');
  row.classList.remove('is-open');
  sortRows();
  updateOverlapMarks();
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
  setErrorMark(row, false);
  collapseRow(row);
  return true;
}

function cancelRow(row) {
  const titleInput = row.querySelector('input[name$="-title"]');
  const startInput = row.querySelector('input[name$="-start_time"]');
  const endInput = row.querySelector('input[name$="-end_time"]');
  if (!row.dataset.openTitle && !row.dataset.openStart && !row.dataset.openEnd) {
    row.querySelector('input[name$="-DELETE"]').checked = true;
    row.classList.add('hidden');
    row.classList.remove('is-open');
    updateOverlapMarks();
    return;
  } else {
    titleInput.value = row.dataset.openTitle;
    startInput.value = row.dataset.openStart;
    endInput.value = row.dataset.openEnd;
    row.querySelector('.row-errors').replaceChildren();
    collapseRow(row);
  }
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
  const cancelBtn = event.target.closest('.cancel-btn');
  const deleteBtn = event.target.closest('.delete-btn');
  const autoShiftBtn = event.target.closest('.auto-shift-btn');
  const keepBtn = event.target.closest('.keep-btn');
  if (addBtn) {
    const openedRow = document.querySelector('.schedule-row.is-open');
    if (openedRow) {
      shakeRow(openedRow);
      return;
    }
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
  if (cancelBtn) {
    const row = cancelBtn.closest('.schedule-row');
    cancelRow(row);
  }
  if (deleteBtn) {
    const ok = confirm('本当に削除しますか？');
    if (ok) {
      const row = deleteBtn.closest('.schedule-row');
      const deleteInput = row.querySelector('input[name$="-DELETE"]');
      deleteInput.checked = true;
      row.classList.add('hidden');
      updateOverlapMarks();
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
      updateOverlapMarks();
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

form.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter') {
    return;
  } else if (event.isComposing) {
    return;
  } else if (event.target.tagName !== 'INPUT') {
    return;
  }
  const scheduleRow = event.target.closest('.schedule-row');
  event.preventDefault();
  closeRow(scheduleRow);
});

form.addEventListener('input', (event) => {
  const input = event.target;
  if (!input.name.endsWith('-start_time') && !input.name.endsWith('-end_time')) {
    return;
  }
  const row = input.closest('.schedule-row');
  updateEditorDuration(row);
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

document.querySelectorAll('.schedule-row').forEach((row) => {
  updateSummary(row);
});
sortRows();
updateOverlapMarks();

const rows = document.querySelectorAll('.schedule-row:not(.hidden)');
const firstRow = Array.from(rows).find((row) => {
  const endInput = row.querySelector('input[name$="-end_time"]');
  return row.hasAttribute('data-error') || !endInput.value;
});

if (firstRow) {
  openRow(firstRow);
}