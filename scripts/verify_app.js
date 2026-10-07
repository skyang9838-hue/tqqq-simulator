/* app.js 를 최소 DOM 스텁 위에서 실제로 실행해, 화면에 나갈 숫자를 뽑아
   Python 계산(rolling.py)과 대조한다. */
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const app = fs.readFileSync(path.join(ROOT, "web", "app.js"), "utf8");
const data = fs.readFileSync(path.join(ROOT, "data", "web_data.json"), "utf8");
const coef = { b: 1.03982, c: 0.001505 };
const payload = JSON.parse(data);
payload.coef = coef;
payload.built = "test";

const store = {};           // id -> {innerHTML, textContent}
const listeners = {};

function makeCtx() {
  const noop = () => {};
  return new Proxy({}, {
    get: (t, k) => {
      if (k === "measureText") return () => ({ width: 10 });
      if (k === "canvas") return { width: 900, height: 330 };
      return noop;
    },
    set: () => true,
  });
}

function makeEl(id) {
  const el = {
    id,
    _html: "", _text: "",
    style: {}, dataset: {},
    clientWidth: 900, clientHeight: 330,
    width: 900, height: 330,
    children: [],
    get innerHTML() { return this._html; },
    set innerHTML(v) { this._html = v; store[id] = v; },
    get textContent() { return this._text; },
    set textContent(v) { this._text = v; store[id] = v; },
    getContext: () => makeCtx(),
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 900, height: 330 }),
    addEventListener: (ev, fn) => { (listeners[id] = listeners[id] || {})[ev] = fn; },
    removeEventListener: () => {},
    querySelectorAll: () => [],
    setAttribute: () => {}, removeAttribute: () => {}, getAttribute: () => null,
    closest: () => null,
    scrollIntoView: () => {},
    setSelectionRange: () => {},
    appendChild: () => {},
    offsetWidth: 200,
    selectionStart: 0,
    value: "",
  };
  return el;
}

const els = {};
const INPUT_DEFAULTS = { "f-init": "100,000,000", "f-monthly": "1,500,000", "f-goal": "500,000,000" };

global.document = {
  documentElement: { style: {} },
  getElementById: (id) => {
    if (!els[id]) {
      els[id] = makeEl(id);
      if (INPUT_DEFAULTS[id] !== undefined) els[id].value = INPUT_DEFAULTS[id];
      if (id === "tqqq-data") els[id]._text = JSON.stringify(payload);
    }
    return els[id];
  },
  addEventListener: () => {},
};
global.getComputedStyle = () => ({ getPropertyValue: () => "#000000" });
global.window = {
  devicePixelRatio: 1,
  matchMedia: () => ({ addEventListener: () => {}, addListener: () => {} }),
};
global.requestAnimationFrame = (fn) => { fn(); return 1; };
global.cancelAnimationFrame = () => {};
global.ResizeObserver = class { observe() {} };
global.MutationObserver = class { observe() {} };

// 실행
eval(app);

/* ---------- 결과 추출 ---------- */
function stripTags(s) { return String(s).replace(/<[^>]*>/g, "|").replace(/\|+/g, "|"); }

console.log("=".repeat(78));
console.log("app.js 실행 결과 (초기 1억 + 월 150만, 10년, 목표 5억)");
console.log("=".repeat(78));
console.log("\n[헤드라인 스탯]");
console.log(stripTags(store["stats"]));
console.log("\n[목표 도달]");
console.log(stripTags(store["goal"]));
console.log("\n[최악 표 첫 3행]");
const rowsHtml = String(store["t-worst"] || "").split("<tr").slice(1, 4);
rowsHtml.forEach((r) => console.log("  " + stripTags(r).slice(0, 150)));
console.log("\n[분포]");
console.log(stripTags(store["dist"]).slice(0, 700));
console.log("\n[선택 케이스 요약]");
console.log(stripTags(store["path-stats"]));
console.log("\n[메타]");
["m-range", "m-days", "m-real", "mm-b", "mm-c"].forEach((k) =>
  console.log("  " + k + " = " + store[k]));
