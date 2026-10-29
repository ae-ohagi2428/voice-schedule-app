/* =========================================================
   設定（ミリ秒）
   ========================================================= */
const RANDOM_MIN     = 60000;  // 呼吸・歌う・寝る・うなずくが始まるまでの最短時間（ふだんがこの時間続いたら）
const RANDOM_MAX     = 120000; // 呼吸・歌う・寝る・うなずくが始まるまでの最長時間
const BREATH_LENGTH  = 16000;  // 呼吸の長さ（CSS の 4s × 4回）
const LAUGH_LENGTH   = 2600;   // 笑う動きの長さ（CSS の 2.6s と同じ）
const SING_LENGTH    = 12000;  // 歌う動きの長さ（CSS の 12s と同じ）
const SLEEP_LENGTH   = 22000;  // 寝る動きの長さ（CSS の 22s と同じ）
const NOTICE_LENGTH  = 6000;   // お知らせの長さ（CSS の 6s と同じ）
const WAKE_LENGTH    = 2200;   // 寝ているときにタップして起きる動きの長さ（CSS の 2.2s と同じ）
const NOD_LENGTH     = 3000;   // うなずく動きの長さ（CSS の 3s と同じ）
const BLEND_LENGTH   = 600;    // 状態が切り替わるときに、傾きなどを元に戻す時間
const MOUTH_MIN      = 4000;   // ふだんの口を開けたり閉じたりする間隔の、最短時間
const MOUTH_MAX      = 10000;  // ふだんの口を開けたり閉じたりする間隔の、最長時間
 
const chara = document.getElementById('chara');
const swayWrap = chara.querySelector('.sway-wrap');
 
// 状態が切り替わるときに、なめらかにつなぐパーツ（回転・伸び縮みしているもの）
const movingParts = chara.querySelectorAll('.sway-wrap, .head, .hands, .antenna, .ear-left, .ear-right, .fluff, .face, .fx-z');
 
let state = 'idle';
let pending = null;      // 区切りのいいときまで待っている、次の状態（{ next, length }）
let randomTimer = null;  // 呼吸・歌う・寝る・うなずくが始まるまでのタイマー
let endTimer = null;     // 決まった長さの動きが終わるまでのタイマー
let mouthTimer = null;   // ふだんの口を開けたり閉じたりするタイマー
let randomEnabled = true; // 呼吸・歌う・寝る・うなずくをしてよいか（一日終了・予定なしの日は false）
 
/*
  状態を切り替える関数
  1. 今の傾き・伸び縮みを読み取っておく
  2. chara のクラスを「state-〇〇」に付け替える（CSS のアニメーションが切り替わる）
  3. 読み取っておいた傾きから元の形へ、BLEND_LENGTH かけて戻す（パッと元に戻って見えないように）
     composite: 'add' は「CSS のアニメーションの上に足す」という指定。
     新しい状態の動き（笑ったときの触角など）を止めずに、前の傾きだけがだんだん消えていく
  4. 状態が変わったことを、chara の「statechange」というイベントで知らせる
     （task_run.js が受け取って、寝る・呼吸のセリフを吹き出しに出す）
*/
function setState(next) {
  const before = Array.from(movingParts, (el) => getComputedStyle(el).transform);
  state = next;
  pending = null;
  chara.className = 'chara state-' + next;
  movingParts.forEach((el, i) => {
    if (before[i] !== 'none') {
      el.animate([{ transform: before[i] }, { transform: 'none' }],
                 { duration: BLEND_LENGTH, easing: 'ease-in-out', composite: 'add' });
    }
  });
  chara.dispatchEvent(new CustomEvent('statechange', { detail: { state: next } }));
}
 
// タイマーを全部止める関数
function clearTimers() {
  clearTimeout(randomTimer);
  clearTimeout(endTimer);
  clearTimeout(mouthTimer);
}
 
/*
  ふだんの口を、MOUTH_MIN〜MOUTH_MAX のランダムな間隔で開けたり閉じたりする関数
  chara に「mouth-shut」クラスを付けると口を閉じ、外すと口を開ける（見た目は CSS で決めている）
  ふだんの状態のときだけ動く。ほかの状態に切り替わると、setState で className ごと付け替えるのでクラスも外れる
*/
function scheduleMouth() {
  const wait = MOUTH_MIN + Math.random() * (MOUTH_MAX - MOUTH_MIN);
  mouthTimer = setTimeout(() => {
    if (state === 'idle') chara.classList.toggle('mouth-shut');
    scheduleMouth();
  }, wait);
}
 
/*
  次の状態を「予約」する関数（呼吸・歌う・寝る・うなずくに使う）
  ふだんのときは、体の揺れの1回分が終わって、まっすぐの形に戻るまで待ってから切り替える。
  実際の切り替えは、下の animationiteration / animationend のところで行う
*/
function requestState(next, length) {
  pending = { next, length };
}
 
/*
  体の箱（.sway-wrap）のアニメーションが1回分終わるたびに呼ばれる
  animationiteration：くり返しのアニメーションが1回終わったとき
  animationend      ：1回だけのアニメーション（揺れ始め用の -in）が終わったとき
  e.target が体の箱のときだけ見る（耳や触角のアニメーションの区切りでも、同じイベントが届くため）
*/
function onSwayBoundary(e) {
  if (e.target !== swayWrap || !pending) return;
  const { next, length } = pending;
  startOnce(next, length);
}
swayWrap.addEventListener('animationiteration', onSwayBoundary);
swayWrap.addEventListener('animationend', onSwayBoundary);
 
/*
  呼吸・歌う・寝る・うなずくのタイマーをセットする関数
  ふだんが RANDOM_MIN〜RANDOM_MAX のどこかまで続いたら、4つのうち1つを4分の1ずつの確率で予約する
*/
function scheduleRandom() {
  if (!randomEnabled) return;
  const wait = RANDOM_MIN + Math.random() * (RANDOM_MAX - RANDOM_MIN);
  randomTimer = setTimeout(() => {
    const r = Math.random();
    if (r < 0.25) {
      requestState('breath', BREATH_LENGTH);
    } else if (r < 0.5) {
      requestState('sing', SING_LENGTH);
    } else if (r < 0.75) {
      requestState('sleep', SLEEP_LENGTH);
    } else {
      requestState('nod', NOD_LENGTH);
    }
  }, wait);
}
 
/*
  呼吸・歌う・寝る・うなずくを、してよいかどうかを切りかえる関数。task_run.js から呼ぶ
  false にすると、待っているタイマーと予約を取り消す。今している動きは最後まで続け、
  ふだんに戻ったあとは、scheduleRandom が何もしないので、次の動きは始まらない
  true に戻したときは、ふだんの状態ならタイマーをセットし直す
  毎秒同じ値で呼ばれても、値が変わらないときは何もしない
*/
function setRandomEnabled(enabled) {
  if (enabled === randomEnabled) return;
  randomEnabled = enabled;
  clearTimeout(randomTimer);
  pending = null;
  if (enabled && state === 'idle') scheduleRandom();
}
 
// ふだんの状態に戻す関数（呼吸・歌う・寝る・うなずくのタイマーと、口のタイマーを新しくセットする）
function toIdle() {
  clearTimers();
  setState('idle');
  scheduleRandom();
  scheduleMouth();
}
 
// 決まった長さだけ動いて、終わったらふだんに戻る関数（笑う・呼吸・歌う・寝る・起きる・うなずく・お知らせ）
function startOnce(next, length) {
  clearTimers();
  setState(next);
  endTimer = setTimeout(toIdle, length);
}
 
// タップしたときの反応。task_run.js から呼ぶ（笑う・起きる途中のタップは無視する）
function reactToTap() {
  if (state === 'laugh' || state === 'wake') return;
  if (state === 'sleep') {
    startOnce('wake', WAKE_LENGTH);   // 寝ているときは「！」が出て起きる
  } else {
    startOnce('laugh', LAUGH_LENGTH);
  }
}
 
// ページを開いたら、ふだんの状態から始める
toIdle();