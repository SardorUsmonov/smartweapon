import * as THREE from 'three';
import { SVGLoader } from '../vendor/three/SVGLoader.js';
import { OrbitControls } from '../vendor/three/OrbitControls.js';

// One renderer survives the live HTML refreshes; the server-rendered SVG remains
// the authority for each region's current status, accessible name and link.
const overview = document.getElementById('executive-overview');
const DEPTH = 22; // Visual extrusion only: equal height is not a data measure.
let view = null;

class SituationMap {
  constructor(geo) {
    this.geo = geo;
    this.regions = new Map();
    this.pickable = [];
    this.surface = document.createElement('div');
    this.surface.className = 'map3d-surface';
    this.labels = document.createElement('div');
    this.labels.className = 'map3d-labels';
    this.leaders = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    this.leaders.classList.add('map3d-leaders');
    this.leaders.setAttribute('aria-hidden', 'true');
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.surface.append(this.renderer.domElement, this.leaders, this.labels);
    const canvas = this.renderer.domElement;
    canvas.setAttribute('aria-hidden', 'true');

    this.scene = new THREE.Scene();
    this.camera = new THREE.OrthographicCamera(-450, 450, 300, -300, 1, 3000);
    this.camera.up.set(0, 0, 1);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = false;
    this.controls.enablePan = false;
    this.controls.minZoom = .8;
    this.controls.maxZoom = 4;
    this.controls.minPolarAngle = .015;
    this.controls.maxPolarAngle = Math.PI * .34;
    this.controls.rotateSpeed = .45;
    this.controls.zoomSpeed = .7;
    this.mode = 'tilt';
    this.reset();

    this.scene.add(new THREE.AmbientLight(0xffffff, 1.4));
    const key = new THREE.DirectionalLight(0xffffff, 2.5);
    key.position.set(-280, 350, 850);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    Object.assign(key.shadow.camera, { left: -650, right: 650, top: 600, bottom: -600, near: 1, far: 1800 });
    key.shadow.normalBias = 1;
    key.shadow.bias = -.0002;
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0x93bfe2, .7);
    fill.position.set(450, -250, 400);
    this.scene.add(fill);

    this.floor = new THREE.Mesh(new THREE.PlaneGeometry(1200, 950), new THREE.ShadowMaterial({ opacity: .2 }));
    this.floor.position.z = -2;
    this.floor.receiveShadow = true;
    this.scene.add(this.floor);
    this.grid = new THREE.GridHelper(1100, 22, 0x60778b, 0x60778b);
    this.grid.rotation.x = Math.PI / 2;
    this.grid.position.z = -1;
    this.grid.material.transparent = true;
    this.grid.material.opacity = .035;
    this.scene.add(this.grid);

    const loader = new SVGLoader();
    for (const [code, region] of Object.entries(geo.regions)) {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      const path = document.createElementNS(svg.namespaceURI, 'path');
      path.setAttribute('d', region.d);
      svg.append(path);
      const shapes = loader.parse(new XMLSerializer().serializeToString(svg)).paths.flatMap(SVGLoader.createShapes);
      const geometry = new THREE.ExtrudeGeometry(shapes, { depth: DEPTH, bevelEnabled: false, steps: 1, curveSegments: 6 });
      geometry.rotateX(Math.PI);
      geometry.translate(-geo.w / 2, geo.h / 2, DEPTH);
      const face = new THREE.MeshStandardMaterial({ roughness: .52, metalness: .12 });
      const side = new THREE.MeshStandardMaterial({ roughness: .7, metalness: .18 });
      const mesh = new THREE.Mesh(geometry, [face, side]);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.userData.code = code;
      const group = new THREE.Group();
      group.add(mesh);
      const edges = new THREE.LineBasicMaterial({ transparent: true, opacity: .65 });
      for (const shape of shapes) {
        for (const outline of [shape, ...shape.holes]) {
          const points = outline.getPoints(6).map(p => new THREE.Vector3(p.x - geo.w / 2, geo.h / 2 - p.y, DEPTH + .2));
          group.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points), edges));
        }
      }
      const anchor = new THREE.Vector3(region.cx - geo.w / 2, geo.h / 2 - region.cy, DEPTH + 4);
      const pin = new THREE.Mesh(new THREE.SphereGeometry(3.4, 12, 8), new THREE.MeshStandardMaterial({ roughness: .3, metalness: .12 }));
      pin.position.copy(anchor);
      pin.position.y += code === 'UZ-TK' ? 0 : 13;
      pin.position.z += 2;
      pin.castShadow = true;
      group.add(pin);
      this.scene.add(group);
      this.pickable.push(mesh);
      const label = document.createElement('a');
      label.className = 'map3d-label';
      label.dataset.code = code;
      label.textContent = region.short;
      label.addEventListener('dragstart', event => event.preventDefault());
      label.addEventListener('focus', () => this.highlight(code, true));
      label.addEventListener('blur', () => this.highlight(null));
      label.addEventListener('pointerenter', () => this.highlight(code, true));
      label.addEventListener('pointerleave', () => { if (document.activeElement !== label) this.highlight(null); });
      label.addEventListener('keydown', event => { if (event.key === 'Escape') this.highlight(null); });
      this.labels.append(label);
      const leader = document.createElementNS(this.leaders.namespaceURI, 'line');
      this.leaders.append(leader);
      this.regions.set(code, { group, face, side, edges, pin, anchor, label, leader, status: 'nodata', href: null, title: '' });
    }

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.controls.addEventListener('change', () => { this.hideTip(); this.draw(); });
    canvas.addEventListener('pointerdown', event => {
      this.drag = { x: event.clientX, y: event.clientY, id: event.pointerId, moved: false };
      this.highlight(null);
    });
    canvas.addEventListener('pointermove', event => {
      if (this.drag) {
        this.drag.moved ||= Math.hypot(event.clientX - this.drag.x, event.clientY - this.drag.y) > 5;
        if (this.drag.moved) this.surface.classList.add('is-dragging');
        return;
      }
      this.highlight(this.pick(event), true);
    });
    canvas.addEventListener('pointerup', event => {
      const drag = this.drag;
      this.drag = null;
      this.surface.classList.remove('is-dragging');
      if (drag && drag.id === event.pointerId && !drag.moved) {
        const region = this.regions.get(this.pick(event));
        if (region?.href) window.location.assign(region.href);
      }
    });
    canvas.addEventListener('pointercancel', () => { this.drag = null; this.surface.classList.remove('is-dragging'); });
    canvas.addEventListener('pointerleave', () => { if (!this.drag) this.highlight(null); });
    canvas.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      this.failed = true;
      this.surface.remove();
      this.wrap?.classList.remove('is-3d');
    });
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.themeObserver = new MutationObserver(() => this.setPalette());
    this.themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  }

  mount(wrap) {
    if (this.failed || !wrap) return;
    this.wrap = wrap;
    this.tip = wrap.querySelector('.map-tip');
    this.labels.setAttribute('aria-label', wrap.dataset.mapLabel);
    this.labels.setAttribute('role', 'group');
    this.binding?.abort();
    this.binding = new AbortController();
    for (const [code, region] of this.regions) {
      const source = wrap.querySelector(`.uzmap-regions > .uzmap-region[data-code="${code}"]`);
      region.status = ['critical', 'warning', 'good'].find(status => source?.classList.contains(`st-${status}`)) || 'nodata';
      const href = source?.getAttribute('href');
      region.href = href && /^\/hudud\/\d+$/.test(href) ? href : null;
      region.title = source?.getAttribute('aria-label') || source?.querySelector('title')?.textContent || this.geo.regions[code].name;
      region.label.setAttribute('aria-label', region.title);
      if (region.href) {
        region.label.href = region.href;
        region.label.removeAttribute('aria-disabled');
        region.label.removeAttribute('tabindex');
      } else {
        region.label.removeAttribute('href');
        region.label.setAttribute('aria-disabled', 'true');
        region.label.setAttribute('tabindex', '-1');
      }
      region.pin.visible = region.status !== 'nodata';
    }
    wrap.append(this.surface);
    wrap.classList.add('is-3d');
    wrap.querySelectorAll('[data-map3d]').forEach(button => {
      button.addEventListener('click', () => {
        const action = button.dataset.map3d;
        this.highlight(null);
        if (action === 'in' || action === 'out') {
          this.camera.zoom = THREE.MathUtils.clamp(this.camera.zoom * (action === 'in' ? 1.25 : .8), .8, 4);
          this.camera.updateProjectionMatrix();
        } else {
          this.mode = action === 'top' ? 'top' : 'tilt';
          this.reset();
        }
        this.controls.update();
        this.syncButtons();
        this.draw();
      }, { signal: this.binding.signal });
    });
    this.resizeObserver.disconnect();
    this.resizeObserver.observe(wrap);
    this.setPalette();
    this.syncButtons();
    this.resize();
    if (this.restoreFocus) {
      this.regions.get(this.restoreFocus)?.label.focus({ preventScroll: true });
      this.restoreFocus = null;
    }
  }

  reset() {
    this.camera.position.set(...(this.mode === 'top' ? [0, -.1, 1100] : [100, -560, 1000]));
    this.controls.target.set(0, 0, 6);
    this.camera.zoom = 1;
    this.controls.enableRotate = this.mode !== 'top';
    this.camera.updateProjectionMatrix();
    this.controls.update();
  }

  syncButtons() {
    this.wrap?.querySelectorAll('[data-map3d="top"], [data-map3d="tilt"]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.map3d === this.mode));
    });
  }

  setPalette() {
    const dark = document.documentElement.dataset.theme === 'dark';
    const css = getComputedStyle(document.documentElement);
    const statusColor = { critical: css.getPropertyValue('--red').trim(), warning: css.getPropertyValue('--yellow').trim(), good: css.getPropertyValue('--green').trim() };
    for (const region of this.regions.values()) {
      region.face.color.set(region.status === 'nodata' ? (dark ? '#273744' : '#d6dfe3') : (dark ? '#12344f' : '#b8c1c6'));
      region.side.color.set(dark ? '#112b42' : '#6d8ca4');
      region.edges.color.set(dark ? '#b5a77d' : '#778d9b');
      region.pin.material.color.set(statusColor[region.status] || '#85929c');
    }
    this.floor.material.opacity = dark ? .38 : .18;
    this.grid.material.opacity = dark ? .065 : .035;
    this.draw();
  }

  resize() {
    if (!this.wrap?.isConnected || this.failed) return;
    const width = this.wrap.clientWidth, height = this.wrap.clientHeight;
    if (!width || !height) return;
    this.renderer.setSize(width, height, false);
    const aspect = width / height;
    const span = Math.max(this.geo.h * 1.13, this.geo.w * 1.13 / aspect);
    this.camera.left = -span * aspect / 2;
    this.camera.right = span * aspect / 2;
    this.camera.top = span / 2;
    this.camera.bottom = -span / 2;
    this.camera.updateProjectionMatrix();
    this.draw();
  }

  draw() {
    if (!this.wrap?.isConnected || this.failed) return;
    this.renderer.render(this.scene, this.camera);
    const width = this.wrap.clientWidth, height = this.wrap.clientHeight;
    const placed = [];
    // Offset dense eastern labels, then resolve collisions after projection.
    const offsets = { 'UZ-TK': [-18, -32], 'UZ-TO': [5, -8], 'UZ-NG': [16, -22], 'UZ-AN': [25, 1], 'UZ-FA': [12, 25], 'UZ-SI': [0, 20], 'UZ-JI': [-22, -6] };
    const order = [...Object.keys(offsets), ...[...this.regions.keys()].filter(code => !(code in offsets))];
    for (const code of order) {
      const region = this.regions.get(code);
      const position = region.anchor.clone();
      position.z += region.group.position.z;
      position.project(this.camera);
      const x = (position.x + 1) * width / 2;
      const y = (1 - position.y) * height / 2;
      const visible = Math.abs(position.x) <= 1 && Math.abs(position.y) <= 1;
      region.label.style.visibility = visible ? 'visible' : 'hidden';
      region.leader.style.display = visible ? '' : 'none';
      if (!visible) continue;
      const w = region.label.offsetWidth, h = region.label.offsetHeight;
      const preferred = offsets[code] || [0, 9];
      const candidates = [preferred, [0, 9]];
      for (const distance of [22, 40, 60, 80, 100]) {
        for (const [dx, dy] of [[0,-1], [0,1], [-1,0], [1,0], [-1,-1], [1,-1], [-1,1], [1,1]]) candidates.push([dx * distance, dy * distance]);
      }
      let best = null;
      for (const [dx, dy] of candidates) {
        const cx = THREE.MathUtils.clamp(x + dx, w / 2 + 5, width - w / 2 - 5);
        const cy = THREE.MathUtils.clamp(y + dy, 42 + h / 2, height - 63 - h / 2);
        const rect = { left: cx - w / 2 - 2, right: cx + w / 2 + 2, top: cy - h / 2 - 2, bottom: cy + h / 2 + 2 };
        const overlaps = placed.filter(r => rect.left < r.right && rect.right > r.left && rect.top < r.bottom && rect.bottom > r.top).length;
        const score = overlaps * 100000 + (cx - x - preferred[0]) ** 2 + (cy - y - preferred[1]) ** 2;
        if (!best || score < best.score) best = { cx, cy, rect, score };
        if (score === 0) break;
      }
      placed.push(best.rect);
      region.label.style.left = `${best.cx}px`;
      region.label.style.top = `${best.cy}px`;
      region.leader.setAttribute('x1', x);
      region.leader.setAttribute('y1', y);
      region.leader.setAttribute('x2', best.cx);
      region.leader.setAttribute('y2', best.cy);
      region.leader.style.opacity = Math.hypot(best.cx - x, best.cy - y) > 15 ? '.45' : '0';
    }
  }

  pick(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
    this.raycaster.setFromCamera(this.pointer, this.camera);
    return this.raycaster.intersectObjects(this.pickable, false)[0]?.object.userData.code || null;
  }

  highlight(code, tooltip = false) {
    if (this.activeCode !== code) {
      for (const [key, region] of this.regions) {
        const active = key === code && Boolean(region.href);
        region.group.position.z = active ? 5 : 0;
        region.face.emissive.set(active ? '#22313c' : '#000000');
        region.face.emissiveIntensity = .25;
        region.label.classList.toggle('is-active', active);
      }
      this.activeCode = code;
      this.draw();
    }
    if (!tooltip || !code || !this.regions.get(code)?.href) return this.hideTip();
    const region = this.regions.get(code);
    if (!this.tip) return;
    const [name, ...details] = region.title.split(':');
    const heading = document.createElement('b');
    heading.textContent = name;
    const body = document.createElement('span');
    body.textContent = details.join(':').trim();
    this.tip.replaceChildren(heading, body);
    this.tip.setAttribute('role', 'tooltip');
    this.tip.hidden = false;
    const x = parseFloat(region.label.style.left), y = parseFloat(region.label.style.top);
    this.tip.style.left = `${THREE.MathUtils.clamp(x + 12, 8, Math.max(8, this.wrap.clientWidth - this.tip.offsetWidth - 8))}px`;
    this.tip.style.top = `${THREE.MathUtils.clamp(y + 18, 8, Math.max(8, this.wrap.clientHeight - this.tip.offsetHeight - 8))}px`;
  }

  hideTip() { if (this.tip) this.tip.hidden = true; }

  dispose() {
    this.binding?.abort();
    this.resizeObserver?.disconnect();
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

if (overview) {
  try {
    const response = await fetch('/static/data/uz_regions.json');
    if (!response.ok) throw new Error('Map geometry unavailable');
    view = new SituationMap(await response.json());
    view.mount(overview.querySelector('.executive-map'));
  } catch (error) {
    view?.dispose();
    view = null;
    console.warn('3D map unavailable; the geographic overview remains available.', error.message);
  }
  document.body.addEventListener('htmx:beforeSwap', event => {
    if (!view || view.failed || !event.detail.target?.contains(view.surface)) return;
    view.restoreFocus = document.activeElement?.closest('.map3d-label')?.dataset.code;
    view.highlight(null);
    view.surface.remove();
  });
  document.body.addEventListener('htmx:afterSwap', () => {
    const wrap = overview.querySelector('.executive-map');
    if (view && wrap && view.surface.parentElement !== wrap) view.mount(wrap);
  });
  // HTMX settles server attributes after afterSwap; restore the enhancement
  // class after that step as well, otherwise the fallback SVG becomes visible.
  document.body.addEventListener('htmx:afterSettle', () => {
    if (view && !view.failed && view.wrap?.contains(view.surface)) view.wrap.classList.add('is-3d');
  });
  window.addEventListener('pagehide', event => { if (!event.persisted) view?.dispose(); });
}
