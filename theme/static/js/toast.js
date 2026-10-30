function showToast(message, type= 'info') {
  const box = document.createElement('div');
  box.className = 'fixed top-4 left-1/2 -translate-x-1/2 w-[calc(100%-44px)] max-w-[240px] z-50 flex flex-col gap-2 transition-opacity duration-500';

  const p = document.createElement('p');
  p.className = 'text-center rounded-[16px] px-4 py-3 text-[12.5px] shadow-[0_6px_18px_rgba(91,83,115,0.15)] '
    + (type === 'error' ? 'bg-[#F3E4EE] text-[#C0708F]' : 'bg-[#EFE9F8] text-[#6B5B93]');
  p.textContent = message;

  box.appendChild(p);
  document.body.appendChild(box);

  setTimeout(() => {
    box.classList.add('opacity-0');
    box.addEventListener('transitionend', () => box.remove(), {once: true});
  }, 3500);
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-auto-dismiss]').forEach((el) => {
    setTimeout(() => {
      el.classList.add('opacity-0');
      el.addEventListener('transitionend', () => el.remove(), { once: true });
    }, 3500);
  });
});
