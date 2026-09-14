/* Relief view of the leadership map.
   The SVG map (leadership-map.js) stays the source of truth for data, links,
   selection, zoom and the alert filter; this module mirrors that state as a
   lit, extruded relief. Every region has the same height: height is a visual
   device, not a measure. Without WebGL, or in the flat view, the SVG remains. */
import * as THREE from 'three';
import { SVGLoader } from '../vendor/three/SVGLoader.js';
import { OrbitControls } from '../vendor/three/OrbitControls.js';

const DEPTH = 24, RAISE = 7, HOVER = 3, VIEW_KEY = 'aq-map-view';
const OFFSETS = {
  'UZ-TK': [-18, -30], 'UZ-TO': [12, -6], 'UZ-NG': [14, -24], 'UZ-AN': [28, 4], 'UZ-FA': [12, 26],
  'UZ-SI': [0, 22], 'UZ-JI': [-24, -8], 'UZ-QR': [0, -8], 'UZ-XO': [-6, 14], 'UZ-NW': [0, 4]
};
const CANDIDATES = [[0, -1], [0, 1], [-1, 0], [1, 0], [-1, -1], [1, -1], [-1, 1], [1, 1]];
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const overview = document.getElementById('executive-overview');

function webglAvailable() {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(window.WebGLRenderingContext && (canvas.getContext('webgl2') || canvas.getContext('webgl')));
  } catch (_) { return false; }
}
function storedView() { try { return localStorage.getItem(VIEW_KEY) === '2d' ? '2d' : '3d'; } catch (_) { return '3d'; } }
function rememberView(value) { try { localStorage.setItem(VIEW_KEY, value); } catch (_) { /* private mode */ } }
function el(tag, className, parent) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (parent) parent.append(node);
  return node;
}
function ease(t) { return 1 - Math.pow(1 - t, 3); }

class Relief {
  constructor(geo) {
    this.geo = geo;
    this.regions = new Map();
    this.pickable = [];
    this.view = 'tilt';
    this.focusCode = null;
    this.hovered = null;
    this.host = el('div', 'lm3-host');
    this.labels = el('div', 'lm3-labels');
    this.leaders = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    this.leaders.classList.add('lm3-leaders');
    this.leaders.setAttribute('aria-hidden', 'true');
    this.tip = el('div', 'lm3-tip');
    this.tip.hidden = true;
    this.tools = el('div', 'lm3-tools');
    this.hint = el('p', 'lm3-hint');

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    const canvas = this.renderer.domElement;
    canvas.setAttribute('aria-hidden', 'true');
    this.host.append(canvas, this.leaders, this.labels, this.tip, this.hint, this.tools);

    this.scene = new THREE.Scene();
    this.camera = new THREE.OrthographicCamera(-450, 450, 300, -300, 1, 4000);
    this.camera.up.set(0, 0, 1);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = false;
    this.controls.enablePan = false;
    this.controls.enableZoom = false;
    this.controls.minPolarAngle = .02;
    this.controls.maxPolarAngle = 1.08;
    this.controls.rotateSpeed = .5;
    this.resetCamera();

    this.scene.add(new THREE.AmbientLight(0xffffff, 1.35));
    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(-260, 320, 820);
    key.castShadow = true;
    key.shadow.mapSize.set(1536, 1536);
    Object.assign(key.shadow.camera, { left: -700, right: 700, top: 620, bottom: -620, near: 1, far: 2200 });
    key.shadow.normalBias = 1;
    key.shadow.bias = -.0002;
    this.scene.add(key);
    this.fill = new THREE.DirectionalLight(0x93bfe2, .6);
    this.fill.position.set(480, -260, 420);
    this.scene.add(this.fill);

    this.floor = new THREE.Mesh(new THREE.PlaneGeometry(1400, 1100), new THREE.ShadowMaterial({ opacity: .22 }));
    this.floor.position.z = -1.5;
    this.floor.receiveShadow = true;
    this.scene.add(this.floor);
    this.grid = new THREE.GridHelper(1240, 31, 0x60778b, 0x60778b);
    this.grid.rotation.x = Math.PI / 2;
    this.grid.position.z = -1;
    this.grid.material.transparent = true;
    this.grid.material.opacity = .05;
    this.scene.add(this.grid);

    const loader = new SVGLoader();
    for (const [code, region] of Object.entries(geo.regions)) {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      const path = document.createElementNS(svg.namespaceURI, 'path');
      path.setAttribute('d', region.d);
      svg.append(path);
      const shapes = loader.parse(new XMLSerializer().serializeToString(svg)).paths.flatMap(SVGLoader.createShapes);
      const geometry = new THREE.ExtrudeGeometry(shapes, { depth: DEPTH, bevelEnabled: true, bevelThickness: 1.4, bevelSize: 1, bevelSegments: 2, curveSegments: 6 });
      geometry.rotateX(Math.PI);
      geometry.translate(-geo.w / 2, geo.h / 2, DEPTH);
      const face = new THREE.MeshStandardMaterial({ roughness: .58, metalness: .06, transparent: true });
      const side = new THREE.MeshStandardMaterial({ roughness: .8, metalness: .1, transparent: true });
      const mesh = new THREE.Mesh(geometry, [face, side]);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.userData.code = code;
      const group = new THREE.Group();
      group.add(mesh);
      const edge = new THREE.LineBasicMaterial({ transparent: true, opacity: .55 });
      const ring = new THREE.LineBasicMaterial({ transparent: true, opacity: .95 });
      const outlines = [], rings = [];
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (const shape of shapes) {
        for (const outline of [shape, ...shape.holes]) {
          const points = outline.getPoints(6).map(p => new THREE.Vector3(p.x - geo.w / 2, geo.h / 2 - p.y, DEPTH + .3));
          points.forEach(p => { minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x); minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y); });
          const buffer = new THREE.BufferGeometry().setFromPoints(points);
          const line = new THREE.LineLoop(buffer, edge);
          outlines.push(line);
          group.add(line);
          const highlight = new THREE.LineLoop(buffer, ring);
          highlight.position.z = .6;
          highlight.visible = false;
          rings.push(highlight);
          group.add(highlight);
        }
      }
      this.scene.add(group);
      const label = el('div', 'lm3-label');
      label.dataset.lmRegion = code;
      label.setAttribute('role', 'button');
      label.tabIndex = 0;
      const name = el('span', 'lm3-name', label);
      name.textContent = region.short;
      const count = el('i', 'lm3-count', label);
      count.hidden = true;
      label.addEventListener('pointerenter', () => this.hover(code, true));
      label.addEventListener('pointerleave', () => { if (document.activeElement !== label) this.hover(null); });
      label.addEventListener('focus', () => this.hover(code, true));
      label.addEventListener('blur', () => this.hover(null));
      label.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); label.click(); }
        if (event.key === 'Escape') this.hover(null);
      });
      this.labels.append(label);
      const leader = document.createElementNS(this.leaders.namespaceURI, 'line');
      this.leaders.append(leader);
      this.regions.set(code, {
        group, mesh, face, side, edge, ring, rings, label, name, count, leader,
        anchor: new THREE.Vector3(region.cx - geo.w / 2, geo.h / 2 - region.cy, DEPTH + 2),
        bounds: { minX, maxX, minY, maxY }, row: null, state: 'context', selected: false, muted: false
      });
    }

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.controls.addEventListener('change', () => { this.hideTip(); this.draw(); });
    canvas.addEventListener('pointerdown', event => {
      this.drag = { x: event.clientX, y: event.clientY, id: event.pointerId, moved: false };
      this.hover(null);
    });
    canvas.addEventListener('pointermove', event => {
      if (this.drag) {
        this.drag.moved ||= Math.hypot(event.clientX - this.drag.x, event.clientY - this.drag.y) > 5;
        if (this.drag.moved) this.host.classList.add('is-dragging');
        return;
      }
      this.hover(this.pick(event), true);
    });
    canvas.addEventListener('pointerup', event => {
      const drag = this.drag;
      this.drag = null;
      this.host.classList.remove('is-dragging');
      if (drag && drag.id === event.pointerId && !drag.moved) this.choose(this.pick(event));
    });
    canvas.addEventListener('pointercancel', () => { this.drag = null; this.host.classList.remove('is-dragging'); });
    canvas.addEventListener('pointerleave', () => { if (!this.drag) this.hover(null); });
    canvas.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      this.failed = true;
      this.detach();
      this.onFailure?.();
    });
    this.buildTools();
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.themeObserver = new MutationObserver(() => { this.setPalette(); this.draw(); });
    this.themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  }

  buildTools() {
    const icon = d => `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
    const glyph = {
      tilt: icon('<path d="M3 15l9-5 9 5-9 5-9-5Z"/><path d="M3 15v3l9 5 9-5v-3"/>'),
      top: icon('<rect x="4" y="4" width="16" height="16" rx="1.5"/><path d="M4 12h16M12 4v16"/>'),
      in: icon('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5M8 11h6M11 8v6"/>'),
      out: icon('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5M8 11h6"/>'),
      reset: icon('<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/>')
    };
    const make = (action, key) => {
      const button = el('button', '', this.tools);
      button.type = 'button';
      button.dataset.lm3 = action;
      button.innerHTML = glyph[key];
      button.addEventListener('click', () => this.act(action));
      return button;
    };
    make('tilt', 'tilt'); make('top', 'top');
    el('i', '', this.tools);
    make('in', 'in'); make('out', 'out');
    el('i', '', this.tools);
    make('reset', 'reset');
  }

  act(action) {
    this.hover(null);
    if (action === 'in' || action === 'out') {
      this.animate({ zoom: THREE.MathUtils.clamp(this.camera.zoom * (action === 'in' ? 1.3 : .77), .75, 5) });
    } else if (action === 'tilt' || action === 'top') {
      this.view = action;
      this.applyView();
    } else {
      this.view = 'tilt';
      this.focusCode = null;
      this.resetCamera(true);
    }
    this.syncTools();
  }

  syncTools() {
    this.tools.querySelectorAll('[data-lm3="tilt"], [data-lm3="top"]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.lm3 === this.view));
    });
    if (this.strings) {
      const titles = { tilt: this.strings.tiltView, top: this.strings.topView, in: this.strings.zoomIn, out: this.strings.zoomOut, reset: this.strings.resetView };
      this.tools.querySelectorAll('button').forEach(button => {
        button.title = titles[button.dataset.lm3] || '';
        button.setAttribute('aria-label', titles[button.dataset.lm3] || '');
      });
    }
  }

  resetCamera(smooth = false) {
    const target = new THREE.Vector3(0, 0, DEPTH / 2);
    if (smooth && !reduced.matches) return this.animate({ target, zoom: 1, view: this.view });
    this.controls.target.copy(target);
    this.placeCamera(this.view, target);
    this.camera.zoom = 1;
    this.controls.enableRotate = this.view !== 'top';
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.draw();
  }

  placeCamera(view, target) {
    const offset = view === 'top' ? new THREE.Vector3(0, -.5, 1200) : new THREE.Vector3(70, -720, 900);
    this.camera.position.copy(target).add(offset);
  }

  applyView() {
    this.controls.enableRotate = this.view !== 'top';
    this.animate({ view: this.view });
  }

  /* Short camera transitions; instant when the person prefers reduced motion. */
  animate({ target, zoom, view }) {
    const from = { target: this.controls.target.clone(), position: this.camera.position.clone(), zoom: this.camera.zoom };
    const to = { target: target ? target.clone() : from.target.clone(), zoom: zoom ?? from.zoom };
    if (view) {
      // OrbitControls measures angles in a y-up frame; the scene is z-up.
      const toYUp = new THREE.Quaternion().setFromUnitVectors(this.camera.up, new THREE.Vector3(0, 1, 0));
      const fromYUp = toYUp.clone().invert();
      const spherical = new THREE.Spherical().setFromVector3(from.position.clone().sub(from.target).applyQuaternion(toYUp));
      const goal = new THREE.Spherical(spherical.radius, view === 'top' ? .02 : .67, spherical.theta);
      to.position = new THREE.Vector3().setFromSpherical(goal).applyQuaternion(fromYUp).add(to.target);
    } else {
      to.position = from.position.clone().sub(from.target).add(to.target);
    }
    if (reduced.matches) return this.jump(to);
    cancelAnimationFrame(this.frame);
    const start = performance.now();
    const step = now => {
      const k = ease(Math.min(1, (now - start) / 280));
      this.controls.target.lerpVectors(from.target, to.target, k);
      this.camera.position.lerpVectors(from.position, to.position, k);
      this.camera.zoom = from.zoom + (to.zoom - from.zoom) * k;
      this.camera.updateProjectionMatrix();
      this.controls.update();
      this.draw();
      if (k < 1) this.frame = requestAnimationFrame(step);
    };
    this.frame = requestAnimationFrame(step);
  }

  jump(to) {
    this.controls.target.copy(to.target);
    this.camera.position.copy(to.position);
    this.camera.zoom = to.zoom;
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.draw();
  }

  /* ---- binding to the server-rendered overview ---- */
  attach(root) {
    if (this.failed || !root) return;
    const stage = root.querySelector('.lm-map-stage'), svg = root.querySelector('[data-lm-map]');
    if (!stage || !svg) return;
    this.detach();
    this.root = root; this.stage = stage; this.svg = svg;
    try {
      this.data = JSON.parse(root.querySelector('[data-lm-data]').textContent);
      this.strings = JSON.parse(root.querySelector('[data-lm-strings]').textContent);
    } catch (_) { return; }
    const rows = new Map(this.data.regions.map(row => [row.code, row]));
    for (const [code, region] of this.regions) {
      const row = rows.get(code) || null;
      region.row = row;
      region.state = row ? row.state : 'context';
      region.name.textContent = row ? row.short : this.geo.regions[code].short;
      const status = row ? `${this.strings[row.state] || this.strings.unknown}${row.stale ? ` · ${this.strings.stale}` : ''}` : '';
      region.status = status;
      region.label.hidden = !row;
      region.label.setAttribute('aria-label', row ? `${row.name}: ${status}` : '');
      region.label.title = row ? `${row.name} · ${status}` : '';
      region.mesh.castShadow = Boolean(row);
      const flagged = row && (row.critical || row.warning || row.offline || row.state === 'unknown');
      region.count.hidden = !flagged;
      if (flagged) {
        region.count.textContent = row.state === 'unknown' ? '?' : ((row.critical || 0) + (row.warning || 0) || '!');
        region.count.className = `lm3-count ${row.state}`;
      }
    }
    this.pickable = [...this.regions.values()].filter(region => region.row).map(region => region.mesh);
    this.hint.textContent = this.strings.rotateHint || '';
    this.labels.setAttribute('role', 'group');
    this.labels.setAttribute('aria-label', this.strings.mapLabel || '');
    stage.classList.add('is-3d');
    stage.append(this.host);
    this.north = stage.querySelector('.lm-north');
    this.stateObserver?.disconnect();
    this.stateObserver = new MutationObserver(() => this.syncState());
    this.stateObserver.observe(svg, { subtree: true, childList: true, attributes: true, attributeFilter: ['class'] });
    this.resizeObserver.disconnect();
    this.resizeObserver.observe(stage);
    this.setPalette();
    this.syncTools();
    this.resize();
    this.syncState();
  }

  detach() {
    this.stateObserver?.disconnect();
    this.resizeObserver?.disconnect();
    this.hideTip();
    this.host.remove();
    this.stage?.classList.remove('is-3d');
    if (this.north) this.north.style.transform = '';
    this.stage = null; this.svg = null;
  }

  /* Selection, zoom and the alert filter are read from the SVG's classes. */
  syncState() {
    if (!this.svg) return;
    const selected = this.svg.querySelector('.lm-face.is-selected')?.dataset.lmRegion || null;
    const zoomed = this.svg.classList.contains('is-zoomed');
    const muted = new Set([...this.svg.querySelectorAll('.lm-face.is-muted')].map(node => node.dataset.lmRegion));
    for (const [code, region] of this.regions) {
      region.selected = code === selected;
      region.muted = muted.has(code);
      region.rings.forEach(line => { line.visible = region.selected; });
      region.label.classList.toggle('is-selected', region.selected);
      region.label.classList.toggle('is-muted', region.muted);
      region.label.setAttribute('aria-pressed', String(region.selected));
    }
    this.applyHeights();
    const focus = zoomed && selected ? selected : null;
    if (focus !== this.focusCode) {
      this.focusCode = focus;
      if (focus) this.focusRegion(focus); else this.animate({ target: new THREE.Vector3(0, 0, DEPTH / 2), zoom: 1 });
    }
    this.setPalette();
    this.draw();
  }

  applyHeights() {
    for (const region of this.regions.values()) {
      const lift = region.selected ? RAISE : (this.hovered === region.mesh.userData.code ? HOVER : 0);
      region.group.position.z = lift;
    }
  }

  focusRegion(code) {
    const region = this.regions.get(code);
    if (!region || !this.stage) return;
    const { minX, maxX, minY, maxY } = region.bounds;
    const target = new THREE.Vector3((minX + maxX) / 2, (minY + maxY) / 2, DEPTH);
    const spanX = this.camera.right - this.camera.left, spanY = this.camera.top - this.camera.bottom;
    const fit = Math.min(spanX / Math.max(40, maxX - minX + 60), spanY / Math.max(40, maxY - minY + 60));
    this.animate({ target, zoom: THREE.MathUtils.clamp(fit * .82, 1.4, 5) });
  }

  choose(code) {
    if (!code || !this.svg) return;
    const face = this.svg.querySelector(`.lm-face[data-lm-region="${code}"]`);
    if (!face) return;
    face.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
  }

  setPalette() {
    if (!this.root) return;
    const css = getComputedStyle(this.root);
    const read = (name, fallback) => (css.getPropertyValue(name).trim() || fallback);
    const dark = document.documentElement.dataset.theme === 'dark';
    const tone = { stable: read('--lm-map-stable', '#405e72'), warning: read('--lm-map-warning', '#806b43'),
      critical: read('--lm-map-critical', '#92565e'), unknown: read('--lm-map-unknown', '#45515c'),
      context: read('--lm-map-unknown', '#45515c') };
    const sideColor = new THREE.Color(read('--lm-map-side', '#1c2b37'));
    const lineColor = new THREE.Color(read('--lm-map-line', '#91a3af'));
    const gold = new THREE.Color(read('--lm-gold', '#d1bc8b'));
    for (const region of this.regions.values()) {
      const base = new THREE.Color(tone[region.state] || tone.unknown);
      region.face.color.copy(base);
      region.side.color.copy(region.state === 'context' ? base.clone().lerp(sideColor, .5) : sideColor);
      region.edge.color.copy(lineColor);
      region.ring.color.copy(gold);
      const opacity = region.state === 'context' ? .45 : (region.muted ? .38 : 1);
      region.face.opacity = opacity;
      region.side.opacity = opacity;
      region.edge.opacity = region.state === 'context' ? .2 : (region.muted ? .25 : .55);
      region.face.emissive.set(dark ? '#0b131b' : '#0e1a24');
      region.face.emissiveIntensity = region.state === 'unknown' || region.state === 'context' ? .18 : .08;
    }
    this.floor.material.opacity = dark ? .42 : .2;
    this.grid.material.opacity = dark ? .075 : .045;
    this.fill.intensity = dark ? .5 : .7;
  }

  resize() {
    if (!this.stage?.isConnected || this.failed) return;
    const width = this.stage.clientWidth, height = this.stage.clientHeight;
    if (!width || !height) return;
    this.renderer.setSize(width, height, false);
    const aspect = width / height;
    const span = Math.max(this.geo.h * 1.12, this.geo.w * 1.12 / aspect);
    this.camera.left = -span * aspect / 2;
    this.camera.right = span * aspect / 2;
    this.camera.top = span / 2;
    this.camera.bottom = -span / 2;
    this.camera.updateProjectionMatrix();
    this.draw();
  }

  draw() {
    if (!this.stage?.isConnected || this.failed) return;
    this.renderer.render(this.scene, this.camera);
    if (this.north) this.north.style.transform = `rotate(${-this.controls.getAzimuthalAngle()}rad)`;
    const width = this.stage.clientWidth, height = this.stage.clientHeight;
    // Narrow stages show only the labels that carry information: flagged,
    // selected or pointed-at regions. The region strip below lists the rest.
    const compact = width < 560;
    const placed = [];
    const order = [...Object.keys(OFFSETS), ...[...this.regions.keys()].filter(code => !(code in OFFSETS))];
    for (const code of order) {
      const region = this.regions.get(code);
      const quiet = compact && region.count.hidden && !region.selected && this.hovered !== code;
      if (region.label.hidden || quiet) { region.label.style.visibility = 'hidden'; region.leader.style.display = 'none'; continue; }
      const position = region.anchor.clone();
      position.z += region.group.position.z;
      position.project(this.camera);
      const x = (position.x + 1) * width / 2, y = (1 - position.y) * height / 2;
      const visible = Math.abs(position.x) <= 1 && Math.abs(position.y) <= 1;
      region.label.style.visibility = visible ? 'visible' : 'hidden';
      region.leader.style.display = visible ? '' : 'none';
      if (!visible) continue;
      const w = region.label.offsetWidth, h = region.label.offsetHeight;
      const preferred = OFFSETS[code] || [0, 10];
      const candidates = [preferred, [0, 10]];
      for (const distance of [24, 42, 62, 84, 108]) for (const [dx, dy] of CANDIDATES) candidates.push([dx * distance, dy * distance]);
      let best = null;
      for (const [dx, dy] of candidates) {
        const cx = THREE.MathUtils.clamp(x + dx, w / 2 + 6, width - w / 2 - 6);
        const cy = THREE.MathUtils.clamp(y + dy, 14 + h / 2, height - 60 - h / 2);
        const rect = { left: cx - w / 2 - 3, right: cx + w / 2 + 3, top: cy - h / 2 - 3, bottom: cy + h / 2 + 3 };
        const overlaps = placed.filter(r => rect.left < r.right && rect.right > r.left && rect.top < r.bottom && rect.bottom > r.top).length;
        const score = overlaps * 100000 + (cx - x - preferred[0]) ** 2 + (cy - y - preferred[1]) ** 2;
        if (!best || score < best.score) best = { cx, cy, rect, score };
        if (score === 0) break;
      }
      placed.push(best.rect);
      region.label.style.left = `${best.cx}px`;
      region.label.style.top = `${best.cy}px`;
      region.leader.setAttribute('x1', x); region.leader.setAttribute('y1', y);
      region.leader.setAttribute('x2', best.cx); region.leader.setAttribute('y2', best.cy);
      region.leader.style.opacity = Math.hypot(best.cx - x, best.cy - y) > 18 ? '.55' : '0';
    }
  }

  pick(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
    this.raycaster.setFromCamera(this.pointer, this.camera);
    return this.raycaster.intersectObjects(this.pickable, false)[0]?.object.userData.code || null;
  }

  hover(code, tooltip = false) {
    if (this.hovered !== code) {
      this.hovered = code;
      for (const [key, region] of this.regions) {
        const active = key === code && Boolean(region.row);
        region.label.classList.toggle('is-active', active);
        region.face.emissiveIntensity = active ? .22 : (region.state === 'unknown' || region.state === 'context' ? .18 : .08);
      }
      this.applyHeights();
      this.renderer.domElement.style.cursor = code ? 'pointer' : '';
      this.draw();
    }
    const region = code ? this.regions.get(code) : null;
    if (!tooltip || !region?.row) return this.hideTip();
    const row = region.row, number = value => value == null ? '—' : String(value);
    const heading = el('b'); heading.textContent = row.name;
    const status = el('span'); status.textContent = region.status;
    const counts = el('span');
    counts.textContent = `${number(row.critical)} ${this.strings.criticalLabel} · ${number(row.warning)} ${this.strings.warningLabel}`;
    this.tip.replaceChildren(heading, status, counts);
    this.tip.hidden = false;
    const x = parseFloat(region.label.style.left) || 0, y = parseFloat(region.label.style.top) || 0;
    this.tip.style.left = `${THREE.MathUtils.clamp(x + 14, 8, Math.max(8, this.stage.clientWidth - this.tip.offsetWidth - 8))}px`;
    this.tip.style.top = `${THREE.MathUtils.clamp(y + 20, 8, Math.max(8, this.stage.clientHeight - this.tip.offsetHeight - 8))}px`;
  }

  hideTip() { this.tip.hidden = true; }

  dispose() {
    this.detach();
    this.themeObserver?.disconnect();
    this.controls?.dispose();
    const materials = new Set();
    this.scene.traverse(object => {
      object.geometry?.dispose();
      if (object.material) (Array.isArray(object.material) ? object.material : [object.material]).forEach(material => materials.add(material));
    });
    materials.forEach(material => material.dispose());
    this.renderer.dispose();
  }
}

/* ---- page wiring ---- */
if (overview) {
  let relief = null, mode = storedView();
  const toggles = () => [...overview.querySelectorAll('[data-lm-view]')];
  const root = () => overview.querySelector('[data-leadership]');
  const paint = () => toggles().forEach(button => button.setAttribute('aria-pressed', String(button.dataset.lmView === mode)));
  const apply = () => {
    const current = root();
    if (!current || !relief) return;
    if (mode === '3d') relief.attach(current); else relief.detach();
    paint();
  };
  const hideToggles = () => toggles().forEach(button => { button.closest('.lm-view')?.setAttribute('hidden', ''); });
  const wire = () => {
    const current = root();
    if (!current) return;
    if (!relief) { hideToggles(); return; }
    if (current.dataset.lm3Wired) return;
    current.dataset.lm3Wired = 'true';
    toggles().forEach(button => button.addEventListener('click', () => { mode = button.dataset.lmView === '2d' ? '2d' : '3d'; rememberView(mode); apply(); }));
    // Wait for leadership-map.js to finish building the SVG before mirroring it.
    const ready = () => current.dataset.lmMounted === 'ready';
    if (ready()) apply();
    else {
      const watch = new MutationObserver(() => { if (ready()) { watch.disconnect(); apply(); } else if (current.dataset.lmMounted === 'failed') { watch.disconnect(); hideToggles(); } });
      watch.observe(current, { attributes: true, attributeFilter: ['data-lm-mounted'] });
    }
  };
  if (webglAvailable()) {
    try {
      const response = await fetch('/static/data/uz_regions.json', { credentials: 'same-origin' });
      if (!response.ok) throw new Error('Map geometry unavailable');
      relief = new Relief(await response.json());
      relief.onFailure = () => { relief = null; hideToggles(); };
    } catch (error) {
      relief?.dispose();
      relief = null;
      console.warn('Relief map unavailable; the flat map stays in place.', error.message);
    }
  }
  wire();
  document.body.addEventListener('htmx:beforeSwap', event => {
    if (event.detail.target?.id === 'executive-overview') relief?.detach();
  });
  document.body.addEventListener('htmx:afterSettle', event => {
    if (event.detail.target?.id === 'executive-overview' || event.detail.elt?.id === 'executive-overview') wire();
  });
  window.addEventListener('pagehide', event => { if (!event.persisted) relief?.dispose(); });
}
