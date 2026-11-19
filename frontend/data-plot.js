(() => {
  'use strict';
  const svgNS='http://www.w3.org/2000/svg';
  const fmt=value=>new Intl.NumberFormat('ru',{maximumFractionDigits:4}).format(value);

  function number(text) {
    const source=String(text).trim().replace('−','-').replace(',','.');
    if(!/^[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:\s*\/\s*\d+)?$/.test(source)) return null;
    const parts=source.split('/').map(Number);
    const result=parts.length===2?parts[0]/parts[1]:parts[0];
    return Number.isFinite(result)&&result>=0&&result<=10000?result:null;
  }

  function coordinates(spec, values) {
    const x=spec.mode==='histogram'?spec.bins:spec.x;
    const left=x[0],right=x[x.length-1];
    const maximum=Math.max(5,...values.filter(v=>v!==null));
    const top=Math.ceil(maximum/5)*5;
    return {x:value=>48+(value-left)/(right-left)*404,y:value=>190-value/top*160,top};
  }

  function mount(container,spec,answer) {
    if(!container||!answer) return;
    let saved;
    try { saved=JSON.parse(answer.value); } catch { saved=[]; }
    if(!Array.isArray(saved)||saved.length!==spec.labels.length) saved=[];
    const fieldset=document.createElement('fieldset');
    fieldset.className='data-plot';
    const legend=document.createElement('legend');
    legend.textContent=spec.mode==='frequency_table'?'Заполни таблицу частот':'Построй график через таблицу значений';
    fieldset.append(legend);
    const table=document.createElement('table');
    table.className='data-table';
    const inputs=[];
    const heading=document.createElement('tr');
    for(const title of [spec.mode==='histogram'?'Интервал':'Значение',spec.axis]) {
      const th=document.createElement('th'); th.scope='col'; th.textContent=title; heading.append(th);
    }
    const thead=document.createElement('thead'); thead.append(heading); table.append(thead);
    const tbody=document.createElement('tbody');
    spec.labels.forEach((label,index)=>{
      const row=document.createElement('tr');
      const th=document.createElement('th'); th.scope='row'; th.textContent=label; row.append(th);
      const td=document.createElement('td');
      const input=document.createElement('input');
      input.type='text'; input.inputMode='text'; input.className='field';
      input.required=true; input.maxLength=40; input.autocomplete='off';
      input.setAttribute('aria-label',spec.axis+': '+label);
      input.setAttribute('aria-describedby','data-plot-help answer-error');
      input.setAttribute('data-graph-parameter',String(index));
      input.value=typeof saved[index]==='string'?saved[index]:'';
      td.append(input); row.append(td); tbody.append(row); inputs.push(input);
    });
    table.append(tbody); fieldset.append(table);
    const help=document.createElement('p'); help.id='data-plot-help'; help.className='muted compact-copy';
    help.textContent='Введи все значения. Допустимы числа и точные дроби, например 5/3. '+
      (spec.mode==='frequency_table'?'Сумма частот должна равняться объёму выборки.':'График обновляется по твоим значениям; правильность проверяется после отправки.');
    fieldset.append(help);
    let svg,alternative;
    if(spec.mode!=='frequency_table') {
      svg=document.createElementNS(svgNS,'svg');
      svg.setAttribute('viewBox','0 0 480 235'); svg.setAttribute('role','img');
      svg.setAttribute('class','data-plot-preview');
      svg.setAttribute('aria-label',spec.mode==='histogram'?'Твоя гистограмма':'Твой полигон частот');
      fieldset.append(svg);
      alternative=document.createElement('p'); alternative.className='muted compact-copy';
      alternative.setAttribute('aria-live','polite'); fieldset.append(alternative);
    }
    container.append(fieldset);
    function node(tag,attrs,text) {
      const element=document.createElementNS(svgNS,tag);
      Object.entries(attrs).forEach(([key,value])=>element.setAttribute(key,String(value)));
      if(text!==undefined) element.textContent=text;
      svg.append(element); return element;
    }
    function update(emit) {
      const raw=inputs.map(input=>input.value);
      answer.value=raw.every(value=>value.trim()==='')?'':JSON.stringify(raw);
      if(svg) {
        svg.replaceChildren();
        const values=raw.map(number), p=coordinates(spec,values);
        for(let t=0;t<=5;t++) {
          const value=p.top*t/5,y=p.y(value);
          node('line',{x1:48,x2:452,y1:y,y2:y,stroke:'#d7d5d0','stroke-width':1});
          node('text',{x:40,y:y+4,'text-anchor':'end'},fmt(value));
        }
        node('line',{x1:48,x2:48,y1:30,y2:190,stroke:'#555'});
        node('line',{x1:48,x2:452,y1:190,y2:190,stroke:'#555'});
        const xs=spec.mode==='histogram'?spec.bins:spec.x;
        xs.forEach(value=>node('text',{x:p.x(value),y:207,'text-anchor':'middle'},fmt(value)));
        node('text',{x:48,y:17},spec.axis);
        node('text',{x:250,y:229,'text-anchor':'middle'},spec.mode==='histogram'?'Интервалы значений':'Значение');
        values.forEach((value,index)=>{
          if(value===null) return;
          if(spec.mode==='histogram') {
            node('rect',{x:p.x(spec.bins[index]),y:p.y(value),width:p.x(spec.bins[index+1])-p.x(spec.bins[index]),
              height:190-p.y(value),fill:'#587764','fill-opacity':0.25,stroke:'#466a52','stroke-width':1.5});
          } else {
            if(index>0&&values[index-1]!==null) node('line',{x1:p.x(xs[index-1]),y1:p.y(values[index-1]),x2:p.x(xs[index]),y2:p.y(value),stroke:'#315d78','stroke-width':2});
            node('circle',{cx:p.x(xs[index]),cy:p.y(value),r:4,fill:'#315d78'});
          }
        });
        alternative.textContent=spec.labels.map((label,index)=>label+': '+(raw[index].trim()||'не задано')).join('; ')+'.';
      }
      if(emit) answer.dispatchEvent(new Event('input',{bubbles:true}));
    }
    const handlers=inputs.map(input=>{const handler=()=>update(true); input.addEventListener('input',handler); return handler;});
    update(false);
    return ()=>inputs.forEach((input,index)=>input.removeEventListener('input',handlers[index]));
  }
  window.ReplayDataPlot={mount,number,coordinates};
})();
