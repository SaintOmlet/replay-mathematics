(() => {
  "use strict";

  const WIDTH = 400;
  const HEIGHT = 224;
  const ink = "#303634";
  const soft = "#666f6b";
  const primary = "#315d78";
  const green = "#466a52";
  const line = "#bdc7c0";
  const { PI, atan2, cos, hypot, sin, sqrt } = Math;
  const point = (x, y) => ({ x, y });
  const midpoint = (a, b) => point((a.x + b.x) / 2, (a.y + b.y) / 2);
  const polar = (center, r, angle) => point(center.x + r * cos(angle), center.y + r * sin(angle));

  function painter(ctx, canvasWidth) {
    function path(points, { color = ink, width = 1.7, dash = [], close = false, fill = "" } = {}) {
      ctx.save();
      ctx.beginPath();
      points.forEach(({ x, y }, i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
      if (close) ctx.closePath();
      if (fill) { ctx.fillStyle = fill; ctx.fill(); }
      ctx.setLineDash(dash);
      ctx.lineWidth = width;
      ctx.strokeStyle = color;
      ctx.stroke();
      ctx.restore();
    }
    function arc(center, radius, start, end, color = primary, width = 2) {
      ctx.save();
      ctx.beginPath();
      ctx.arc(center.x, center.y, radius, start, end);
      ctx.lineWidth = width;
      ctx.strokeStyle = color;
      ctx.stroke();
      ctx.restore();
    }
    function label(text, x, y, { color = ink, align = "left" } = {}) {
      ctx.save();
      ctx.font = "600 " + Math.max(15, 12 * WIDTH / canvasWidth) + "px system-ui, sans-serif";
      ctx.textBaseline = "middle";
      ctx.textAlign = align;
      ctx.fillStyle = color;
      ctx.fillText(text, x, y);
      ctx.restore();
    }
    function dot(p, color = ink) {
      ctx.save();
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3, 0, 2 * PI);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.restore();
    }
    function tick(a, b) {
      const tip = midpoint(a, b);
      const norm = hypot(b.x - a.x, b.y - a.y);
      const dx = (b.y - a.y) * 5 / norm;
      const dy = (a.x - b.x) * 5 / norm;
      path([point(tip.x - dx, tip.y - dy), point(tip.x + dx, tip.y + dy)], { color: green, width: 2.2 });
    }
    function rightAngle(vertex, a, b, size = 11) {
      const unit = p => {
        const x = p.x - vertex.x;
        const y = p.y - vertex.y;
        const norm = hypot(x, y);
        return point(x * size / norm, y * size / norm);
      };
      const u = unit(a);
      const v = unit(b);
      path([point(vertex.x + u.x, vertex.y + u.y), point(vertex.x + u.x + v.x, vertex.y + u.y + v.y),
        point(vertex.x + v.x, vertex.y + v.y)], { color: soft, width: 1.4 });
    }
    return { path, arc, label, dot, tick, rightAngle };
  }

  function oppositeAngles({ path, arc, label, dot }) {
    const O = point(200, 113);
    const angle = .70;
    const A = polar(O, 127, PI);
    const B = polar(O, 127, -angle);
    const C = polar(O, 127, 0);
    const D = polar(O, 127, PI - angle);
    path([A, C]);
    path([B, D]);
    arc(O, 46, -angle, 0);
    arc(O, 46, PI - angle, PI);
    arc(O, 31, PI, 2 * PI - angle, soft, 1.2);
    dot(O);
    label("A", A.x - 16, A.y);
    label("B", B.x + 8, B.y - 6);
    label("C", C.x + 8, C.y);
    label("D", D.x - 16, D.y + 6);
    label("O", O.x + 6, O.y + 15);
    label("α", 256, 94, { color: primary });
    label("α", 136, 137, { color: primary });
    label("β", 176, 71, { color: soft });
  }

  function parallelLines({ path, arc, label, dot }) {
    const upper = point(170, 69);
    const lower = point(228, 155);
    const direction = atan2(lower.y - upper.y, lower.x - upper.x);
    path([point(53, upper.y), point(348, upper.y)]);
    path([point(53, lower.y), point(348, lower.y)]);
    path([polar(upper, 46, direction + PI), polar(lower, 55, direction)]);
    arc(upper, 38, 0, direction);
    arc(lower, 38, PI, PI + direction);
    dot(upper);
    dot(lower);
    label("p", 357, upper.y + 3);
    label("q", 357, lower.y + 3);
    label("s", 269, 205);
    label("α", 214, 90, { color: primary });
    label("α", 175, 130, { color: primary });
  }

  function isosceles({ path, label, dot, tick, rightAngle }) {
    const A = point(200, 29);
    const B = point(74, 171);
    const C = point(326, 171);
    const D = midpoint(B, C);
    path([A, B, C], { close: true });
    path([A, D], { color: primary, width: 2.2 });
    tick(A, B);
    tick(A, C);
    rightAngle(D, A, C);
    [A, B, C, D].forEach(p => dot(p));
    label("A", A.x, A.y - 14, { align: "center" });
    label("B", B.x - 14, B.y + 1);
    label("C", C.x + 8, C.y + 1);
    label("D", D.x, D.y + 16, { align: "center" });
  }

  function tangents({ path, arc, label, dot, tick, rightAngle }) {
    const O = point(144, 112);
    const P = point(324, 112);
    const radius = 69;
    const tangentOffset = radius * radius / (P.x - O.x);
    const height = sqrt(radius * radius - tangentOffset * tangentOffset);
    const A = point(O.x + tangentOffset, O.y - height);
    const B = point(O.x + tangentOffset, O.y + height);
    arc(O, radius, 0, 2 * PI, ink, 1.7);
    path([A, P, B], { color: primary, width: 2 });
    path([A, O, B], { color: soft });
    rightAngle(A, O, P);
    rightAngle(B, O, P);
    tick(A, P);
    tick(B, P);
    [A, B, O, P].forEach(p => dot(p));
    label("A", A.x + 8, A.y - 8);
    label("B", B.x + 8, B.y + 8);
    label("O", O.x - 17, O.y);
    label("P", P.x + 9, P.y);
  }

  function trapezoid({ path, label, dot, tick }) {
    const A = point(110, 58);
    const B = point(235, 58);
    const C = point(319, 175);
    const D = point(74, 175);
    const M = midpoint(A, D);
    const N = midpoint(B, C);
    path([A, B, C, D], { close: true });
    path([M, N], { color: primary, width: 2.2 });
    tick(A, M);
    tick(M, D);
    tick(B, N);
    tick(N, C);
    [A, B, C, D, M, N].forEach(p => dot(p));
    label("A", A.x, A.y - 14, { align: "center" });
    label("B", B.x, B.y - 14, { align: "center" });
    label("C", C.x + 8, C.y);
    label("D", D.x - 17, D.y);
    label("M", M.x - 22, M.y);
    label("N", N.x + 9, N.y);
  }

  function rightMetric({ path, label, dot, rightAngle }) {
    const A = point(69, 177);
    const B = point(331, 177);
    const H = point(167, A.y);
    const C = point(H.x, H.y - sqrt((H.x - A.x) * (B.x - H.x)));
    path([A, C, B, A]);
    path([C, H], { color: primary, width: 2.2 });
    rightAngle(C, A, B);
    rightAngle(H, C, B);
    [A, B, C, H].forEach(p => dot(p));
    label("A", A.x - 16, A.y);
    label("B", B.x + 8, B.y);
    label("C", C.x, C.y - 14, { align: "center" });
    label("H", H.x, H.y + 16, { align: "center" });
  }

  function unitCircle({ path, arc, label, dot }) {
    const O = point(190, 111);
    const radius = 73;
    const angle = .65;
    const P = polar(O, radius, -angle);
    const X = point(P.x, O.y);
    const Y = point(O.x, P.y);
    path([point(86, O.y), point(326, O.y)], { color: soft });
    path([point(O.x, 203), point(O.x, 21)], { color: soft });
    path([point(318, O.y - 4), point(326, O.y), point(318, O.y + 4)], { color: soft });
    path([point(O.x - 4, 29), point(O.x, 21), point(O.x + 4, 29)], { color: soft });
    arc(O, radius, 0, 2 * PI, ink, 1.7);
    path([Y, P, X], { color: green, dash: [4, 3] });
    path([O, P], { color: primary, width: 2.2 });
    arc(O, 24, -angle, 0);
    dot(O);
    dot(P, primary);
    label("P", P.x + 9, P.y - 6, { color: primary });
    label("O", O.x - 17, O.y + 13);
    label("x", 335, O.y);
    label("y", O.x + 10, 19);
    label("t", O.x + 31, O.y - 10, { color: primary });
    label("cos t", X.x, X.y + 17, { color: green, align: "center" });
    label("sin t", Y.x - 9, Y.y, { color: green, align: "right" });
  }

  function sector({ path, arc, label, dot }) {
    const O = point(188, 114);
    const radius = 75;
    const start = -1.26;
    const end = -.18;
    const A = polar(O, radius, start);
    const B = polar(O, radius, end);
    const curved = Array.from({ length: 33 }, (_, i) => polar(O, radius, start + i * (end - start) / 32));
    path([O, ...curved], { color: primary, fill: "#e7eee8", close: true, width: 1.2 });
    arc(O, radius, 0, 2 * PI, soft, 1.5);
    arc(O, radius, start, end, primary, 2.6);
    path([A, O, B], { color: primary, width: 2 });
    arc(O, 28, start, end);
    [A, B, O].forEach(p => dot(p));
    label("A", A.x + 5, A.y - 11);
    label("B", B.x + 9, B.y);
    label("O", O.x - 15, O.y + 14);
    label("θ", O.x + 28, O.y - 24, { color: primary });
  }

  function mastHeight({ path, arc, label, dot, rightAngle }) {
    const O=point(306,178), T=point(306,30), A=point(202,178), B=point(60,178);
    path([B,O,T], { color: ink });
    path([A,T], { color: primary });
    path([B,T], { color: soft, dash: [5,4] });
    rightAngle(O,A,T);
    arc(A,30,atan2(T.y-A.y,T.x-A.x),0,primary,1.5);
    arc(B,40,atan2(T.y-B.y,T.x-B.x),0,soft,1.5);
    [O,T,A,B].forEach(p=>dot(p));
    label("O",O.x+8,O.y+5);
    label("T",T.x+8,T.y);
    label("A",A.x-4,A.y+19);
    label("B",B.x-4,B.y+19);
    label("h",O.x+12,108,{color:primary});
    label("x",252,193,{color:primary});
    label("d",124,193);
    label("θ",230,163,{color:primary});
    label("φ",107,163,{color:soft});
  }

  const diagrams = new Map([
    ["g8-right-trig", {
      draw: mastHeight,
      label: "Мачта OT перпендикулярна земле. Точки O, A, B лежат на одной прямой в этом порядке. Наблюдение из A и B ведётся с уровня земли. OA = x, AB = d, OT = h. Угол подъёма из A равен θ, из B равен φ, θ больше φ.",
      caption: "Модель мачты. tan θ = h/x, tan φ = h/(x+d). Высота наблюдения равна нулю."
    }],
    ["g7-adjacent-vertical", {
      draw: oppositeAngles,
      label: "Прямые AC и BD пересекаются в O. Вертикальные AOD и BOC отмечены одинаковыми дугами α. Смежный AOB подписан β.",
      caption: "Вертикальные ∠AOD и ∠BOC равны. Углы α и β смежные, их сумма 180°."
    }],
    ["g7-parallel-transversal", {
      draw: parallelLines,
      label: "Две горизонтальные параллельные прямые p и q пересекает секущая s. Два внутренних угла с противоположных сторон секущей отмечены одинаковыми дугами.",
      caption: "При p ∥ q отмеченные внутренние накрест лежащие углы равны."
    }],
    ["g7-isosceles", {
      draw: isosceles,
      label: "Равнобедренный треугольник ABC. На сторонах AB и AC одинаковые отметки. Под медианой AD у середины основания D показан прямой угол.",
      caption: "В равнобедренном ABC медиана AD к основанию BC служит высотой и биссектрисой."
    }],
    ["g7-circle-tangency", {
      draw: tangents,
      label: "Из P проведены касательные к окружности с центром O. Они касаются в точках A и B. Радиусы OA и OB перпендикулярны касательным.",
      caption: "PA = PB. В точках касания OA ⟂ PA, OB ⟂ PB."
    }],
    ["g8-midlines-trapezoid", {
      draw: trapezoid,
      label: "Трапеция ABCD с параллельными основаниями AB и CD. M и N расположены посередине боковых сторон AD и BC.",
      caption: "Средняя линия MN параллельна основаниям, MN = (AB + CD) / 2."
    }],
    ["g8-right-metric", {
      draw: rightMetric,
      label: "Треугольник ABC с прямым углом C. Из C опущена высота CH на гипотенузу AB. Она разделяет гипотенузу на AH и HB.",
      caption: "Высота к гипотенузе: CH² = AH · HB."
    }],
    ["g9-unit-circle", {
      draw: unitCircle,
      label: "На единичной окружности точка P получена поворотом на угол t от положительного направления оси x. Проекции точки на оси дают cos t и sin t.",
      caption: "Точка на единичной окружности имеет координаты P(cos t; sin t)."
    }],
    ["g9-arcs-sectors", {
      draw: sector,
      label: "Радиусы OA и OB ограничивают выделенный сектор. Дуга AB отмечена толстой линией. Центральный угол обозначен θ.",
      caption: "При θ в радианах длина дуги равна rθ, площадь сектора равна r²θ / 2."
    }]
  ]);

  function mount(element, topicId) {
    const diagram = diagrams.get(topicId);
    if (!element || !diagram) return;
    const figure = document.createElement("figure");
    const canvas = document.createElement("canvas");
    const caption = document.createElement("figcaption");
    figure.className = "geometry-figure";
    figure.style.margin = "0";
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", diagram.label);
    canvas.textContent = diagram.label;
    canvas.style.display = "block";
    canvas.style.width = "100%";
    canvas.style.maxWidth = "560px";
    canvas.style.aspectRatio = WIDTH + " / " + HEIGHT;
    canvas.style.marginInline = "auto";
    caption.textContent = diagram.caption;
    caption.className = "muted compact-copy";
    caption.style.padding = "0 10px 8px";
    figure.append(canvas, caption);
    element.replaceChildren(figure);

    const ctx = canvas.getContext("2d");
    if (!ctx) return () => figure.remove();
    function redraw() {
      const cssWidth = canvas.clientWidth;
      if (!cssWidth) return;
      const ratio = Math.min(window.devicePixelRatio || 1, 3);
      const cssHeight = cssWidth * HEIGHT / WIDTH;
      canvas.width = Math.round(cssWidth * ratio);
      canvas.height = Math.round(cssHeight * ratio);
      ctx.setTransform(canvas.width / WIDTH, 0, 0, canvas.height / HEIGHT, 0, 0);
      ctx.fillStyle = "#fafbf8";
      ctx.fillRect(0, 0, WIDTH, HEIGHT);
      ctx.strokeStyle = line;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      diagram.draw(painter(ctx, cssWidth));
    }
    let observer;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(redraw);
      observer.observe(figure);
    }
    redraw();
    return () => { observer?.disconnect(); figure.remove(); };
  }

  window.ReplayGeometry = Object.freeze({ has: topicId => diagrams.has(topicId), mount });
})();
