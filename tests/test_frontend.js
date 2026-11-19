"use strict";

const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const vm = require("node:vm");

const storage = new Map();
const fakePage = { querySelector: () => null, querySelectorAll: () => [] };
const context = {
  document: {
    querySelector(selector) {
      if (selector === "#page") return fakePage;
      if (selector === "#alert") return { textContent: "", hidden: true };
      if (selector === ".skip") return { addEventListener() {} };
      return null;
    },
  },
  window: { ReplayMath: { inline: value => String(value ?? "") } },
  location: { hash: "#home" },
  sessionStorage: {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: key => storage.delete(key),
  },
  addEventListener() {},
  Intl, Date, console,
};
const source = readFileSync("frontend/app.js", "utf8").replace(/\ninit\(\);\s*$/, "\n");
vm.createContext(context);
vm.runInContext(source, context);

const evaluate = expression => vm.runInContext(expression, context);
evaluate("session = {id:'test-session',index:0,question:{id:'linear:2'}}");
evaluate("saveDraft(session,'3/4')");
assert.equal(evaluate("restoreDraft(session)"), "3/4");
assert.equal(evaluate("restoreDraft({...session,index:1})"), "");
assert.equal(evaluate("restoreDraft({...session,question:{id:'linear:3'}})"), "");
evaluate("saveDraft({...session,index:1,question:{id:'linear:7'}},'17')");
evaluate("removeDraft(session)");
assert.equal(evaluate("restoreDraft(session)"), "");
assert.equal(evaluate("restoreDraft({...session,index:1,question:{id:'linear:7'}})"), "17");
evaluate("saveDraft(session,'never submitted')");
evaluate("restoreDraft({...session,expired:true})");
assert.equal(evaluate("restoreDraft(session)"), "");
evaluate("saveDraft({...session,expired:true},'late')");
assert.equal(evaluate("restoreDraft(session)"), "");

assert.match(evaluate("answerFields({response:{kind:'pair'}},'ru')"), /2;3/);
assert.match(evaluate("answerFields({response:{kind:'interval'}},'ru')"), /\(2;5\]/);
assert.match(evaluate("answerFields({response:{kind:'fraction'}},'ru')"), /точную несократимую дробь/);
assert.match(evaluate("answerFields({response:{kind:'sequence',parts:['First','Second']}},'ru')"), /c,a,b/);
const sequence = evaluate("answerFields({response:{kind:'sequence',options:[{value:'c',label:'Провести окружность из A'},{value:'a',label:'Выбрать одинаковый радиус'},{value:'b',label:'Соединить точки пересечения'}]}},'ru')");
assert.match(sequence, /<strong>c\.<\/strong> Провести окружность из A/);
assert.match(sequence, /<strong>a\.<\/strong> Выбрать одинаковый радиус/);
assert.match(sequence, /<strong>b\.<\/strong> Соединить точки пересечения/);
assert.doesNotMatch(sequence, /type="radio"/, "An ordering task must not become a single-choice answer");
assert.match(evaluate("answerFields({response:{kind:'choice',options:[{value:'s1',label:'One'}]}},'ru')"), /value="s1"/);
assert.match(evaluate("answerFields({options:['1/3','1/2']},'en')"), /value="1\/3"/);

async function checkSubmissionAndExpiry() {
  const events = {};
  const input = {
    value: "", type: "text", attrs: {}, disabled: false,
    setAttribute(key, value) { this.attrs[key] = value; },
    removeAttribute(key) { delete this.attrs[key]; },
    focus() { context.lastFocus = "answer"; },
  };
  const button = { disabled: false };
  const error = { textContent: "", hidden: true };
  const timer = { textContent: "", classList: { toggle() {} } };
  const hints = { innerHTML: "" };
  const hintButton = { setAttribute() {}, getAttribute() { return "false"; }, addEventListener() {} };
  const form = {
    querySelectorAll: () => [input, button],
    addEventListener(name, callback) { events[name] = callback; },
  };
  const plainControl = { addEventListener() {}, focus() {}, scrollIntoView() {} };
  const confirmationEvents = {};
  const confirmationButtons = {
    "[data-cancel]": { addEventListener(name, callback) {confirmationEvents.cancel=callback;}, focus() {context.lastFocus="cancel";} },
    "[data-confirm]": { addEventListener(name, callback) {confirmationEvents.confirm=callback;} },
  };
  const confirmation = { hidden:true, querySelector: selector=>confirmationButtons[selector], scrollIntoView() {} };
  const skip = { ...plainControl, addEventListener(name, callback) {events.skip=callback;}, focus() {context.lastFocus="skip";} };
  fakePage.setAttribute = () => {};
  fakePage.querySelector = selector => ({
    "#answer-form": form, "#answer-error": error, "#answer": input,
    "#timer": timer, "#hints": hints, "#hint-question": hintButton,
    "#skip-question": skip, "#next-question": plainControl,
    "#session-confirmation": confirmation,
    "#finish-session": plainControl, ".feedback": plainControl, ".prompt": plainControl,
  })[selector] || null;
  fakePage.querySelectorAll = selector => selector === "#answer-form input[name=answer]" ? [input] : [];
  context.FormData = class { get() { return input.value; } };
  context.performance = { now: () => 1000 };
  context.setInterval = () => 1;
  context.clearInterval = () => {};
  let response;
  const requests = [];
  const normalFetch = async (url, options) => {
    requests.push({ url, options });
    return { ok: response.ok, json: async () => response.data };
  };
  context.fetch = normalFetch;
  const settle = () => new Promise(resolve => setImmediate(resolve));
  evaluate("session={id:'submit-session',mode:'practice',lang:'ru',index:0,total:1,question:{id:'linear:2',title:'Линейное уравнение',prompt:'Find x'},hints:[]}");
  evaluate("renderQuestion(session)");
  input.value="3/4";
  events.input();
  response = { ok: false, data: { error: "Ошибка формата" } };
  events.submit({ preventDefault() {}, currentTarget: form, submitter: button });
  await settle();
  assert.equal(evaluate("restoreDraft(session)"),"3/4","Rejected submission must preserve its draft");
  assert.equal(error.textContent,"Ошибка формата");
  assert.equal(input.attrs["aria-invalid"],"true");
  assert.equal(context.lastFocus,"answer");

  const countBeforeCancel = requests.length;
  events.skip({ currentTarget:skip });
  assert.equal(requests.length,countBeforeCancel,"Opening confirmation cannot submit a skipped answer");
  assert.equal(confirmation.hidden,false);
  assert.equal(context.lastFocus,"cancel");
  confirmationEvents.cancel();
  assert.equal(confirmation.hidden,true);
  assert.equal(context.lastFocus,"skip");
  assert.equal(requests.length,countBeforeCancel,"Cancelling skip cannot record an attempt");

  const accepted = evaluate("({...session,feedback:{correct:true,answer:'3/4',solution:[]}})");
  response = { ok: true, data: accepted };
  events.submit({ preventDefault() {}, currentTarget: form, submitter: button });
  await settle();
  assert(!storage.has("replay-answer-v2:submit-session:0:linear:2"),"Successful ACK clears only submitted draft");

  evaluate("session={id:'stale-session',mode:'practice',lang:'ru',index:0,total:1,question:{id:'linear:2'},hints:[]}; renderQuestion(session)");
  error.textContent="";
  let releaseRequest;
  context.fetch=()=>new Promise(resolve=>{releaseRequest=resolve;});
  input.value="3/";
  events.submit({preventDefault(){},currentTarget:form,submitter:button});
  evaluate("routeVersion+=1");
  context.lastFocus="other-page";
  releaseRequest({ok:false,json:async()=>({error:"Outdated error"})});
  await settle();
  assert.equal(error.textContent,"","Stale request failure must not write into a different route");
  assert.equal(context.lastFocus,"other-page");
  context.fetch=normalFetch;

  evaluate("session={id:'expired-session',mode:'test',index:0,total:2,question:{id:'linear:1'},remainingSeconds:0}");
  evaluate("saveDraft(session,'late answer')");
  response = { ok: true, data: evaluate("({...session,index:1,question:{id:'linear:5'},remainingSeconds:240})") };
  evaluate("renderQuestion = function(state,focus) { lastRendered=state; lastRenderedFocus=focus; }; startTimer(session)");
  await settle();
  const expiredRequest = requests.at(-1);
  assert.equal(expiredRequest.url,"/api/sessions/expired-session/expire");
  assert.equal(expiredRequest.options.method,"POST");
  assert.deepEqual(JSON.parse(expiredRequest.options.body),{index:0});
  assert(!storage.has("replay-answer-v2:expired-session:0:linear:1"));
  assert.equal(context.lastRendered.index,1);
  assert.equal(context.lastRenderedFocus,true);
}

checkSubmissionAndExpiry().then(() => {
  console.log("Frontend drafts, ACK/error focus, expiry POST and structured-response checks passed.");
}).catch(error => {
  console.error(error);
  process.exitCode=1;
});
