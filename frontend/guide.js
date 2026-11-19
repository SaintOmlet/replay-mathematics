"use strict";

window.ReplayGuide = (() => {
  const mount = document.querySelector("#guide-panel");
  const preference = "replay-guide-v1";
  const steps = [
    {route:"topics", target:".filterbar", title:"Выбери тему",
      text:"Класс и поиск сужают список. Название темы открывает урок, а «Задачи» сразу запускают практику."},
    {route:"lesson/linear", target:".lesson-sections", title:"Открой урок",
      text:"Прочитай правило, разбери примеры и ответь на вопросы для самопроверки. Завершение урока отмечается отдельно от результата практики."},
    {route:"test", target:"#test-settings", title:"Настрой проверку",
      text:"Выбери темы и количество задач. В настройках можно задать сложность и лимит времени на вопрос или отключить его."},
    {route:"progress", target:"#progress-summary", title:"Посмотри результат",
      text:"Здесь появятся выполненные уроки, точность и история. После тестов отсюда можно вернуться к ошибочным задачам."},
  ];
  let dismissed;
  try { dismissed = Boolean(localStorage.getItem(preference)); } catch { dismissed = false; }
  let current = -1;
  let focusNext = false;

  function finish() {
    dismissed = true;
    current = -1;
    try { localStorage.setItem(preference, "seen"); } catch {}
    refresh();
  }

  function navigate() {
    const route=steps[current].route;
    focusNext = true;
    if(location.hash==="#"+route) refresh();
    else location.hash=route;
  }

  function start() {
    current=0;
    navigate();
  }

  function refresh() {
    document.querySelectorAll(".guide-target").forEach(node=>node.classList.remove("guide-target"));
    if(current<0) {
      mount.innerHTML=dismissed?"":'<aside class="surface guide-status" aria-label="Знакомство с Replay">'+
        '<span>Впервые в Replay?</span><div class="actions"><button class="btn secondary compact" data-guide="start">Пройти тур</button>'+
        '<button class="btn plain compact" data-guide="skip">Пропустить</button></div></aside>';
      return;
    }
    const step=steps[current];
    const actual=location.hash.slice(1)||"home";
    const onStep=actual===step.route||(current===0&&actual==="home");
    if(!onStep) {
      mount.innerHTML='<aside class="surface guide-status" aria-label="Знакомство с Replay">'+
        '<span>Тур приостановлен. Шаг '+(current+1)+' из '+steps.length+'.</span>'+
        '<div class="actions"><button class="btn secondary compact" data-guide="resume">Вернуться к шагу</button>'+
        '<button class="btn plain compact" data-guide="skip">Закончить тур</button></div></aside>';
      return;
    }
    mount.innerHTML='<aside class="surface guide-status guide-running" aria-label="Знакомство с Replay">'+
      '<div><p class="muted compact-copy">Шаг '+(current+1)+' из '+steps.length+'</p>'+
      '<h2 tabindex="-1">'+step.title+'</h2><p>'+step.text+'</p></div>'+
      '<div class="actions">'+(current>0?'<button class="btn plain compact" data-guide="back">Назад</button>':'')+
      '<button class="btn primary compact" data-guide="next">'+(current+1===steps.length?"Закончить":"Далее")+'</button>'+
      '<button class="btn plain compact" data-guide="skip">Пропустить</button></div></aside>';
    document.querySelector(step.target)?.classList.add("guide-target");
    if(focusNext) {
      mount.querySelector("h2").focus({preventScroll:true});
      focusNext=false;
    }
  }

  mount.addEventListener("click",event=>{
    const control=event.target.closest("[data-guide]")?.dataset.guide;
    if(control==="start") start();
    if(control==="resume") navigate();
    if(control==="skip" || (control==="next"&&current===steps.length-1)) {
      finish();
      document.querySelector("#page h1")?.focus({preventScroll:true});
    } else if(control==="next"||control==="back") {
      current+=control==="next"?1:-1;
      navigate();
    }
  });

  const sections=[
    ["Начало обучения","Выбери класс и тему. Нажми на название, чтобы открыть урок, или на «Задачи», чтобы сразу запустить практику."],
    ["Уроки","В уроке есть теория, примеры, ошибки и вопросы для самопроверки. Сначала ответь сам, затем открой ответ. «Отметить урок завершённым» сохраняет факт прохождения, а освоение проверяется по задачам."],
    ["Учебный маршрут","В каталоге и прогрессе показаны следующие шаги. Они учитывают начатые темы, самостоятельные ответы и необходимые основы. Любую тему также можно открыть напрямую. Остальные незавершённые занятия доступны в раскрываемом списке."],
    ["Графические задания","В темах «Построение прямой», «Построение и преобразование параболы» и «Чтение графика» ответом служит твой график. Меняй числовые параметры, ползунки или отмеченные точки и нажми «Ответить». Точные значения вводятся с клавиатуры, координаты доступны в таблице. Заданный график отмечен зелёным пунктиром. Черновик построения сохраняется при обновлении текущей вкладки."],
    ["Полное множество решений","В заданиях на все корни записывай числа через точку с запятой. Для объединения промежутков используй U или ∪. Пустое множество обозначается ∅ или словами «нет решений», все действительные числа — R. Если ответ неверен, проверь обе границы, скобки и все ветви исходного условия."],
    ["Как появляются задачи","У темы есть несколько типов задач с разными способами решения. Одни и те же тема и номер варианта (seed) воспроизводят задачу. Replay предпочитает свежие варианты и чередует типы. Для линейных уравнений, систем и парабол также можно вручную открыть дополнительные варианты с номерами от 1000 до 1000999."],
    ["Проверка","В разделе «Тест» выбери тему, несколько тем или целый класс. Кнопка класса добавляет его темы к отмеченным; «Снять выбор» очищает набор. Настрой количество, сложность и время. В тесте подсказки скрыты. Таймер текущего вопроса продолжает идти при уходе. По истечении времени ответ не отправляется автоматически: вопрос отмечается пропущенным."],
    ["Итоги и повторение","После сдачи видны результат, время и решения. «Повторить эти задачи» снова даёт те же варианты с ошибками. «Новые задачи по ошибкам» подбирает свежие задачи по темам."],
    ["Как читается прогресс","Точность включает все попытки. Для освоения учитываются самостоятельные ответы на разные задачи и методы после завершения урока. Подсказки, обращения к наставнику и повторы знакомых задач не дают нового самостоятельного результата. Они сохранены отдельно. По старым попыткам помощь могла не учитываться, поэтому их самостоятельность неизвестна. В таблице тем указан следующий шаг."],
    ["SAT Math","Англоязычный режим содержит авторские задачи. Дробь можно вводить как 2/3. Для десятичного ответа SAT отводит до пяти символов для положительного и до шести для отрицательного числа. Заполни доступные знаки, округляя или отбрасывая лишние. Например, для 2/3 допустимы .6666, .6667, 0.666 или 0.667. Тренажёр не пересчитывает точность в официальный балл SAT."],
    ["Где лежат данные","Историю хранит локальный файл data/study.sqlite3. Перед переносом останови сервер и скопируй папку data. Синхронизации нет. Неотправленный ответ хранится в текущей вкладке браузера и восстанавливается при обновлении того же вопроса до истечения времени. Закрытие вкладки может удалить черновик. Отправленные ответы остаются в базе. ИИ-наставнику нужен интернет и ключ Groq."],
  ];

  function content() {
    return '<section class="surface panel guide-reference stack"><button class="btn primary" id="guide-start">Запустить тур</button>'+
      sections.map(([title,text])=>'<section class="guide-entry"><h2>'+title+'</h2><p>'+text+'</p>'+
      (title==="Как появляются задачи"?'<form id="reproduce-form" class="guide-reproduce">'+
        '<label class="setting" for="problem-id">Код задачи<input class="field" id="problem-id" placeholder="Например, linear:130" maxlength="80" required></label>'+
        '<button class="btn secondary" type="submit">Открыть задачу</button></form>':'')+'</section>').join("")+'</section>';
  }

  return Object.freeze({start,refresh,content});
})();
