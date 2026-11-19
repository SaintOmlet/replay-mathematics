"use strict";

const page = document.querySelector("#page");
const alertBox = document.querySelector("#alert");
const names = {home:"Темы", topics:"Темы", test:"Тест", progress:"Прогресс", sat:"SAT Math", lesson:"Урок", session:"Задачи",guide:"Как пользоваться"};
const modeNames = {practice:"Практика", test:"Тест", review:"Работа над ошибками"};
const levelNames = {easy:"Лёгкий", medium:"Средний", hard:"Сложный", mixed:"Все уровни"};
const links = {
  skills:"https://satsuite.collegeboard.org/practice/student-question-bank/math",
  bank:"https://satsuite.collegeboard.org/practice/student-question-bank",
  bluebook:"https://satsuite.collegeboard.org/practice/practice-tests/bluebook",
  desmos:"https://www.desmos.com/testing/cb-sat/graphing"
};
const demos = {
  lines:{type:"lines",m1:2,b1:1,m2:-1,b2:4},
  systems:{type:"lines",m1:1,b1:2,m2:-2,b2:5},
  quadratics:{type:"quadratic",a:1,b:-6,c:9,level:3},
  triangles:{type:"triangle",base:8,height:5}
};
let model = {topics:[], progress:null, coachAvailable:false};
let grade = 0;
let session = null;
let busy = false;
let clock = null;
let graphCleanup = [];
let routeVersion = 0;

const esc = (value = "") => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
const fmt = number => new Intl.NumberFormat("ru-RU").format(number ?? 0);
const pct = (a,b) => b ? Math.round(100*a/b)+"%" : "—";
const topicById = id => model.topics.find(t => t.id === id);
const activePath = () => location.hash.slice(1) || "home";
const sessionPath = id => "sessions/" + encodeURIComponent(id);
const mathText = value => window.ReplayMath.inline(value);
const assistanceNames = {independent:"Самостоятельно",assisted:"С помощью или повторно",unknown:"Помощь не учитывалась"};
const draftPrefix = "replay-answer-v2:";

function draftKey(s) {
  return draftPrefix+s.id+":"+s.index+":"+s.question.id;
}

function saveDraft(s, value) {
  if(!s.question||s.feedback||s.finished||s.expired) return;
  try {
    if(value) sessionStorage.setItem(draftKey(s),JSON.stringify({value,updatedAt:Date.now()}));
    else sessionStorage.removeItem(draftKey(s));
  } catch { /* Practice remains usable when browser storage is unavailable. */ }
}

function removeDraft(s) {
  if(!s.question) return;
  try { sessionStorage.removeItem(draftKey(s)); } catch {}
}

function restoreDraft(s) {
  if(s.expired||s.feedback) { removeDraft(s); return ""; }
  try {
    const record=JSON.parse(sessionStorage.getItem(draftKey(s))||"null");
    if(!record||typeof record.value!=="string"||record.value.length>500||Date.now()-record.updatedAt>7*86400000) {
      removeDraft(s);
      return "";
    }
    return record.value;
  } catch { removeDraft(s); return ""; }
}

async function request(path, data) {
  const res = await fetch("/api/" + path, data === undefined ? {} : {
    method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data)
  });
  let value;
  try { value = await res.json(); } catch { throw new Error("Сервер вернул неожиданный ответ."); }
  if (!res.ok) throw new Error(value.error || "Не удалось выполнить действие.");
  return value;
}

function message(text) {
  if (alertBox.textContent === text) return;
  alertBox.textContent = text;
  alertBox.hidden = !text;
}

async function action(work, source, onError) {
  if (busy) return;
  busy = true;
  message("");
  if (source) source.disabled = true;
  try { await work(); }
  catch (error) {
    if(onError) onError(error.message);
    else message(error.message);
  }
  finally { busy = false; if(source) source.disabled = false; }
}

function setView(html) {
  graphCleanup.splice(0).forEach(dispose => dispose());
  page.innerHTML = html;
  page.setAttribute("aria-busy","false");
}

function focusTarget(selector, scroll=false) {
  const element=page.querySelector(selector);
  element?.focus({preventScroll:true});
  if(scroll) element?.scrollIntoView({block:"nearest"});
}

function heading(title, body="", context="") {
  return '<header class="page-heading">'+(context?'<div class="context">'+context+'</div>':'')+
    '<h1 tabindex="-1">'+esc(title)+'</h1>'+(body?'<p>'+esc(body)+'</p>':'')+'</header>';
}

function routeLink(href,label,kind="secondary") {
  return '<a class="btn '+kind+'" href="#'+href+'">'+esc(label)+'</a>';
}

function external(href,label) {
  return '<a class="text-link" href="'+href+'" target="_blank" rel="noopener">'+esc(label)+'</a>';
}

function resumeStrip() {
  const sessions = model.progress?.activeSessions || (model.progress?.active?[model.progress.active]:[]);
  const rows=sessions.map(active=>'<div class="resume"><div><strong>'+esc(modeNames[active.mode])+(active.lang==="en"?' · SAT Math':'')+'</strong>'+
    '<span>'+esc(active.title||"")+(active.total?' · задача '+fmt(active.index+1)+' из '+fmt(active.total):'')+'</span>'+
    (active.expired?'<small class="negative">Время текущей задачи истекло</small>':
      active.secondsPerQuestion?'<small class="muted">Таймер продолжает идти</small>':'')+
    '</div>'+routeLink('session/'+encodeURIComponent(active.id),'Продолжить','secondary')+'</div>');
  return rows.length?'<section class="surface resume-list" aria-label="Незавершённые сессии"><h2>Продолжить обучение</h2>'+rows[0]+
    (rows.length>1?'<details class="resume-more"><summary>Остальные незавершённые занятия · '+fmt(rows.length-1)+'</summary>'+rows.slice(1).join("")+'</details>':'')+'</section>':'';
}

function learningPath() {
  const steps=model.progress?.recommendations||[];
  return steps.length?'<section class="surface learning-path" aria-labelledby="learning-path-title"><h2 class="section-label" id="learning-path-title">Следующие шаги</h2><ol>'+steps.map(step=>
    '<li><div><a class="text-link" href="#lesson/'+encodeURIComponent(step.topic)+'">'+esc(step.title)+'</a><p class="muted compact-copy">'+esc(step.reason)+'</p></div>'+
    (step.action==="practice"?'<button class="btn secondary compact" type="button" data-next-practice="'+esc(step.topic)+'">Решать</button>':routeLink('lesson/'+encodeURIComponent(step.topic),'Открыть урок','secondary compact'))+'</li>').join("")+'</ol></section>':'';
}

function bindLearningPath() {
  page.querySelectorAll("[data-next-practice]").forEach(button=>button.addEventListener("click",()=>startPractice(button.dataset.nextPractice,button)));
}

function countLabel(progress) {
  return fmt(progress.correct)+' из '+fmt(progress.answered)+' верно';
}

function renderTopics() {
  setView(heading("Темы по математике") + resumeStrip() + learningPath() +
    '<div class="filterbar"><div class="chips" aria-label="Класс">'+[[0,"Все классы"],[7,"7 класс"],[8,"8 класс"],[9,"9 класс"]]
      .map(([n,label])=>'<button class="chip" type="button" data-grade="'+n+'" aria-pressed="'+(n===grade)+'">'+label+'</button>').join("")+
    '</div><input type="search" class="field search" id="topic-search" aria-label="Поиск по темам" placeholder="Найти тему"></div>'+
    '<div id="topic-list"></div><p id="topic-status" class="sr-only" role="status"></p>');
  const input = page.querySelector("#topic-search");
  bindLearningPath();
  const list = page.querySelector("#topic-list");
  const stats = new Map((model.progress?.topics||[]).map(t=>[t.id,t]));
  function refresh() {
    const words=input.value.trim().toLocaleLowerCase("ru");
    const topics=model.topics.filter(t=>!t.satOnly&&(!grade||t.grade===grade)&&[t.title,t.description,t.section,t.sat].join(" ").toLocaleLowerCase("ru").includes(words));
    list.innerHTML=[7,8,9].map(n=>{
      const group=topics.filter(t=>t.grade===n);
      if(!group.length) return "";
      const sections=new Map();
      for(const t of group) {
        const key=t.section||"Школьная математика";
        if(!sections.has(key)) sections.set(key,[]);
        sections.get(key).push(t);
      }
      return '<section class="surface topic-section" aria-labelledby="grade-'+n+'"><h2 class="section-label" id="grade-'+n+'">'+n+' класс</h2>'+
        [...sections].map(([section,topicList])=>'<div class="topic-subsection"><h3>'+esc(section)+'</h3><ul class="topic-rows">'+topicList.map(t=>{
          const id=encodeURIComponent(t.id);
          const prior=stats.get(t.id);
          return '<li class="topic-row"><a class="topic-title" href="#lesson/'+id+'">'+esc(t.title)+'</a>'+
            (prior?.answered||prior?.lessonCompleted?'<span class="topic-progress">'+
              [prior.answered?countLabel(prior):"",prior.mastered?"Освоена":prior.lessonCompleted?"Урок завершён":""].filter(Boolean).join(" · ")+
              (prior.nextStep?'<small>'+esc(prior.nextStep)+'</small>':'')+
              '</span>':'')+
            '<button class="btn secondary compact" type="button" data-practice="'+id+'" aria-label="Задачи: '+esc(t.title)+'">Задачи</button></li>';
        }).join("")+'</ul></div>').join("")+'</section>';
    }).join("") || '<p class="empty">Подходящих тем нет. Измени запрос или класс.</p>';
    page.querySelector("#topic-status").textContent = "Найдено тем: "+topics.length;
  }
  input.addEventListener("input",refresh);
  page.querySelectorAll("[data-grade]").forEach(button=>button.addEventListener("click",()=>{
    grade = Number(button.dataset.grade);
    page.querySelectorAll("[data-grade]").forEach(el=>el.setAttribute("aria-pressed",String(Number(el.dataset.grade)===grade)));
    refresh();
  }));
  list.addEventListener("click",event=>{
    const button=event.target.closest("button[data-practice]");
    if(button) startPractice(decodeURIComponent(button.dataset.practice),button);
  });
  refresh();
}

function mountGraph(selector, graph) {
  const element=page.querySelector(selector);
  if (!element || !graph || !window.MathLab?.mount) return;
  const dispose=window.MathLab.mount(element,graph);
  if (typeof dispose === "function") graphCleanup.push(dispose);
}

function startPractice(id, source) {
  return startSession({mode:"practice",topics:[id],count:5,lang:topicById(id)?.satOnly?"en":"ru"},source);
}

function lesson(id, body) {
  const t=topicById(id);
  if(!t) return missing();
  const demo=body.graph||demos[id];
  const hasDiagram=window.ReplayGeometry?.has(id);
  const examples=body.examples||[];
  const mistakes=body.mistakes||[];
  const checks=body.checks||[];
  const practicePath=(t.satOnly?"sat/":"test/")+encodeURIComponent(id);
  const satApplications=(t.satApplications||[]).map(topicById).filter(Boolean);
  setView(heading(t.title,"",'<a class="text-link" href="#topics">Темы</a><span aria-hidden="true"> / </span>'+t.grade+' класс')+
    '<div class="layout"><article class="surface panel lesson-sections">'+
    (body.intro?'<p class="lesson-intro">'+mathText(body.intro)+'</p>':'')+
    '<section><h2>Теория</h2><div class="formula">'+mathText(body.formula)+'</div>'+solution(body.theory)+'</section>'+
    (demo?'<div id="lesson-graph"></div>':'')+
    (hasDiagram?'<div class="surface" id="lesson-diagram"></div>':'')+
    (examples.length?'<section><h2>Разобранные примеры</h2>'+examples.map(example=>
      '<div class="lesson-example"><p class="result-prompt"><strong>'+mathText(example.prompt)+'</strong></p>'+solution(example.steps)+'</div>').join("")+'</section>':'')+
    (mistakes.length?'<section><h2>Типичные ошибки</h2><ul class="steps">'+mistakes.map(item=>
      '<li><strong>'+mathText(item.error)+'</strong><p>'+mathText(item.explanation)+'</p></li>').join("")+'</ul></section>':'')+
    (checks.length?'<section><h2>Самопроверка</h2>'+checks.map((item,i)=>
      '<div class="lesson-check"><p>'+fmt(i+1)+'. '+mathText(item.prompt)+'</p>'+
      '<details><summary>Показать ответ</summary><p>'+mathText(item.answer)+'</p></details></div>').join("")+'</section>':'')+
    '<section class="lesson-end"><button class="btn secondary" type="button" id="complete-lesson" '+(body.completed?'disabled':'')+'>'+
    (body.completed?'Урок завершён':'Отметить урок завершённым')+'</button><p id="lesson-confirmation" class="muted" role="status"></p></section>'+
    '</article><aside class="surface panel stack"><h2>Задания</h2>'+
    '<button class="btn primary full" id="practice-start">Начать практику</button>'+
    routeLink(practicePath,"Тест по теме","secondary full")+
    '<p class="muted compact-copy">Практика: 5 задач с подсказками.</p>'+
    (satApplications.length?'<div class="separated stack"><h3>Применение в SAT</h3><p class="muted compact-copy">Задания на английском, разбор на русском.</p>'+satApplications.map(target=>
      routeLink('sat/'+encodeURIComponent(target.id),target.title,'secondary full')).join('')+
    external(links.skills,"Навыки College Board")+'</div>':'')+'</aside></div>');
  mountGraph("#lesson-graph",demo);
  if(hasDiagram) {
    const dispose=window.ReplayGeometry.mount(page.querySelector("#lesson-diagram"),id);
    if(typeof dispose==="function") graphCleanup.push(dispose);
  }
  page.querySelector("#practice-start").addEventListener("click",e=>startPractice(id,e.currentTarget));
  page.querySelector("#complete-lesson").addEventListener("click",event=>{
    const button=event.currentTarget;
    if(button.getAttribute("aria-disabled")==="true") return;
    action(async()=>{
      await request("lessons/"+encodeURIComponent(id)+"/complete",{});
      button.textContent="Урок завершён";
      button.setAttribute("aria-disabled","true");
      page.querySelector("#lesson-confirmation").textContent="Прохождение сохранено в прогрессе.";
    });
  });
}

function construct(id,isSat) {
  const available=model.topics.filter(t=>isSat?t.satReady:!t.satOnly);
  const selected=available.some(t=>t.id===id)?id:"";
  const firstGrade=topicById(selected)?.grade||7;
  const sections=[7,8,9].map(n=>'<details class="test-grade" data-test-grade="'+n+'"'+(n===firstGrade?' open':'')+
    '><summary>'+n+' класс <span class="muted grade-selection"></span></summary><fieldset class="topic-options"><legend class="sr-only">'+n+' класс</legend><div>'+
    available.filter(t=>t.grade===n).map(t=>'<label class="choice"><input name="topics" type="checkbox" value="'+esc(t.id)+'"'+
      (selected===t.id?" checked":"")+'><span>'+esc(t.title)+'</span></label>').join("")+'</div></fieldset></details>').join("");
  const topicPicker='<section class="surface panel" id="test-topics"><div class="section-head"><h2>Выбор тем</h2>'+
    '</div><div class="actions select-actions" aria-label="Быстрый выбор тем"><button type="button" class="btn plain compact" data-select="all">Все темы</button>'+
    [7,8,9].map(n=>'<button type="button" class="btn plain compact" data-select="'+n+'" aria-label="Выбрать темы за '+n+' класс">'+n+' класс</button>').join("")+
    '<button type="button" class="btn plain compact" data-select="clear">Снять выбор</button></div>'+sections+'</section>';
  const settings='<aside class="surface panel stack" id="test-settings"><h2>Настройки</h2>'+
    '<label class="setting">Количество задач<select class="field" name="count"><option value="3">3</option><option value="5" selected>5</option><option value="10">10</option><option value="15">15</option><option value="25">25</option><option value="40">40</option></select></label>'+
    '<label class="setting">Сложность<select class="field" name="difficulty">'+["mixed","easy","medium","hard"].map(value=>
      '<option value="'+value+'">'+levelNames[value]+'</option>').join("")+'</select></label>'+
    '<label class="setting">Время на задачу<select class="field" name="secondsPerQuestion"><option value="60">1 минута</option>'+
      '<option value="120">2 минуты</option><option value="240" selected>4 минуты</option><option value="360">6 минут</option>'+
      '<option value="">Без таймера</option></select></label>'+
    '<p class="muted compact-copy">Решения доступны после сдачи. Таймер текущей задачи продолжает идти при уходе со страницы.</p>'+
    '<p class="muted compact-copy" id="selected-count" role="status"></p>'+
    '<button class="btn primary full" type="submit">Начать тест</button>'+
    (isSat?'<div class="separated"><h3>Официальная практика</h3><ul class="link-list"><li>'+external(links.bank,"Банк заданий College Board")+
      '</li><li>'+external(links.bluebook,"Пробники Bluebook")+'</li><li>'+external(links.desmos,"Калькулятор SAT")+'</li></ul></div>':'')+
    '</aside>';
  setView(heading(isSat?"SAT Math":"Тест",isSat?"Учебные задания на английском, разбор на русском.":"")+
    (isSat?'<details class="surface panel"><summary>Материал для подготовки к SAT</summary><ul class="link-list">'+available.filter(t=>t.satOnly).map(t=>
      '<li><a class="text-link" href="#lesson/'+encodeURIComponent(t.id)+'">'+esc(t.title)+'</a></li>').join('')+'</ul><p class="muted compact-copy">Авторская практика по четырём областям SAT Math. Это не полный пробник экзамена и не прогноз балла.</p></details>':'')+
    '<form id="test-form" class="layout">'+settings+topicPicker+'</form>');
  const form=page.querySelector("#test-form");
  function updateSelected() {
    const selectedCount=form.querySelectorAll("input[name=topics]:checked").length;
    form.querySelector("#selected-count").textContent="Выбрано тем: "+selectedCount;
    form.querySelectorAll("[data-test-grade]").forEach(group=>{
      const count=group.querySelectorAll("input[name=topics]:checked").length;
      group.querySelector(".grade-selection").textContent=count?"· выбрано "+count:"";
    });
  }
  form.addEventListener("change",updateSelected);
  updateSelected();
  form.querySelectorAll("[data-select]").forEach(b=>b.addEventListener("click",()=>{
    const selection=b.dataset.select;
    form.querySelectorAll("input[name=topics]").forEach(input=>{
      if(selection==="clear") input.checked=false;
      else if(selection==="all"||String(topicById(input.value).grade)===selection) input.checked=true;
    });
    if(/^[789]$/.test(selection))
      form.querySelectorAll("[data-test-grade]").forEach(group=>{group.open=group.dataset.testGrade===selection;});
    updateSelected();
  }));
  form.addEventListener("submit",event=>{
    event.preventDefault();
    const data=new FormData(form);
    const topics=data.getAll("topics");
    if(!topics.length) {
      message("Выбери хотя бы одну тему.");
      const first=form.querySelector("input[name=topics]");
      if(first) {
        first.closest("details").open=true;
        first.focus();
      }
      return;
    }
    const duration=data.get("secondsPerQuestion");
    startSession({mode:"test",topics,count:Number(data.get("count")),lang:isSat?"en":"ru",
      difficulty:data.get("difficulty"),secondsPerQuestion:duration?Number(duration):null},event.submitter);
  });
}

function startSession(config, source) {
  const version=routeVersion;
  return action(async ()=>{
    const state=await request("sessions",config);
    if (version!==routeVersion) return;
    session=state;
    location.hash="session/"+encodeURIComponent(state.id);
  },source);
}

function timestamp(value) {
  if(!value) return "";
  const date=new Date(typeof value==="number"&&value<1e12?value*1000:value);
  return Number.isNaN(date.valueOf())?"":new Intl.DateTimeFormat("ru-RU",{dateStyle:"short",timeStyle:"short"}).format(date);
}

function durationLabel(seconds) {
  if(seconds===null||seconds===undefined) return "—";
  const minutes=Math.floor(seconds/60);
  const rest=seconds%60;
  return (minutes?fmt(minutes)+" мин ":"")+fmt(rest)+" сек";
}

function table(labels, rows) {
  return '<table class="data-table"><thead><tr>'+labels.map(label=>'<th scope="col">'+esc(label)+'</th>').join("")+
    '</tr></thead><tbody>'+rows.map(row=>'<tr><th scope="row">'+row[0]+'</th>'+row.slice(1).map(cell=>'<td>'+cell+'</td>').join("")+'</tr>').join("")+
    '</tbody></table>';
}

function progress() {
  const p=model.progress;
  const stats=(p.topics||[]).filter(t=>t.answered>0||t.lessonCompleted);
  const attempted=stats.filter(t=>t.independentAttempted>=3);
  const strong=attempted.filter(t=>t.independentCorrect/t.independentAttempted>=.8).sort((a,b)=>b.independentCorrect-a.independentCorrect).slice(0,4);
  const weak=attempted.filter(t=>t.independentCorrect/t.independentAttempted<.6).sort((a,b)=>b.mistakes-a.mistakes).slice(0,4);
  const labels=rows=>rows.map(t=>'<a class="text-link" href="#lesson/'+encodeURIComponent(t.id)+'">'+esc(topicById(t.id)?.title||t.id)+'</a>').join(", ");
  setView(heading("Прогресс")+resumeStrip()+learningPath()+
    '<section class="surface panel stack progress-summary" id="progress-summary"><h2>Освоение и точность</h2>'+
    '<dl class="progress-totals"><div><dt>Освоено тем</dt><dd>'+fmt(p.mastered)+' из '+fmt(model.topics.length)+' · '+pct(p.mastered,model.topics.length)+'</dd></div>'+
    '<div><dt>Завершено уроков</dt><dd>'+fmt(p.lessonsCompleted)+'</dd></div><div><dt>Точность ответов</dt><dd>'+pct(p.correct,p.answered)+
    (p.answered?' <span class="muted">('+countLabel(p)+')</span>':'')+'</dd></div></dl>'+
    '<details class="progress-rule"><summary>Когда тема считается освоенной</summary><p>После завершения урока нужны минимум шесть разных задач с самостоятельными ответами и точность от 80%, минимум три типа задач (или все, если их меньше трёх). Среди верных — две средние и одна сложная, если такие уровни есть в теме. Ответы с подсказками, наставником и повторы знакомых задач сохраняются отдельно. По старым попыткам самостоятельность неизвестна.</p></details>'+
    (p.mistakeCount?'<div class="actions"><button id="review-exact" class="btn primary">Повторить ошибочные задачи · '+fmt(p.mistakeCount)+'</button>'+
    '<button id="review-start" class="btn secondary">Новые задачи по ошибкам</button></div>':'')+'</section>'+
    '<div class="layout equal progress-block"><section class="surface panel stack"><h2>По классам</h2>'+
    table(["Класс","Уроки","Освоено","Точность"],p.grades.map(row=>[row.grade+" класс",
      fmt(row.lessons)+" / "+fmt(row.topics),fmt(row.mastered)+" / "+fmt(row.topics),pct(row.correct,row.answered)]))+'</section>'+
    '<section class="surface panel stack"><h2>По сложности</h2>'+
    table(["Уровень","Верно / всего","Точность"],p.levels.map(row=>[esc(levelNames[row.level]),
      fmt(row.correct)+" / "+fmt(row.answered),pct(row.correct,row.answered)]))+'</section></div>'+
    '<div class="layout equal progress-block"><section class="surface panel stack"><h2>Темы с активностью</h2>'+
    (stats.length?table(["Тема","Верно / всего","Урок"],stats.map(t=>[labels([t])+
      (t.nextStep?'<p class="muted compact-copy">'+esc(t.nextStep)+'</p>':'')+
      '<p class="attempt-types">'+fmt(t.independent||0)+' самостоятельно · '+fmt(t.assisted||0)+' с помощью или повторно'+
      (t.unknown?' · '+fmt(t.unknown)+' без учёта помощи':'')+'</p>',fmt(t.correct)+" / "+fmt(t.answered),
      t.mastered?"Освоена":t.lessonCompleted?"Завершён":"—"])):'<p class="empty">Ответов пока нет.</p>'+routeLink("topics","Выбрать тему"))+
    (strong.length?'<p><strong>Сильные:</strong> '+labels(strong)+'</p>':'')+
    (weak.length?'<p><strong>Требуют практики:</strong> '+labels(weak)+'</p>':'')+
    (!strong.length&&!weak.length&&stats.length?'<p class="muted compact-copy">Для оценки сильных и слабых тем нужны самостоятельные ответы минимум на три разных варианта по теме.</p>':'')+
    '</section><section class="surface panel stack"><h2>Завершённые сессии</h2>'+
    (p.recent.length?'<ul class="history-list">'+p.recent.map(r=>'<li><div><a class="text-link" href="#session/'+encodeURIComponent(r.id)+'">'+esc(modeNames[r.mode])+
      (r.lang==="en"?' · SAT Math':'')+'</a><small class="history-mode">'+esc((r.topics||[]).map(id=>topicById(id)?.title||id).join(', '))+'</small><span class="muted">'+esc(timestamp(r.finishedAt))+' · '+durationLabel(r.elapsedSeconds)+'</span></div><span>'+fmt(r.correct)+' / '+fmt(r.total)+'</span></li>').join("")+
      '</ul>':'<p class="empty">Завершённых сессий пока нет.</p>')+'</section></div>'+
    (p.testTrend.length?'<section class="surface panel stack progress-block"><h2>История последних тестов</h2>'+
      '<p class="muted compact-copy">Состав и сложность тестов могут отличаться. Проценты между разными наборами напрямую не сравниваются.</p>'+
      table(["Дата и режим","Результат","Время"],p.testTrend.map(r=>['<a class="text-link" href="#session/'+encodeURIComponent(r.id)+'">'+
        esc(timestamp(r.finishedAt))+'</a><small class="history-mode">'+(r.lang==="en"?'SAT Math':'Школьная математика')+
        (r.difficulty?' · '+esc(levelNames[r.difficulty]||r.difficulty):'')+'</small>',
        fmt(r.correct)+' / '+fmt(r.total)+' · '+pct(r.correct,r.total),durationLabel(r.elapsedSeconds)]))+'</section>':''));
  page.querySelector("#review-start")?.addEventListener("click",e=>startSession({mode:"review",topics:[],count:5,lang:"ru"},e.currentTarget));
  bindLearningPath();
  page.querySelector("#review-exact")?.addEventListener("click",e=>startSession({mode:"review",topics:[],count:Math.min(20,p.mistakeCount),lang:"ru",reviewStrategy:"exact"},e.currentTarget));
}

function solution(items) {
  return '<ol class="steps">'+(items||[]).map(s=>'<li>'+mathText(s)+'</li>').join("")+'</ol>';
}

function resultStatus(item) {
  if(item.correct) return "Верно";
  if(item.timedOut) return "Время вышло";
  if(item.unanswered||item.submitted===null) return "Без ответа";
  return "Ошибка";
}

function renderResults(s) {
  const items=s.results||[];
  const incorrect=[...new Set(items.filter(r=>!r.correct&&!r.unanswered).map(r=>r.topic).filter(Boolean))];
  const timedOut=items.filter(r=>r.timedOut).length;
  setView('<div class="task-area">'+heading("Результат","",esc(modeNames[s.mode]))+
    '<section class="surface panel result-summary"><div><strong>'+fmt(s.correct)+' из '+fmt(s.total)+' верно · '+pct(s.correct,s.total)+'</strong>'+
    '<span class="muted">Время: '+durationLabel(s.elapsedSeconds)+'</span>'+
    (timedOut?'<span class="muted">Время вышло в '+fmt(timedOut)+' из '+fmt(s.total)+' задач</span>':'')+'</div>'+
    '<div class="actions">'+(incorrect.length?'<button class="btn primary" id="result-exact">Повторить эти задачи</button>'+
    '<button class="btn secondary" id="result-practice">Новые задачи по ошибкам</button>':'')+
    routeLink("progress","Прогресс")+'</div></section>'+
    (incorrect.length?'<section class="surface panel stack"><h2>Ошибки по темам</h2><ul class="topic-errors">'+incorrect.map(id=>
      '<li>'+esc(topicById(id)?.title||id)+' <strong>'+fmt(s.topicErrors?.[id])+'</strong></li>').join("")+'</ul></section>':'')+
    '<section class="surface result-list"><h2 class="section-label">Разбор ответов</h2>'+
    (items.length?items.map((item,i)=>'<details class="result-item"><summary><span>'+fmt(i+1)+'. '+esc(item.title||topicById(item.topic)?.title||"Задача")+
      '</span><span class="result-status '+(item.correct?"positive":item.unanswered?"muted":"negative")+'">'+resultStatus(item)+
      '</span></summary><div class="result-detail"><p class="result-prompt"'+(s.lang==="en"?' lang="en"':'')+'>'+mathText(item.prompt)+
      '</p><p>Правильный ответ: <strong>'+esc(item.answerDisplay??item.answer)+'</strong> <span class="muted">· Твой ответ: '+esc(item.submittedDisplay??item.submitted??"—")+'</span></p>'+
      (item.diagnostic?'<p>'+mathText(item.diagnostic)+'</p>':'')+solution(item.solution)+'<p class="muted compact-copy">'+esc(levelNames[item.difficulty]||"")+
      (item.assistance?' · '+esc(assistanceNames[item.assistance]||""):'')+
      (item.seconds!==undefined&&item.seconds!==null?' · '+durationLabel(item.seconds):'')+
      (item.id?' · Код задачи: <code>'+esc(item.id)+'</code>':'')+'</p></div></details>').join(""):'<p class="empty">В этой сессии ответов нет.</p>')+'</section></div>');
  page.querySelector("#result-practice")?.addEventListener("click",e=>startSession({mode:"review",topics:incorrect,count:5,
    lang:s.lang||"ru",sourceSessionId:s.id},e.currentTarget));
  page.querySelector("#result-exact")?.addEventListener("click",e=>startSession({mode:"review",topics:incorrect,count:Math.min(40,items.length),
    lang:s.lang||"ru",reviewStrategy:"exact",sourceSessionId:s.id},e.currentTarget));
}

function renderHints(hints) {
  const element=page.querySelector("#hints");
  if (!element) return;
  element.innerHTML=hints.length?'<div class="notice"><strong>Подсказки</strong>'+solution(hints)+'</div>':"";
  const button=page.querySelector("#hint-question");
  const total=session?.question?.hintTotal??2;
  if(button&&hints.length) button.textContent=hints.length>=total?"Подсказки показаны":"Ещё подсказка";
  if(button) button.setAttribute("aria-disabled",String(hints.length>=total));
}

function answerFields(q, lang) {
  const response=q.response||{};
  if(response.kind==="graph"||response.kind==="data_plot") {
    return '<input type="hidden" name="answer" id="answer"><div id="graph-answer"></div>';
  }
  const options=response.kind==="choice"&&Array.isArray(response.options)?response.options:
    Array.isArray(q.options)?q.options.map((value,i)=>({value,label:String.fromCharCode(65+i)+". "+value})):[];
  if(options.length) {
    return '<fieldset class="options" aria-describedby="answer-error"><legend class="sr-only">Выбери один вариант ответа</legend>'+
      options.map(option=>'<label class="option"><input type="radio" name="answer" value="'+esc(option.value)+'" required>'+
        '<span>'+mathText(option.label)+'</span></label>').join("")+'</fieldset>';
  }
  const hints={
    fraction:"Введи точную несократимую дробь, например 3/11. Целый результат можно записать целым числом.",
    pair:"Введи координаты через точку с запятой, например 2;3.",
    interval:"Введи интервал, например (2;5]. Круглая скобка исключает границу, квадратная включает.",
    sequence:"Введи обозначения шагов через запятую в правильном порядке, например c,a,b.",
    roots:"Введи все корни через точку с запятой, например −2;0;2. Если корней нет, введи ∅ или нет решений.",
    expression:"Введи выражение целиком. Степень: x^2, произведение: 2x или 2*x, дробь: (x+1)/(x−2). Соблюдай требуемый вид ответа.",
    interval_set:"Введи всё множество решений. Объединение: (-inf;2] U [5;+inf). Пустое множество: ∅. Все действительные числа: R.",
  };
  const instruction=hints[response.kind]||(lang==="en"?
    "Число или дробь. Десятичный ответ SAT: до 5 знаков для положительного и 6 для отрицательного, с округлением или усечением. Для 2/3 допустимы .6666 или .6667.":
    "Число или дробь, например 3/4.");
  const descriptions=response.kind==="sequence"?response.options:response.parts;
  const parts=Array.isArray(descriptions)?'<ol class="answer-parts">'+descriptions.map((part,index)=>{
    const item=typeof part==="object"&&part!==null?part:{value:String.fromCharCode(97+index),label:part};
    return '<li><strong>'+esc(item.value||String.fromCharCode(97+index))+'.</strong> '+mathText(item.label||item.text||"")+'</li>';
  }).join("")+'</ol>':"";
  return parts+'<div class="answer-entry"><label for="answer">Ответ</label><input name="answer" id="answer" class="field" maxlength="500" autocomplete="off" aria-describedby="answer-format answer-error" required>'+
    '<small id="answer-format">'+esc(instruction)+'</small></div>';
}

function answerError(text) {
  const output=page.querySelector("#answer-error");
  if(!output) { message(text); return; }
  output.textContent=text;
  output.hidden=!text;
  const fields=[...page.querySelectorAll("#answer-form input[name=answer]"),...page.querySelectorAll("#answer-form [data-graph-parameter]")];
  fields.forEach(field=>{
    if(text) field.setAttribute("aria-invalid","true");
    else field.removeAttribute("aria-invalid");
  });
  if(text) {
    const field=page.querySelector("#answer-form input[name=answer]:checked, #answer-form [data-graph-parameter]")||fields[0];
    field?.focus();
  }
}

function renderQuestion(s, focus=false) {
  stopTimer();
  if (s.finished) {
    renderResults(s);
    if(focus) focusTarget("h1",true);
    return;
  }
  const q=s.question;
  if(!q) return missing();
  const test=s.mode==="test";
  const timed=test&&s.remainingSeconds!==null;
  const feedback=s.feedback;
  const fields=answerFields(q,s.lang);

  setView('<div class="task-area">'+heading(q.title||topicById(q.topic)?.title||"Задача","",s.lang==="en"?"SAT Math · "+modeNames[s.mode]:modeNames[s.mode])+
    '<article class="surface question"><header class="question-meta"><span>Задача <strong>'+fmt(s.index+1)+'</strong> из '+fmt(s.total)+
    (q.difficulty?' · '+esc(levelNames[q.difficulty]):'')+'</span>'+
    (timed?'<div class="time-label">Осталось <span class="timer" id="timer" aria-label="Оставшееся время" role="timer"></span></div>':'')+'</header>'+
    '<div class="question-body stack"><p class="prompt" tabindex="-1"'+(s.lang==="en"?' lang="en"':'')+'>'+mathText(q.prompt)+'</p>'+
    (s.expired?'<p class="notice" role="status">Время этой задачи истекло. Ответ будет отмечен как пропущенный.</p>':'')+
    (!feedback?'<form id="answer-form" class="answer-form">'+fields+'<p id="answer-error" class="field-error" role="alert" hidden></p><div class="actions"><button type="submit" class="btn primary">Ответить</button>'+
      '<button type="button" class="btn secondary" id="skip-question">Пропустить</button></div></form>':
      '<div class="feedback '+(feedback.correct?"good":"bad")+'" tabindex="-1"><strong>'+
      (feedback.correct?"Верно":feedback.submitted===null?"Задача пропущена":"Неверный ответ")+
      '</strong><p>Правильный ответ: '+esc(feedback.answerDisplay??feedback.answer)+'</p>'+
      (feedback.diagnostic?'<p>'+mathText(feedback.diagnostic)+'</p>':'')+
      '<p class="muted compact-copy">'+esc(assistanceNames[feedback.assistance]||"")+'</p>'+
      '<details class="solution"><summary>Разбор решения</summary>'+solution(feedback.solution)+'</details></div>'+
      '<button class="btn primary" id="next-question">'+(s.index+1>=s.total?"Посмотреть результат":"Следующая задача")+'</button>')+
    (!test&&!feedback?'<button class="btn plain" id="hint-question">Подсказка</button>':'')+
    (!test?'<div id="hints" aria-live="polite" aria-atomic="true"></div>':'')+'</div></article>'+
    (!test&&q.graph?'<div id="question-graph"></div>':'')+
    (!test&&model.coachAvailable?'<details class="surface details"><summary>ИИ-наставник</summary>'+
      '<p class="muted">Твой вопрос и условие задачи отправятся в Groq.</p><form id="coach-form" class="coach-form">'+
      '<input class="field" name="question" maxlength="300" required aria-label="Вопрос наставнику"><button type="submit" class="btn secondary">Спросить</button></form>'+
      '<p class="coach-answer" id="coach-answer" aria-live="polite"></p></details>':'')+
    (timed?'<p class="muted compact-copy timer-warning">Время текущей задачи продолжает идти при уходе со страницы. Незавершённый ответ восстанавливается до истечения времени.</p>':'')+
    '<div class="task-footer"><button class="btn plain" id="finish-session">Завершить досрочно</button></div>'+
    '<div id="session-confirmation" class="notice" role="group" aria-labelledby="confirmation-title" hidden></div></div>');
  mountGraph("#question-graph",q.graph);
  renderHints(s.hints||[]);
  const form=page.querySelector("#answer-form");
  const draft=restoreDraft(s);
  if(form&&draft&&!s.expired) {
    for(const input of form.querySelectorAll("input[name=answer]")) {
      if(input.type==="radio") input.checked=input.value===draft;
      else input.value=draft;
    }
  }
  if(form&&["graph","data_plot"].includes(q.response?.kind)) {
    const editor=page.querySelector("#graph-answer");
    const widget=q.response.kind==="graph"?window.ReplayGraphExercise:window.ReplayDataPlot;
    if(widget?.mount) {
      const dispose=widget.mount(editor,q.response,page.querySelector("#answer"));
      if(typeof dispose==="function") graphCleanup.push(dispose);
    } else {
      editor.textContent="Редактор графика не загрузился. Обнови страницу.";
      form.querySelector("button[type=submit]").disabled=true;
    }
  }
  form?.addEventListener("input",()=>{
    answerError("");
    saveDraft(s,String(new FormData(form).get("answer")||""));
  });
  if(s.expired) {
    form?.querySelectorAll("input,button").forEach(control=>{control.disabled=true;});
    removeDraft(s);
    const graphControls=page.querySelector("#graph-answer fieldset");
    if(graphControls) graphControls.disabled=true;
  }

  function change(kind, data, button) {
    const version=routeVersion;
    return action(async()=>{
      const state=await request(sessionPath(s.id)+"/"+kind,{index:s.index,...data});
      if(kind==="answer"||kind==="finish") removeDraft(s);
      if(version!==routeVersion || session?.id!==s.id) return;
      session=state;
      if(kind==="hint"&&state.index===s.index&&!state.finished) renderHints(state.hints||[]);
      else renderQuestion(state,true);
    },kind==="hint"?undefined:button,error=>{
      if(version!==routeVersion || session?.id!==s.id) return;
      if(kind==="answer") answerError(error);
      else message(error);
    });
  }
  function confirmChange(kind, data, source, text) {
    if(busy) return;
    const panel=page.querySelector("#session-confirmation");
    panel.innerHTML='<p id="confirmation-title">'+esc(text)+'</p><div class="actions">'+
      '<button class="btn secondary" type="button" data-cancel>Продолжить решать</button>'+
      '<button class="btn primary" type="button" data-confirm>Подтвердить</button></div>';
    panel.hidden=false;
    function cancel() {
      panel.hidden=true;
      source.focus();
    }
    panel.querySelector("[data-cancel]").addEventListener("click",cancel);
    panel.querySelector("[data-confirm]").addEventListener("click",event=>change(kind,data,event.currentTarget));
    panel.onkeydown=event=>{
      if(event.key==="Escape") {event.preventDefault();cancel();}
    };
    panel.querySelector("[data-cancel]").focus();
    panel.scrollIntoView({block:"nearest"});
  }
  page.querySelector("#answer-form")?.addEventListener("submit",e=>{
    e.preventDefault();
    const value=String(new FormData(e.currentTarget).get("answer")||"").trim();
    if(!value) {answerError("Введи ответ.");return;}
    change("answer",{answer:value},e.submitter);
  });
  page.querySelector("#skip-question")?.addEventListener("click",e=>{
    confirmChange("answer",{answer:null},e.currentTarget,"Пропустить задачу? В этой попытке она будет отмечена без ответа.");
  });
  page.querySelector("#next-question")?.addEventListener("click",e=>change("next",{},e.currentTarget));
  page.querySelector("#hint-question")?.addEventListener("click",e=>{
    if(e.currentTarget.getAttribute("aria-disabled")!=="true") change("hint",{},e.currentTarget);
  });
  page.querySelector("#finish-session").addEventListener("click",e=>{
    confirmChange("finish",{},e.currentTarget,"Завершить сессию и открыть результат? Неотправленные ответы останутся без оценки.");
  });
  page.querySelector("#coach-form")?.addEventListener("submit",e=>{
    e.preventDefault();
    const text=String(new FormData(e.currentTarget).get("question")||"").trim();
    if(!text) return;
    const output=page.querySelector("#coach-answer");
    action(async()=>{
      output.textContent="Загрузка ответа…";
      try { output.textContent=(await request(sessionPath(s.id)+"/coach",{index:s.index,message:text})).reply; }
      catch(error) { output.textContent=error.message; }
    },e.submitter);
  });

  if(focus) focusTarget(feedback?".feedback":".prompt",true);
  if(timed) startTimer(s);
}

function stopTimer() {
  if(clock!==null) clearInterval(clock);
  clock=null;
}

function startTimer(s) {
  const timer=page.querySelector("#timer");
  const deadline=performance.now()+(s.remainingSeconds??240)*1000;
  const version=routeVersion;
  let polling=false;
  let retryAfter=0;
  const tick=async()=>{
    const now=performance.now();
    const left=Math.max(0,Math.ceil((deadline-now)/1000));
    const shown=Math.floor(left/60)+":"+String(left%60).padStart(2,"0");
    if(timer.textContent!==shown) timer.textContent=shown;
    timer.classList.toggle("is-low",left<=30);
    if(left||busy||polling||now<retryAfter||version!==routeVersion) return;
    polling=true;
    try {
      const state=await request(sessionPath(s.id)+"/expire",{index:s.index});
      if(version!==routeVersion||session?.id!==s.id||session?.index!==s.index) return;
      if(state.index!==s.index||state.finished) removeDraft(s);
      session=state;
      message(state.index!==s.index||state.finished?"Время предыдущей задачи истекло. Она отмечена без ответа.":"");
      renderQuestion(state,state.index!==s.index||state.finished);
    } catch(error){
      if(version===routeVersion) message(error.message);
      retryAfter=performance.now()+2000;
    } finally { polling=false; }
  };
  clock=setInterval(tick,300);
  tick();
}

function missing() {
  setView(heading("Страница не найдена")+routeLink("topics","Открыть темы"));
}

function updateNav(active) {
  document.querySelectorAll("[data-nav]").forEach(a=>{
    if(a.dataset.nav===active) a.setAttribute("aria-current","page");
    else a.removeAttribute("aria-current");
  });
}

async function route(moveFocus=false) {
  const version=++routeVersion;
  let [name,arg]=activePath().split("/");
  try { arg=arg===undefined?"":decodeURIComponent(arg); } catch {arg="";}
  stopTimer();
  message("");
  window.scrollTo(0,0);
  document.title=(names[name]||"Страница не найдена")+" / Replay Mathematics";
  const active=name==="home"||name==="lesson"?"topics":name;
  updateNav(active);
  const loading=setTimeout(()=>{
    if(version===routeVersion) {
      setView('<p class="loading" role="status">Загрузка…</p>');
      page.setAttribute("aria-busy","true");
    }
  },200);
  try {
    if(name==="session") {
      const state=await request(sessionPath(arg));
      if(version!==routeVersion) return;
      session=state;
      updateNav(state.lang==="en"?"sat":state.mode==="test"?"test":state.mode==="review"?"progress":"topics");
      renderQuestion(state,moveFocus);
      return;
    }
    if(["home","topics","progress"].includes(name)){
      const status=await request("progress");
      if(version!==routeVersion) return;
      model.progress=status;
    }
    if(name==="home"||name==="topics") renderTopics();
    else if(name==="lesson") {
      if(!topicById(arg)) { missing(); return; }
      const body=await request("lessons/"+encodeURIComponent(arg));
      if(version!==routeVersion) return;
      lesson(arg,body);
    }
    else if(name==="test"||name==="sat") construct(arg,name==="sat");
    else if(name==="progress") progress();
    else if(name==="guide") {
      setView(heading("Как пользоваться")+window.ReplayGuide.content());
      page.querySelector("#guide-start").addEventListener("click",()=>window.ReplayGuide.start());
      page.querySelector("#reproduce-form").addEventListener("submit",event=>{
        event.preventDefault();
        const {value}=page.querySelector("#problem-id");
        startSession({mode:"practice",topics:[],count:1,lang:"ru",problemId:value.trim()},event.submitter);
      });
    }
    else missing();
    if(moveFocus) focusTarget("h1");
  } catch(error){
    if(version!==routeVersion) return;
    setView(heading("Не удалось открыть страницу")+'<button class="btn secondary" id="retry">Повторить</button>');
    page.querySelector("#retry").addEventListener("click",()=>route(true));
    message(error.message);
  } finally {
    clearTimeout(loading);
    if(version===routeVersion) window.ReplayGuide.refresh();
  }
}

async function init() {
  try {
    model={...model,...await request("catalog")};
    addEventListener("hashchange",()=>route(true));
    await route();
  } catch(error) {
    setView(heading("Тренажёр недоступен","Запусти Start.bat и открой указанный в окне сервера адрес.")+
      '<button class="btn secondary" id="retry">Повторить</button>');
    page.querySelector("#retry").addEventListener("click",()=>location.reload());
    message(error.message);
  }
}

document.querySelector(".skip").addEventListener("click",event=>{
  event.preventDefault();
  document.querySelector("#main").focus();
});

addEventListener("beforeunload",event=>{
  if(!session||session.finished||session.feedback||!activePath().startsWith("session/"))return;
  const form=page.querySelector("#answer-form");
  const value=form?String(new FormData(form).get("answer")||""):"";
  if(value) saveDraft(session,value);
});

init();
