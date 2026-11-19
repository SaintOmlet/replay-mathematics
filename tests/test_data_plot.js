"use strict";

const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const vm = require("node:vm");

// Real widget code and real event listeners, using a small in-memory DOM.
// This test requires neither a browser session nor external packages.
class UIEvent {
  constructor(type, options = {}) {
    Object.assign(this, { type, bubbles: false }, options);
  }
  preventDefault() { this.defaultPrevented = true; }
}

class Element {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.attributes = new Map();
    this.events = new Map();
    this._text = "";
    this._value = "";
  }
  append(...children) {
    children.forEach(child => { child.parentNode = this; this.children.push(child); });
  }
  replaceChildren(...children) {
    this.children.forEach(child => { child.parentNode = null; });
    this.children = [];
    this.append(...children);
  }
  set textContent(value) {
    this._text = String(value);
    this.replaceChildren();
  }
  get textContent() {
    return this._text + this.children.map(child => child.textContent).join(" ");
  }
  set value(value) { this._value = String(value); }
  get value() { return this._value; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  addEventListener(name, callback) {
    if (!this.events.has(name)) this.events.set(name, []);
    this.events.get(name).push(callback);
  }
  removeEventListener(name, callback) {
    this.events.set(name, (this.events.get(name) || []).filter(value => value !== callback));
  }
  dispatchEvent(event) {
    if (!event.target) event.target = this;
    event.currentTarget = this;
    [...(this.events.get(event.type) || [])].forEach(callback => callback(event));
    if (event.bubbles && this.parentNode) this.parentNode.dispatchEvent(event);
    return !event.defaultPrevented;
  }
}

function descendants(element) {
  return element.children.flatMap(child => [child, ...descendants(child)]);
}

function environment() {
  const context = {
    window: {},
    document: {
      createElement: tag => new Element(tag),
      createElementNS: (namespace, tag) => {
        assert.equal(namespace, "http://www.w3.org/2000/svg");
        return new Element(tag);
      },
    },
    Event: UIEvent,
    Intl,
  };
  vm.createContext(context);
  vm.runInContext(readFileSync("frontend/data-plot.js", "utf8"), context);
  return context.window.ReplayDataPlot;
}

function mount(api, spec, draft = "") {
  const form = new Element("form");
  const editor = new Element("div");
  const answer = new Element("input");
  answer.type = "hidden";
  answer.value = draft;
  form.append(editor, answer);
  const drafts = [];
  const answerEvents = [];
  form.addEventListener("input", event => drafts.push({ value: answer.value, target: event.target }));
  answer.addEventListener("input", event => answerEvents.push(event));
  const dispose = api.mount(editor, spec, answer);
  const all = descendants(editor);
  const svg = all.find(value => value.tagName === "SVG");
  const inputs = all.filter(value => value.tagName === "INPUT");
  return {
    editor, answer, form, drafts, answerEvents, dispose, inputs, svg,
    alternative: all.find(value => value.attributes.get("aria-live") === "polite"),
    nodes: tag => svg ? descendants(svg).filter(value => value.tagName === tag.toUpperCase()) : [],
    input(index, value) {
      inputs[index].value = value;
      inputs[index].dispatchEvent(new UIEvent("input", { bubbles: true }));
    },
  };
}

const histogram = {
  kind: "data_plot", mode: "histogram", axis: "Плотность частоты",
  labels: ["[−3;−1)", "[−1;2)", "[2;6]"], bins: [-3, -1, 2, 6],
};
const polygon = {
  kind: "data_plot", mode: "frequency_polygon", axis: "Частота",
  labels: ["−2", "0", "5", "6"], x: [-2, 0, 5, 6],
};
const table = {
  kind: "data_plot", mode: "frequency_table", axis: "Частота",
  labels: ["2", "4", "7"],
};

function near(actual, expected, message) {
  assert(Math.abs(Number(actual) - expected) < 1e-9, message || `${actual} differs from ${expected}`);
}

function attr(node, key) { return node.attributes.get(key); }
function lineData(widget) { return widget.nodes("line").filter(node => attr(node, "stroke") === "#315d78"); }

const api = environment();

// Empty state must be genuinely unanswered and must not save a mount event.
const empty = mount(api, histogram);
assert.equal(empty.answer.value, "");
assert.equal(empty.inputs.length, 3);
assert(empty.inputs.every(input => input.value === ""));
assert.equal(empty.drafts.length, 0);
assert.equal(empty.answerEvents.length, 0);
assert.equal(empty.nodes("rect").length, 0, "Blank values must not silently become zero-height bars");
assert.match(empty.alternative.textContent, /не задано/);
assert.equal(attr(empty.svg, "role"), "img");
assert.equal(attr(empty.svg, "aria-label"), "Твоя гистограмма");
empty.inputs.forEach((input, index) => {
  assert.equal(input.required, true);
  assert.equal(input.maxLength, 40);
  assert.equal(attr(input, "aria-label"), histogram.axis + ": " + histogram.labels[index]);
  assert.match(attr(input, "aria-describedby"), /answer-error/);
  assert.equal(attr(input, "data-graph-parameter"), String(index));
});

// Preserve the exact spelling of a fraction and every other row in the answer.
empty.input(0, "5/3");
assert.deepEqual(JSON.parse(empty.answer.value), ["5/3", "", ""]);
assert.deepEqual(JSON.parse(empty.drafts.at(-1).value), ["5/3", "", ""]);
assert.equal(empty.answerEvents.at(-1).bubbles, true);
assert(empty.drafts.some(event => event.target === empty.answer), "The hidden answer event must reach the enclosing form draft listener");
empty.input(1, "3,5");
empty.input(2, "0");
assert.deepEqual(JSON.parse(empty.answer.value), ["5/3", "3,5", "0"]);
assert.match(empty.alternative.textContent, /5\/3/);
assert.match(empty.alternative.textContent, /3,5/);

// Widths come from numerical bin boundaries, not equally spaced table rows.
const bars = empty.nodes("rect");
assert.equal(bars.length, 3);
const horizontal = value => 48 + (value + 3) / 9 * 404;
for (let index = 0; index < bars.length; index++) {
  near(attr(bars[index], "x"), horizontal(histogram.bins[index]));
  near(attr(bars[index], "width"), (histogram.bins[index + 1] - histogram.bins[index]) / 9 * 404);
}
near(Number(attr(bars[1], "width")) / Number(attr(bars[0], "width")), 3 / 2);
near(Number(attr(bars[2], "width")) / Number(attr(bars[0], "width")), 2);
near(attr(bars[0], "height"), (5 / 3) / 5 * 160, "Fractional height must be evaluated rather than truncated to an integer");
near(attr(bars[1], "height"), 3.5 / 5 * 160);
near(attr(bars[2], "height"), 0);
for (let index = 0; index < bars.length - 1; index++) {
  near(Number(attr(bars[index], "x")) + Number(attr(bars[index], "width")), attr(bars[index + 1], "x"), "Adjacent histogram bins must meet without artificial gaps");
}

const restored = mount(api, histogram, empty.answer.value);
assert.deepEqual(restored.inputs.map(input => input.value), ["5/3", "3,5", "0"]);
assert.deepEqual(JSON.parse(restored.answer.value), ["5/3", "3,5", "0"]);
assert.equal(restored.drafts.length, 0, "Restoring must not create a new user draft event");
restored.input(1, "");
assert.deepEqual(JSON.parse(restored.answer.value), ["5/3", "", "0"]);
const partial = mount(api, histogram, restored.answer.value);
assert.equal(partial.inputs[1].value, "");
assert.equal(partial.nodes("rect").length, 2);
partial.input(0, "");
partial.input(2, "");
assert.equal(partial.answer.value, "", "Clearing every row must clear the saved answer");
assert.equal(partial.nodes("rect").length, 0);

// Unusable JSON is reset predictably; drafts from another question do not fit.
for (const draft of ["{broken", "null", "{}", '["2"]', '["2","4","6","8"]']) {
  const invalid = mount(api, histogram, draft);
  assert.equal(invalid.answer.value, "");
  assert(invalid.inputs.every(input => input.value === ""));
}
assert.equal(mount(api, histogram).answer.value, "", "New questions must not inherit another widget's data");

// Nonuniform x values must set the true point positions and segment lengths.
const poly = mount(api, polygon, '["2","4","3","1"]');
assert.equal(poly.nodes("circle").length, 4);
assert.equal(lineData(poly).length, 3);
const points = poly.nodes("circle");
const px = x => 48 + (x + 2) / 8 * 404;
points.forEach((point, index) => near(attr(point, "cx"), px(polygon.x[index])));
near(Number(attr(points[2], "cx")) - Number(attr(points[1], "cx")), 5 / 8 * 404);
near((Number(attr(points[2], "cx")) - Number(attr(points[1], "cx"))) /
  (Number(attr(points[1], "cx")) - Number(attr(points[0], "cx"))), 5 / 2);
lineData(poly).forEach((line, index) => {
  near(attr(line, "x1"), px(polygon.x[index]));
  near(attr(line, "x2"), px(polygon.x[index + 1]));
});
assert.equal(attr(poly.svg, "aria-label"), "Твой полигон частот");

// Invalid/partial text stays editable, never draws NaN, and cannot bridge gaps.
poly.input(2, "abc");
assert.deepEqual(JSON.parse(poly.answer.value), ["2", "4", "abc", "1"]);
assert.equal(poly.nodes("circle").length, 3);
assert.equal(lineData(poly).length, 1, "A missing point must break both adjacent segments");
near(attr(lineData(poly)[0], "x1"), px(-2));
near(attr(lineData(poly)[0], "x2"), px(0));
assert.match(poly.alternative.textContent, /abc/);
const invalidRestored = mount(api, polygon, poly.answer.value);
assert.equal(invalidRestored.inputs[2].value, "abc", "Reload must preserve an invalid draft for correction");
for (const text of ["", " ", "abc", "-1", "−2", "1/0", "0/0", "Infinity", "NaN", "10001", "1e3", "1/2/3", "<script>alert(1)</script>"]) {
  assert.equal(api.number(text), null, text);
  poly.input(2, text);
  assert.equal(poly.nodes("circle").length, 3, text);
  assert.equal(lineData(poly).length, 1, text);
  for (const node of descendants(poly.svg)) {
    for (const value of node.attributes.values()) assert(!/NaN|Infinity/.test(value));
  }
}
assert.equal(poly.nodes("script").length, 0, "Input must appear as text rather than become executable markup");
for (const [text, expected] of [["0",0], ["5/3",5/3], ["1 / 2",.5], ["3,5",3.5], [".25",.25], ["+2",2], ["10000",10000]]) {
  near(api.number(text), expected, text);
}
poly.input(2, "5/3");
assert.equal(poly.nodes("circle").length, 4);
assert.equal(lineData(poly).length, 3);

// Table-only answers serialize all rows without creating a decorative chart.
const frequency = mount(api, table);
assert.equal(frequency.svg, undefined);
assert.equal(frequency.alternative, undefined);
frequency.input(0, "2");
frequency.input(1, "3");
frequency.input(2, "7");
assert.deepEqual(JSON.parse(frequency.answer.value), ["2", "3", "7"]);
assert.equal(frequency.answerEvents.length, 3);
assert.deepEqual(mount(api, table, frequency.answer.value).inputs.map(input => input.value), ["2", "3", "7"]);

// Disposal removes the widget's listeners, making detached controls inert.
for (const widget of [empty, restored, partial, poly, frequency]) {
  const answer = widget.answer.value;
  const emitted = widget.answerEvents.length;
  assert.equal(typeof widget.dispose, "function");
  widget.dispose();
  widget.dispose();
  widget.inputs.forEach(input => assert.equal((input.events.get("input") || []).length, 0));
  widget.input(0, "999");
  assert.equal(widget.answer.value, answer);
  assert.equal(widget.answerEvents.length, emitted);
}
assert.equal(api.mount(null, histogram, new Element("input")), undefined);
assert.equal(api.mount(new Element("div"), histogram, null), undefined);

console.log("Data plot blank/restore, fractions, full answers, event bubbling, unequal bins/x, invalid text and cleanup checks passed.");
