// キャラクターのアニメーション無効化
setRandomEnabled(false);

// 表示に動きを付ける
const revealEls = document.querySelectorAll('.reveal');
const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
        if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
        }
    }
}, { threshold: 0.25 });
for (const element of revealEls) {
    observer.observe(element);
}