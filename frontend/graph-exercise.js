(() => {
  'use strict';

  const blue = '#315d78';
  const green = '#466a52';
  const format = new Intl.NumberFormat('ru', {maximumFractionDigits: 4});
  const fmt = value => format.format(Math.abs(value)<1e-10 ? 0 : value);

  function evaluate(model, parameters, x) {
    return model==='line' ? parameters.m*x+parameters.b : parameters.a*(x-parameters.h)**2+parameters.k;
  }

  function formula(model, p) {
    const signed = value => value<0 ? ' − '+fmt(-value) : ' + '+fmt(value);
    return model==='line' ? 'y = '+fmt(p.m)+'x'+signed(p.b) :
      'y = '+fmt(p.a)+'(x'+signed(-p.h)+')²'+signed(p.k);
  }

  function initialValues(spec, draft) {
    let saved;
    try { saved=JSON.parse(draft||'null'); } catch { saved=null; }
    return Object.fromEntries(spec.parameters.map(parameter=>{
      const candidate=saved?.[parameter.key];
      const valid=candidate===null||typeof candidate==='number'&&Number.isFinite(candidate);
      return [parameter.key,valid?candidate:parameter.initial];
    }));
  }

  function validParameter(spec, parameter, value) {
    const steps=(value-parameter.min)/parameter.step;
    return typeof value==='number'&&Number.isFinite(value)&&value>=parameter.min&&value<=parameter.max&&
      Math.abs(steps-Math.round(steps))<1e-9&&!(spec.model==='parabola'&&parameter.key==='a'&&value===0);
  }

  function mount(element, spec, answer) {
    if(!element||!window.MathLab?.createPlot) return;
    const draft=initialValues(spec,answer.value);
    const state=Object.fromEntries(spec.parameters.map(p=>[p.key,
      validParameter(spec,p,draft[p.key])?draft[p.key]:p.initial]));
    const card=document.createElement('section');
    card.className='mathlab graph-exercise';
    card.setAttribute('aria-label','Построение графика');
    const heading=document.createElement('div');
    heading.className='mathlab__head';
    const expression=document.createElement('output');
    expression.className='mathlab__tag';
    const title=document.createElement('strong');
    title.textContent='Твой график';
    heading.append(title,expression);
    const canvas=document.createElement('canvas');
    canvas.className='mathlab__plot';
    canvas.setAttribute('role','img');
    const instructions=document.createElement('p');
    instructions.className='mathlab__result';
    instructions.textContent=spec.model==='line' ?
      'Меняй коэффициенты или перетаскивай отмеченные точки по вертикали. Точка на оси y задаёт b, точка при x=1 — наклон.' :
      'Меняй коэффициенты или перетаскивай вершину. Вторую отмеченную точку при x=h+1 двигай по вертикали для изменения a.';
    if(spec.reference) instructions.textContent+=' Заданный график показан зелёным пунктиром.';
    const inputStatus=document.createElement('p');
    inputStatus.className='field-error graph-input-status';inputStatus.setAttribute('role','status');inputStatus.hidden=true;
    const controls=document.createElement('fieldset');
    controls.className='mathlab__controls graph-parameters';
    const legend=document.createElement('legend');
    legend.className='sr-only';
    legend.textContent='Параметры твоего графика';
    controls.append(legend);
    const inputs=new Map();
    const sliders=new Map();
    const table=document.createElement('table');
    table.className='data-table';
    const details=document.createElement('details');
    details.className='mathlab__alternative';
    const summary=document.createElement('summary');
    summary.textContent='Таблица координат';
    details.append(summary,table);
    const actions=document.createElement('div');
    actions.className='graph-actions';
    const reset=document.createElement('button');
    reset.type='button'; reset.className='btn plain compact'; reset.textContent='Сбросить построение';
    actions.append(reset);
    card.append(heading,canvas,instructions,inputStatus,controls,actions,details);
    element.replaceChildren(card);
    const context=canvas.getContext('2d');
    let frame=0;
    let plot=null;
    let drag=null;
    let disposed=false;

    function syncAnswer() {
      answer.value=JSON.stringify(Object.fromEntries(spec.parameters.map(parameter=>{
        const input=inputs.get(parameter.key);
        return [parameter.key,input.value===''?null:Number(input.value)];
      })));
      const invalid=[...inputs.values()].some(input=>input.value===''||!input.validity.valid)||spec.model==='parabola'&&Number(inputs.get('a').value)===0;
      inputStatus.hidden=!invalid;
      inputStatus.textContent=invalid?'Проверь все параметры и их диапазоны. Для параболы a≠0. Предпросмотр показывает последний допустимый график.':'';
    }

    function updateTable() {
      const headers=['x',...(spec.reference?['Заданный график']:[]),'Твой график'];
      const head=document.createElement('thead');
      const row=document.createElement('tr');
      headers.forEach(label=>{ const cell=document.createElement('th'); cell.scope='col';cell.textContent=label;row.append(cell); });
      head.append(row);
      const body=document.createElement('tbody');
      const samples=spec.points?.length ? spec.points.map(p=>p.x) : [-2,-1,0,1,2];
      const center=spec.model==='parabola'?state.h:0;
      const xs=[...new Set([...samples,center-1,center,center+1])].sort((a,b)=>a-b);
      xs.forEach(x=>{
        const row=document.createElement('tr');
        const values=[x,...(spec.reference?[evaluate(spec.reference.model,spec.reference.parameters,x)]:[]),evaluate(spec.model,state,x)];
        values.forEach((value,index)=>{
          const cell=document.createElement(index===0?'th':'td');
          if(index===0) cell.scope='row';
          cell.textContent=fmt(value);row.append(cell);
        });
        body.append(row);
      });
      table.replaceChildren(head,body);
    }

    function handles() {
      return spec.model==='line' ? [[0,state.b],[1,state.m+state.b]] :
        [[state.h,state.k],[state.h+1,state.a+state.k]];
    }

    function draw() {
      if(frame||disposed) return;
      frame=requestAnimationFrame(()=>{
        frame=0;
        if(disposed) return;
        expression.textContent=formula(spec.model,state);
        canvas.setAttribute('aria-label','Твой график '+expression.textContent+'. Координаты приведены в таблице ниже.');
        updateTable();
        if(!context||canvas.clientWidth<75) return;
        context.clearRect(0,0,canvas.width,canvas.height);
        plot=window.MathLab.createPlot(canvas,context);
        const view=spec.view||{xmin:-10,xmax:10,ymin:-10,ymax:10};
        const domain=plot.axes([view.xmin,view.xmax],[view.ymin,view.ymax],false,view);
        if(spec.reference) plot.curve(x=>evaluate(spec.reference.model,spec.reference.parameters,x),domain,{color:green,dash:[7,5]});
        plot.curve(x=>evaluate(spec.model,state,x),domain,{color:blue});
        (spec.points||[]).forEach(point=>plot.point(point.x,point.y,green,5));
        handles().forEach(([x,y])=>plot.point(x,y,blue,6));
      });
    }

    function setParameter(parameter, value) {
      const bounded=Math.max(parameter.min,Math.min(parameter.max,value));
      const snapped=parameter.min+Math.round((bounded-parameter.min)/parameter.step)*parameter.step;
      state[parameter.key]=Number(snapped.toFixed(8));
      inputs.get(parameter.key).value=String(state[parameter.key]);
      sliders.get(parameter.key).value=String(state[parameter.key]);
    }

    for(const parameter of spec.parameters) {
      const wrapper=document.createElement('div');
      wrapper.className='mathlab__control';
      const label=document.createElement('label');
      label.htmlFor='graph-parameter-'+parameter.key;label.textContent=parameter.label;
      const input=document.createElement('input');
      input.className='field graph-number';input.id=label.htmlFor; input.type='number';input.required=true;
      input.min=String(parameter.min); input.max=String(parameter.max); input.step=String(parameter.step);input.value=draft[parameter.key]===null?'':String(draft[parameter.key]);
      input.dataset.graphParameter=parameter.key;input.setAttribute('aria-describedby','answer-error');
      const slider=document.createElement('input');
      slider.type='range';slider.min=input.min;slider.max=input.max;slider.step=input.step;slider.value=String(state[parameter.key]);
      slider.setAttribute('aria-label',parameter.label+' — ползунок');
      input.addEventListener('input',()=>{
        if(input.value!==''&&input.validity.valid&&validParameter(spec,parameter,Number(input.value))) {
          state[parameter.key]=Number(input.value);slider.value=input.value;draw();
        }
        syncAnswer();
      });
      slider.addEventListener('input',()=>{setParameter(parameter,Number(slider.value));syncAnswer();draw();});
      inputs.set(parameter.key,input);sliders.set(parameter.key,slider);
      wrapper.append(label,input,slider);controls.append(wrapper);
    }
    reset.addEventListener('click',()=>{
      spec.parameters.forEach(parameter=>setParameter(parameter,parameter.initial));
      syncAnswer();draw();answer.dispatchEvent(new Event('input',{bubbles:true}));
    });
    canvas.addEventListener('pointerdown',event=>{
      if(!plot||controls.disabled) return;
      const bounds=canvas.getBoundingClientRect();
      const x=event.clientX-bounds.left,y=event.clientY-bounds.top;
      const distances=handles().map(([hx,hy])=>{
        const [px,py]=plot.screen(hx,hy);return Math.hypot(px-x,py-y);
      });
      const closest=Math.min(...distances);
      drag=closest<=18?distances.indexOf(closest):null;
      if(drag===null) return;
      event.preventDefault();canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove',event=>{
      if(drag===null||!plot||controls.disabled) return;
      const bounds=canvas.getBoundingClientRect();
      const [x,y]=plot.coordinates(event.clientX-bounds.left,event.clientY-bounds.top);
      const values=spec.model==='line' ? (drag===0?{b:y}:{m:y-state.b}) :
        (drag===0?{h:x,k:y}:{a:y-state.k});
      spec.parameters.filter(parameter=>Object.hasOwn(values,parameter.key)).forEach(parameter=>setParameter(parameter,values[parameter.key]));
      syncAnswer();draw();answer.dispatchEvent(new Event('input',{bubbles:true}));
    });
    const release=()=>{drag=null;};
    canvas.addEventListener('pointerup',release);
    canvas.addEventListener('pointercancel',release);
    canvas.addEventListener('lostpointercapture',release);
    syncAnswer();draw();
    const observer=new ResizeObserver(draw);observer.observe(canvas);
    return ()=>{disposed=true;observer.disconnect();if(frame) cancelAnimationFrame(frame);};
  }

  window.ReplayGraphExercise={mount,evaluate,formula,initialValues};
})();
