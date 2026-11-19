(() => {
  'use strict';

  const BLUE = '#315d78';
  const GREEN = '#466a52';
  const GRAPHITE = '#353a35';
  const number = new Intl.NumberFormat('ru', { maximumFractionDigits: 2 });
  const fmt = (value) => number.format(Math.abs(value) < 1e-9 ? 0 : value);
  const sign = (value, tail = '') => value < 0 ? ' − ' + fmt(-value) + tail : ' + ' + fmt(value) + tail;
  const blue = { color: BLUE };
  const green = { color: GREEN };

  const models = {
    quadratic: {
      title: 'График параболы',
      controls: [
        ['a', 'Коэффициент a', 1, -4, 4, 0.25],
        ['b', 'Коэффициент b', 0, -12, 12, 0.5],
        ['c', 'Коэффициент c', 0, -18, 18, 0.5],
        ['level', 'Высота линии k', 0, -12, 12, 0.5],
      ],
      draw({ a, b, c, level }, plot) {
        const curve = (x) => a * x * x + b * x + c;
        const vertexX = a !== 0 ? -b / (2 * a) : 0;
        const discriminant = b * b - 4 * a * (c - level);
        let roots = [];
        let infinite = false;
        if (a === 0) {
          if (b !== 0) roots = [(level - c) / b];
          else infinite = Math.abs(c - level) < 1e-9;
        } else if (discriminant > 1e-9) {
          const d = Math.sqrt(discriminant);
          roots = [(-b - d) / (2 * a), (-b + d) / (2 * a)].sort((x, y) => x - y);
        } else if (Math.abs(discriminant) <= 1e-9) {
          roots = [vertexX];
        }
        const limits = plot.axes([0, vertexX, ...roots], [0, c, curve(vertexX), level]);
        plot.curve(curve, limits, blue);
        plot.curve(() => level, limits, { ...green, dash: [6, 5] });
        if (a !== 0) plot.point(vertexX, curve(vertexX), BLUE, 3);
        roots.forEach((x) => plot.point(x, level, GRAPHITE, 5));
        const outcome = infinite ? 'Графики совпадают.' : roots.length
          ? 'Пересечения при x = ' + roots.map(fmt).join(' и ') + '.'
          : 'Точек пересечения нет.';
        const vertex = a !== 0 ? ' Вершина (' + fmt(vertexX) + '; ' + fmt(curve(vertexX)) + ').' : '';
        return {
          legend: ['y = ' + fmt(a) + 'x²' + sign(b, 'x') + sign(c), 'y = ' + fmt(level)],
          result: outcome + vertex,
        };
      },
    },
    lines: {
      title: 'Графики прямых',
      controls: [
        ['m1', 'Наклон первой', 1, -6, 6, 0.25],
        ['b1', 'Высота первой', 1, -15, 15, 0.5],
        ['m2', 'Наклон второй', -1, -6, 6, 0.25],
        ['b2', 'Высота второй', 3, -15, 15, 0.5],
      ],
      draw({ m1, b1, m2, b2 }, plot) {
        const coincident = m1 === m2 && b1 === b2;
        const x = m1 === m2 ? 0 : (b2 - b1) / (m1 - m2);
        const y = m1 * x + b1;
        const limits = plot.axes([0, x], [0, b1, b2, y]);
        plot.curve((u) => m1 * u + b1, limits, blue);
        plot.curve((u) => m2 * u + b2, limits, { ...green, dash: [6, 5] });
        if (m1 !== m2) plot.point(x, y, GRAPHITE, 5);
        return {
          legend: ['y = ' + fmt(m1) + 'x' + sign(b1), 'y = ' + fmt(m2) + 'x' + sign(b2)],
          result: m1 !== m2 ? 'Точка пересечения (' + fmt(x) + '; ' + fmt(y) + ').'
            : coincident ? 'Прямые совпадают. У системы бесконечно много решений.'
              : 'Прямые параллельны. У системы нет решений.',
        };
      },
    },
    triangle: {
      title: 'Прямоугольный треугольник',
      controls: [
        ['base', 'Основание', 6, 1, 20, 0.5],
        ['height', 'Высота', 4, 1, 20, 0.5],
      ],
      draw({ base, height }, plot) {
        plot.axes([0, base], [0, height], true);
        plot.polygon([[0, 0], [base, 0], [0, height]], BLUE, 'rgba(49, 93, 120, .09)');
        const marker = Math.min(base, height) * 0.16;
        plot.path([[marker, 0], [marker, marker], [0, marker]], GRAPHITE);
        [[0, 0], [base, 0], [0, height]].forEach(([x, y]) => plot.point(x, y, BLUE, 3));
        return {
          legend: ['Основание ' + fmt(base), 'Высота ' + fmt(height)],
          result: 'Площадь ' + fmt(base * height / 2) + '. Гипотенуза ' + fmt(Math.hypot(base, height)) + '.',
        };
      },
    },
  };

  function createPlot(canvas, ctx) {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const ratio = Math.min(window.devicePixelRatio || 1, 3);
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    const box = { left: 36, right: width - 18, top: 17, bottom: height - 24 };
    let bounds;
    const px = (x) => box.left + (x - bounds.x[0]) / (bounds.x[1] - bounds.x[0]) * (box.right - box.left);
    const py = (y) => box.bottom - (y - bounds.y[0]) / (bounds.y[1] - bounds.y[0]) * (box.bottom - box.top);

    function toPixelPath(points) {
      ctx.beginPath();
      points.forEach(([x, y], index) => {
        if (index === 0) ctx.moveTo(px(x), py(y));
        else ctx.lineTo(px(x), py(y));
      });
    }

    function grid(step, domain, vertical) {
      ctx.font = '12px system-ui, sans-serif';
      ctx.fillStyle = '#4e554e';
      for (let tick = Math.ceil(domain[0] / step); tick <= Math.floor(domain[1] / step); tick += 1) {
        const value = tick * step;
        const isAxis = tick === 0;
        const screen = vertical ? px(value) : py(value);
        ctx.beginPath();
        ctx.moveTo(vertical ? screen : box.left, vertical ? box.top : screen);
        ctx.lineTo(vertical ? screen : box.right, vertical ? box.bottom : screen);
        ctx.strokeStyle = isAxis ? '#7b8279' : '#dedfd8';
        ctx.lineWidth = isAxis ? 1.35 : 1;
        ctx.stroke();
        ctx.textAlign = vertical ? 'center' : 'right';
        ctx.textBaseline = vertical ? 'top' : 'middle';
        ctx.fillText(fmt(value), vertical ? screen : box.left - 6, vertical ? box.bottom + 4 : screen);
      }
    }

    const range = (values, minimum) => {
      const low = Math.min(...values);
      const high = Math.max(...values);
      const middle = (low + high) / 2;
      const half = Math.max(minimum, (high - low) * 0.63);
      return [middle - half, middle + half];
    };
    const step = (span, count) => {
      const target = span / count;
      const power = 10 ** Math.floor(Math.log10(target));
      return ([1, 2, 5, 10].find((n) => n * power >= target) || 10) * power;
    };

    function clip(action) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(box.left, box.top, box.right - box.left, box.bottom - box.top);
      ctx.clip();
      action();
      ctx.restore();
    }

    return {
      axes(x, y, sameScale = false, viewport = null) {
        bounds = viewport ? {x:[viewport.xmin,viewport.xmax],y:[viewport.ymin,viewport.ymax]} : { x: range(x, 5), y: range(y, 4) };
        if (sameScale) {
          const unit = Math.min((box.right - box.left) / (bounds.x[1] - bounds.x[0]),
            (box.bottom - box.top) / (bounds.y[1] - bounds.y[0]));
          const adjust = (domain, pixels) => {
            const middle = (domain[0] + domain[1]) / 2;
            return [middle - pixels / unit / 2, middle + pixels / unit / 2];
          };
          bounds.x = adjust(bounds.x, box.right - box.left);
          bounds.y = adjust(bounds.y, box.bottom - box.top);
        }
        grid(step(bounds.x[1] - bounds.x[0], Math.max(3, width / 58)), bounds.x, true);
        grid(step(bounds.y[1] - bounds.y[0], Math.max(3, height / 32)), bounds.y, false);
        return bounds.x;
      },
      screen(x,y) { return [px(x),py(y)]; },
      coordinates(x,y) {
        return [bounds.x[0]+(x-box.left)/(box.right-box.left)*(bounds.x[1]-bounds.x[0]),
          bounds.y[0]+(box.bottom-y)/(box.bottom-box.top)*(bounds.y[1]-bounds.y[0])];
      },
      curve(fn, domain, style) {
        const points = Array.from({ length: 161 }, (_, index) => {
          const x = domain[0] + (domain[1] - domain[0]) * index / 160;
          return [x, fn(x)];
        });
        clip(() => {
          toPixelPath(points);
          ctx.setLineDash(style.dash || []);
          ctx.strokeStyle = style.color;
          ctx.lineWidth = 2.6;
          ctx.stroke();
        });
      },
      point(x, y, color, radius) {
        ctx.beginPath();
        ctx.arc(px(x), py(y), radius, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.lineWidth = 1.6;
        ctx.strokeStyle = '#fff';
        ctx.stroke();
      },
      polygon(points, stroke, fill) {
        toPixelPath(points);
        ctx.closePath();
        ctx.fillStyle = fill;
        ctx.fill();
        ctx.strokeStyle = stroke;
        ctx.lineWidth = 2.3;
        ctx.stroke();
      },
      path(points, stroke) {
        toPixelPath(points);
        ctx.strokeStyle = stroke;
        ctx.lineWidth = 1.6;
        ctx.stroke();
      },
    };
  }

  function tagged(tag, className, text) {
    const el = document.createElement(tag);
    el.className = 'mathlab__' + className;
    if (text !== undefined) el.textContent = text;
    return el;
  }

  function mount(element, graph) {
    const model = graph && Object.hasOwn(models, graph.type) ? models[graph.type] : null;
    if (!element || !model) return undefined;
    const card = document.createElement('section');
    card.className = 'mathlab';
    const heading = tagged('div', 'head');
    const legend = tagged('div', 'legend');
    if (graph.type !== 'triangle') legend.setAttribute('data-lines', '');
    const tags = [tagged('span', 'tag'), tagged('span', 'tag')];
    legend.append(...tags);
    heading.append(tagged('strong', 'name', model.title), legend);
    const canvas = tagged('canvas', 'plot');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', model.title);
    const controls = tagged('div', 'controls');
    const result = tagged('p', 'result');
    result.setAttribute('aria-live', 'polite');
    const accessible = document.createElement('details');
    accessible.className = 'mathlab__alternative';
    const accessibleTitle = document.createElement('summary');
    accessibleTitle.textContent = 'Формулы и координаты';
    const description = document.createElement('p');
    const coordinates = document.createElement('table');
    coordinates.className = 'data-table';
    accessible.append(accessibleTitle, description, coordinates);
    card.append(heading, canvas, controls, result, accessible);
    element.replaceChildren(card);

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      canvas.hidden = true;
      result.textContent = 'Этот браузер не поддерживает построение графика.';
      return undefined;
    }
    const state = {};
    let frame = 0;

    function updateCoordinates(view) {
      description.textContent = view.legend.join('; ') + '. ' + view.result;
      const rows = graph.type === 'triangle'
        ? [['Вершина', 'x', 'y'], ['A', 0, 0], ['B', state.base, 0], ['C', 0, state.height]]
        : [['x', view.legend[0], view.legend[1]], ...Array.from({length: 5}, (_, index) => {
            const center = graph.type === 'quadratic' && state.a !== 0 ? -state.b / (2 * state.a) : 0;
            const x = center + index - 2;
            return graph.type === 'quadratic'
              ? [x, state.a * x * x + state.b * x + state.c, state.level]
              : [x, state.m1 * x + state.b1, state.m2 * x + state.b2];
          })];
      const header = document.createElement('thead');
      const headerRow = document.createElement('tr');
      rows[0].forEach(text => {
        const cell = document.createElement('th');
        cell.scope = 'col';
        cell.textContent = text;
        headerRow.append(cell);
      });
      header.append(headerRow);
      const body = document.createElement('tbody');
      rows.slice(1).forEach(values => {
        const row = document.createElement('tr');
        values.forEach((value, index) => {
          const cell = document.createElement(index === 0 ? 'th' : 'td');
          if(index === 0) cell.scope = 'row';
          cell.textContent = typeof value === 'number' ? fmt(value) : value;
          row.append(cell);
        });
        body.append(row);
      });
      coordinates.replaceChildren(header, body);
    }

    function update() {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        if (canvas.clientWidth < 75 || canvas.clientHeight < 50) return;
        const view = model.draw(state, createPlot(canvas, ctx));
        view.legend.forEach((label, index) => { tags[index].textContent = label; });
        if (result.textContent !== view.result) result.textContent = view.result;
        canvas.setAttribute('aria-label', model.title + '. ' + view.legend.join('; ') + '. ' + view.result);
        updateCoordinates(view);
      });
    }

    for (const [key, label, fallback, min, max, step] of model.controls) {
      const initial = typeof graph[key] === 'number' && Number.isFinite(graph[key]) ? graph[key] : fallback;
      state[key] = initial;
      const wrapper = tagged('label', 'control');
      const value = document.createElement('output');
      value.value = fmt(initial);
      const input = document.createElement('input');
      input.type = 'range';
      input.min = String(Math.min(min, initial - step));
      input.max = String(Math.max(max, initial + step));
      input.step = String(step);
      input.value = String(initial);
      input.setAttribute('aria-label', label);
      input.addEventListener('input', () => {
        state[key] = Number(input.value);
        value.value = fmt(state[key]);
        update();
      });
      wrapper.append(tagged('span', 'label', label), value, input);
      controls.append(wrapper);
    }

    const resize = new ResizeObserver(() => {
      if (!card.isConnected) dispose();
      else update();
    });
    function dispose() {
      resize.disconnect();
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
    }
    resize.observe(canvas);
    update();
    return dispose;
  }

  window.MathLab = { mount, createPlot };
})();
