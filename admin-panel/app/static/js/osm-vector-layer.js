import Pbf from '../vendor/osm-vector/pbf.js';
import { VectorTile } from '../vendor/osm-vector/vector-tile.js';

// Draw OSM geometry without baked text. Dashboard labels remain separate and whole.
export function createOsmVectorLayer(L, root) {
  const canvases = new Set();
  const theme = () => {
    const style = getComputedStyle(root);
    return Object.fromEntries(['land', 'park', 'water', 'road', 'minor', 'division', 'building'].map(key =>
      [key, style.getPropertyValue('--osm-vector-' + key).trim()]));
  };
  function decode(buffer) {
    const tile = new VectorTile(new Pbf(new Uint8Array(buffer)));
    const shapes = [];
    for (const name of ['land', 'water_polygons', 'ocean', 'water_lines', 'buildings', 'boundaries', 'streets']) {
      const layer = tile.layers[name];
      if (!layer) continue;
      for (let i = 0; i < layer.length; i++) {
        const feature = layer.feature(i);
        const props = feature.properties;
        if (name === 'boundaries' && Number(props.admin_level) !== 4) continue;
        let color = 'park', width = .65;
        if (name.startsWith('water') || name === 'ocean') color = 'water';
        else if (name === 'buildings') color = 'building';
        else if (name === 'boundaries') { color = 'division'; width = .85; }
        else if (name === 'streets') {
          const major = ['motorway', 'trunk', 'primary', 'secondary'].includes(props.kind);
          color = major ? 'road' : 'minor'; width = major ? 1.3 : .65;
        }
        if (feature.type === 1) continue;
        shapes.push({
          color, width, polygon: feature.type === 3,
          paths: feature.loadGeometry().map(ring => ring.map(point => [point.x * 256 / layer.extent, point.y * 256 / layer.extent]))
        });
      }
    }
    return shapes;
  }
  function paint(canvas) {
    const palette = theme();
    const ctx = canvas.getContext('2d');
    const ratio = canvas.width / 256;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.fillStyle = palette.land;
    ctx.fillRect(0, 0, 256, 256);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    for (const shape of canvas.vectorShapes || []) {
      ctx.beginPath();
      for (const ring of shape.paths) {
        ring.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
        if (shape.polygon) ctx.closePath();
      }
      if (shape.polygon) { ctx.fillStyle = palette[shape.color]; ctx.fill('evenodd'); }
      else {
        ctx.strokeStyle = palette[shape.color]; ctx.lineWidth = shape.width;
        ctx.setLineDash(shape.color === 'division' ? [3, 3] : []); ctx.stroke();
      }
    }
  }
  const Layer = L.GridLayer.extend({
    createTile(coords, done) {
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 256 * Math.min(devicePixelRatio || 1, 2);
      canvas.dataset.vectorState = 'loading';
      canvas.setAttribute('aria-hidden', 'true');
      const controller = new AbortController();
      canvas.cancelRequest = () => controller.abort();
      canvases.add(canvas);
      paint(canvas);
      const timeout = setTimeout(() => controller.abort(), 15000);
      fetch(`https://vector.openstreetmap.org/shortbread_v1/${coords.z}/${coords.x}/${coords.y}.mvt`, {
        signal: controller.signal, referrerPolicy: 'strict-origin-when-cross-origin', credentials: 'omit'
      }).then(response => {
        if (!response.ok) throw new Error(`OSM vector tile: ${response.status}`);
        return response.arrayBuffer();
      }).then(buffer => {
        if (!canvases.has(canvas)) return;
        canvas.vectorShapes = decode(buffer);
        canvas.dataset.vectorState = 'ready';
        paint(canvas); done(null, canvas);
      }).catch(error => {
        if (!canvases.has(canvas)) return;
        canvas.dataset.vectorState = 'error'; done(error, canvas);
      }).finally(() => clearTimeout(timeout));
      return canvas;
    }
  });
  const layer = new Layer({
    minNativeZoom: 6, maxNativeZoom: 14, maxZoom: 18, keepBuffer: 0, updateWhenIdle: true,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>'
  });
  layer.on('tileunload', ({ tile }) => { canvases.delete(tile); tile.cancelRequest?.(); });
  layer.repaint = () => canvases.forEach(paint);
  return layer;
}
