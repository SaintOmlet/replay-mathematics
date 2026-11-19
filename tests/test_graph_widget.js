"use strict";

const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const vm = require("node:vm");

class UIEvent {
  constructor(type, options = {}) {
    Object.assign(this, { type, bubbles: false, pointerId: 1 }, options);
  }
  preventDefault() { this.defaultPrevented = true; }
}

class Element {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.events = new Map();
    this.attributes = new Map();
    this.dataset = {};
    this.disabled = false;
    this.clientWidth = 600;
    this.clientHeight = 360;
    this.width = 600;
    this.height = 360;
    this._value = "";
    this._text = "";
  }
  append(...children) {
    children.forEach(child => { child.parentNode = this; this.children.push(child); });
  }
  replaceChildren(...children) {
    this.children.forEach(child => { child.parentNode = null; });
    this.children = [];
    this.append(...children);
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(" "); }
  set value(value) { this._value = String(value); }
  get value() { return this._value; }
  get validity() {
    const value = Number(this.value);
    const quotient = (value - Number(this.min)) / Number(this.step);
    return { valid: this.value !== "" && Number.isFinite(value) && value >= Number(this.min)
      && value <= Number(this.max) && Math.abs(quotient - Math.round(quotient)) < 1e-9 };
  }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  addEventListener(name, callback) {
    if (!this.events.has(name)) this.events.set(name, []);
    this.events.get(name).push(callback);
  }
  dispatchEvent(event) {
    if (!event.target) event.target = this;
    event.currentTarget = this;
    (this.events.get(event.type) || []).forEach(callback => callback(event));
    if (event.bubbles && this.parentNode) this.parentNode.dispatchEvent(event);
  }
  getContext() { return { clearRect() {} }; }
  getBoundingClientRect() { return { left: 0, top: 0 }; }
  setPointerCapture(id) { this.capturedPointer = id; }
}

function descendants(element) {
  return element.children.flatMap(child => [child, ...descendants(child)]);
}

function environment(xScale=20) {
  const pendingFrames = new Map();
  const observers = [];
  const plots = [];
  let nextFrame = 1;
  const context = {
    window: { MathLab: {
      createPlot() {
        const plot = {
          drawn: [],
          axes() { return [-10, 10]; },
          curve(fn, domain, style) { this.drawn.push({ fn, domain, style }); },
          point() {},
          screen(x, y) { return [200 + xScale*x, 200 - 10*y]; },
          coordinates(x, y) { return [(x - 200)/xScale, (200 - y)/10]; },
        };
        plots.push(plot);
        return plot;
      },
    } },
    document: { createElement: tag => new Element(tag) },
    Event: UIEvent,
    Intl,
    requestAnimationFrame(callback) { const id=nextFrame++; pendingFrames.set(id,callback); return id; },
    cancelAnimationFrame(id) { pendingFrames.delete(id); },
    ResizeObserver: class {
      constructor(callback) { this.callback=callback; this.disconnected=false; observers.push(this); }
      observe(element) { this.element=element; }
      disconnect() { this.disconnected=true; }
    },
  };
  vm.createContext(context);
  vm.runInContext(readFileSync("frontend/graph-exercise.js", "utf8"), context);
  return {
    api: context.window.ReplayGraphExercise,
    observers, plots, pendingFrames,
    flush() {
      const frames = [...pendingFrames.values()]; pendingFrames.clear();
      frames.forEach(callback => callback());
    },
  };
}

const line = {
  model: "line", kind: "graph", parameters: [
    {key:"m", label:"Наклон", min:-6, max:6, step:.5, initial:0},
    {key:"b", label:"Пересечение", min:-15, max:15, step:.5, initial:-8},
  ],
  view: {xmin:-10,xmax:10,ymin:-30,ymax:30},
};
const parabola = {
  ...line, model:"parabola", parameters: [
    {key:"a",label:"Растяжение",min:-6,max:6,step:.5,initial:1},
    {key:"h",label:"Вершина x",min:-10,max:10,step:.5,initial:0},
    {key:"k",label:"Вершина y",min:-15,max:15,step:.5,initial:-8},
  ],
};

function mount(env, spec=line, draft="") {
  const form = new Element("form");
  const editor = new Element("div");
  const answer = new Element("input");
  answer.value=draft;
  form.append(editor,answer);
  const drafts=[];
  form.addEventListener("input",()=>drafts.push(answer.value));
  const dispose=env.api.mount(editor,spec,answer);
  env.flush();
  const all=descendants(editor);
  return {
    form, editor, answer, drafts, dispose,
    number: key=>all.find(element=>element.dataset.graphParameter===key),
    slider: key=>all.find(element=>element.type==="range"&&element.attributes.get("aria-label").startsWith(spec.parameters.find(p=>p.key===key).label)),
    canvas: all.find(element=>element.tagName==="CANVAS"),
    controls: all.find(element=>element.tagName==="FIELDSET"),
    expression: all.find(element=>element.tagName==="OUTPUT"),
    reset: all.find(element=>element.tagName==="BUTTON"),
    table: all.find(element=>element.tagName==="TABLE"),
  };
}

const env=environment();
const first=mount(env,line,'{"m":1.5,"b":2}');
assert.deepEqual(JSON.parse(first.answer.value),{m:1.5,b:2});
first.number("m").value="-2.5";
first.number("m").dispatchEvent(new UIEvent("input",{bubbles:true}));
env.flush();
assert.equal(first.slider("m").value,"-2.5");
assert.deepEqual(JSON.parse(first.drafts.at(-1)),{m:-2.5,b:2},"Typed input must save the current hidden graph answer through the normal form event");
assert.match(first.expression.textContent, /[-−]2,5x/);
first.slider("b").value="4.5";
first.slider("b").dispatchEvent(new UIEvent("input",{bubbles:true}));
env.flush();
assert.equal(first.number("b").value,"4.5");
assert.deepEqual(JSON.parse(first.drafts.at(-1)),{m:-2.5,b:4.5});

first.number("m").value="";
first.number("m").dispatchEvent(new UIEvent("input",{bubbles:true}));
assert.deepEqual(JSON.parse(first.answer.value),{m:null,b:4.5},"Blank parameter must remain invalid, rather than become zero");
const blankDraft=first.answer.value;
const restoredBlank=mount(env,line,blankDraft);
assert.equal(restoredBlank.number("m").value,"","Reload must preserve a partially completed graph draft");
assert.deepEqual(JSON.parse(restoredBlank.answer.value),{m:null,b:4.5});

first.reset.dispatchEvent(new UIEvent("click",{bubbles:true}));
env.flush();
assert.deepEqual(JSON.parse(first.answer.value),{m:0,b:-8});
assert.deepEqual(JSON.parse(first.drafts.at(-1)),{m:0,b:-8},"Reset must save its result so a reload does not restore the old curve");
const separateQuestion=mount(env,line);
assert.deepEqual(JSON.parse(separateQuestion.answer.value),{m:0,b:-8},"A new widget cannot inherit another question's state");
const invalidStep=mount(env,line,'{"m":0.25,"b":2}');
assert.equal(invalidStep.number("m").value,"0.25","An invalid partial draft must remain editable after reload");
assert.equal(invalidStep.number("m").validity.valid,false);
assert.deepEqual(JSON.parse(invalidStep.answer.value),{m:.25,b:2});

function pointer(widget,type,x,y) {
  widget.canvas.dispatchEvent(new UIEvent(type,{clientX:200+20*x,clientY:200-10*y}));
  env.flush();
}
pointer(first,"pointerdown",0,-8);
pointer(first,"pointermove",0,2);
pointer(first,"pointerup",0,2);
assert.deepEqual(JSON.parse(first.drafts.at(-1)),{m:0,b:2});
pointer(first,"pointerdown",1,2);
pointer(first,"pointermove",1,5);
pointer(first,"pointerup",1,5);
assert.deepEqual(JSON.parse(first.drafts.at(-1)),{m:3,b:2},"Dragging the slope handle must submit the visible curve's parameters");
const beforeExpiry=first.answer.value;
first.controls.disabled=true;
pointer(first,"pointerdown",0,2);
pointer(first,"pointermove",0,8);
assert.equal(first.answer.value,beforeExpiry,"Expired question cannot be changed through dragging");

const mobileEnv=environment(10);
const mobile=mount(mobileEnv,line);
mobile.canvas.dispatchEvent(new UIEvent("pointerdown",{clientX:210,clientY:280}));
mobile.canvas.dispatchEvent(new UIEvent("pointermove",{clientX:210,clientY:250}));
mobileEnv.flush();
assert.deepEqual(JSON.parse(mobile.answer.value),{m:3,b:-8},"Nearby handles on a narrow viewport must select the closest handle, rather than always the first");

const quadratic=mount(env,parabola);
pointer(quadratic,"pointerdown",0,-8);
pointer(quadratic,"pointermove",2,-1);
pointer(quadratic,"pointerup",2,-1);
assert.deepEqual(JSON.parse(quadratic.drafts.at(-1)),{a:1,h:2,k:-1});
pointer(quadratic,"pointerdown",3,0);
pointer(quadratic,"pointermove",3,3);
pointer(quadratic,"pointerup",3,3);
assert.deepEqual(JSON.parse(quadratic.drafts.at(-1)),{a:4,h:2,k:-1});

const reference=mount(env,{...line,reference:{model:"line",parameters:{m:4,b:7}}});
assert.equal(reference.expression.textContent,"y = 0x − 8","Reference formula must remain concealed in recovery tasks");
assert.match(reference.table.textContent,/Заданный график/);
assert(!reference.expression.textContent.includes("4x"));
assert.equal(env.plots.at(-1).drawn[0].fn(2),15);
assert.equal(env.plots.at(-1).drawn[1].fn(2),-8);

reference.number("m").value="1";
reference.number("m").dispatchEvent(new UIEvent("input",{bubbles:true}));
assert(env.pendingFrames.size>0);
reference.dispose();
assert.equal(env.pendingFrames.size,0,"Leaving a question must cancel queued canvas updates");
assert(env.observers.at(-1).disconnected,"Leaving a question must disconnect the resize observer");

// Exercise actual plot coordinate transforms independently from the widget stub.
const plotContext={window:{devicePixelRatio:1},Intl,document:{}};
vm.createContext(plotContext);
vm.runInContext(readFileSync("frontend/graph.js","utf8"),plotContext);
const canvas=new Element("canvas");
const drawing=new Proxy({}, {get:()=>()=>{}});
const actualPlot=plotContext.window.MathLab.createPlot(canvas,drawing);
actualPlot.axes([-10,10],[-30,30],false,line.view);
for(const [x,y] of [[-10,-30],[0,0],[2.5,-7],[10,30]]) {
  const [px,py]=actualPlot.screen(x,y);
  const [rx,ry]=actualPlot.coordinates(px,py);
  assert(Math.abs(rx-x)<1e-10&&Math.abs(ry-y)<1e-10,"Dragging coordinate conversion must invert the displayed axes");
}

console.log("Graph widget input, drafts, reset, drag, expiry, reference and cleanup checks passed.");
