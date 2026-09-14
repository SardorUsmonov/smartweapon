// Deterministic label layout: attraction to geography, then collision separation.
// Inputs and returned boxes use container pixels; this module does not touch the DOM.
export function layoutRegionBoxes(items, width, height) {
  const left = 10, top = 48, right = width - 10, bottom = height - 55, gap = 6;
  const obstacle = { x: width - 62, y: 0, w: 62, h: 100 };
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const source = items.map(item => ({ ...item, id: item.id, ax: item.x, ay: item.y }))
    .sort((a, b) => a.ay - b.ay || a.ax - b.ax || String(a.id).localeCompare(String(b.id)));
  const intersects = (a, b) => a.x < b.x + b.w + gap - .01 && a.x + a.w + gap - .01 > b.x && a.y < b.y + b.h + gap - .01 && a.y + a.h + gap - .01 > b.y;
  function constrain(box) {
    box.x = clamp(box.x, left, right - box.w);
    box.y = clamp(box.y, top, bottom - box.h);
    if (intersects(box, obstacle)) {
      const dx = box.x + box.w + gap - obstacle.x;
      const dy = obstacle.y + obstacle.h + gap - box.y;
      if (dx < dy && box.x - dx >= left) box.x -= dx;
      else box.y += dy;
    }
  }
  function separation(a, b, axis) {
    const horizontal = axis === 'x';
    const size = horizontal ? 'w' : 'h';
    const anchor = horizontal ? 'ax' : 'ay';
    const delta = b[anchor] - a[anchor];
    const sign = delta === 0 ? (String(a.id) < String(b.id) ? 1 : -1) : Math.sign(delta);
    const ac = a[axis] + a[size] / 2, bc = b[axis] + b[size] / 2;
    const amount = (a[size] + b[size]) / 2 + gap - sign * (bc - ac);
    const min = horizontal ? left : top, max = horizontal ? right : bottom;
    const roomA = sign > 0 ? a[axis] - min : max - a[axis] - a[size];
    const roomB = sign > 0 ? max - b[axis] - b[size] : b[axis] - min;
    const distance = Math.hypot(b.ax - a.ax, b.ay - a.ay) || 1;
    return { axis, sign, amount, roomA, roomB,
      cost: amount / (.35 + Math.abs(delta) / distance) + (roomA + roomB < amount ? 10000 : 0) };
  }
  function repel(a, b) {
    if (!intersects(a, b)) return;
    const sx = separation(a, b, 'x'), sy = separation(a, b, 'y');
    const move = sx.cost < sy.cost ? sx : sy;
    let da = Math.min(move.roomA, move.amount / 2);
    const db = Math.min(move.roomB, move.amount - da);
    da = Math.min(move.roomA, move.amount - db);
    a[move.axis] -= move.sign * da;
    b[move.axis] += move.sign * db;
    constrain(a); constrain(b);
  }
  function score(boxes) {
    let cost = 0;
    boxes.forEach((box, i) => {
      cost += Math.hypot(box.x + box.w / 2 - box.ax, box.y + box.h / 2 - box.ay) ** 2;
      for (let j = 0; j < i; j++) if (intersects(box, boxes[j])) cost += 1e9;
    });
    return cost;
  }
  function repair(boxes) {
    // A chain of labels against the right edge can defeat local repulsion.
    // Relocate only a remaining collision to the nearest complete free rectangle.
    for (let pass = 0; pass < boxes.length; pass++) {
      const crowded = boxes.map(box => ({ box, count: boxes.filter(other => other !== box && intersects(box, other)).length }))
        .filter(item => item.count).sort((a, b) => b.count - a.count);
      if (!crowded.length) return;
      let moved = false;
      for (const { box } of crowded) {
        const others = boxes.filter(other => other !== box);
        const xs = [left, right - box.w, clamp(box.ax - box.w / 2, left, right - box.w), box.x];
        const ys = [top, bottom - box.h, clamp(box.ay - box.h / 2, top, bottom - box.h), box.y];
        for (const other of [...others, obstacle]) {
          xs.push(other.x - box.w - gap, other.x + other.w + gap);
          ys.push(other.y - box.h - gap, other.y + other.h + gap);
        }
        let placement, cost = Infinity;
        for (const x of xs) for (const y of ys) {
          const candidate = { ...box, x, y };
          if (x < left || y < top || x + box.w > right || y + box.h > bottom || intersects(candidate, obstacle) || others.some(other => intersects(candidate, other))) continue;
          const cx = x + box.w / 2, cy = y + box.h / 2;
          let value = (cx - box.ax) ** 2 + (cy - box.ay) ** 2;
          for (const other of others) {
            if (Math.abs(box.ay - other.ay) > 12 && Math.abs(box.ax - other.ax) < 130) {
              const inversion = Math.max(0, -Math.sign(box.ay - other.ay) * (cy - other.y - other.h / 2));
              value += inversion ** 2 * 2;
            }
          }
          if (value < cost) { placement = candidate; cost = value; }
        }
        if (placement) { box.x = placement.x; box.y = placement.y; moved = true; break; }
      }
      if (!moved) return;
    }
  }
  let best = [], bestScore = Infinity;
  for (let attempt = 0; attempt < 4; attempt++) {
    const boxes = source.map((item, i) => {
      const box = { ...item, x: item.ax - item.w / 2, y: item.ay - item.h / 2 };
      if (attempt) {
        box.x += Math.sin((i + 1) * (attempt + 1) * 2.399) * attempt * 12;
        box.y += Math.cos((i + 1) * (attempt + 1) * 2.399) * attempt * 12;
      }
      constrain(box); return box;
    });
    for (let step = 0; step < 180; step++) {
      const attraction = step < 110 ? .025 * (1 - step / 130) : 0;
      for (const box of boxes) {
        box.x += (box.ax - box.w / 2 - box.x) * attraction;
        box.y += (box.ay - box.h / 2 - box.y) * attraction;
        constrain(box);
      }
      for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) repel(boxes[i], boxes[j]);
    }
    repair(boxes);
    const cost = score(boxes);
    if (cost < bestScore) { best = boxes; bestScore = cost; }
  }
  return new Map(best.map(box => [box.id, { id: box.id, x: box.x, y: box.y, w: box.w, h: box.h }]));
}
