/* The server-rendered region links remain the authority for scope and status. */
(() => {
  'use strict';
  let wrapper, surface, map, tiles, boundary, regions, focused, countryRings, clipPath;
  let loading = false, failed = false, followingCountry = true;
  const markers = new Map();
  const colors = { good: '#288367', warning: '#bb831a', critical: '#bb4149', nodata: '#7c8793' };
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let labelFrame, layoutRegionBoxes;

  function layoutLabels() {
    if (!map || !surface?.isConnected) return;
    const { x: width, y: height } = map.getSize();
    const items = [...markers.values()].map(marker => {
      const point = map.latLngToContainerPoint(marker.getLatLng());
      const element = marker.getElement();
      const visible = point.x >= 0 && point.x <= width && point.y >= 0 && point.y <= height;
      element.style.display = visible ? '' : 'none';
      marker.connector.setLatLngs([]);
      marker.anchor.setStyle({ opacity: visible ? 1 : 0, fillOpacity: visible ? 1 : 0 });
      return { id: element.dataset.regionCode, marker, element, point, visible, w: element.offsetWidth, h: element.offsetHeight };
    }).filter(item => item.visible);
    const boxes = layoutRegionBoxes(items.map(item => ({
      id: item.id, x: item.point.x, y: item.point.y, w: item.w, h: item.h
    })), width, height);
    for (const item of items) {
      const best = boxes.get(item.id);
      if (!best) continue;
      item.element.style.marginLeft = `${best.x - item.point.x}px`;
      item.element.style.marginTop = `${best.y - item.point.y}px`;
      const end = L.point(Math.max(best.x, Math.min(item.point.x, best.x + best.w)), Math.max(best.y, Math.min(item.point.y, best.y + best.h)));
      item.marker.connector.setLatLngs([item.marker.getLatLng(), map.containerPointToLatLng(end)]);
    }
  }
  function scheduleLabels() {
    if (labelFrame) cancelAnimationFrame(labelFrame);
    labelFrame = requestAnimationFrame(() => { labelFrame = null; layoutLabels(); });
  }

  function notice(kind) {
    if (!wrapper) return;
    const box = wrapper.querySelector('.osm-notice');
    box.hidden = !kind;
    box.querySelector('span').textContent = kind ? wrapper.dataset[kind] : '';
    box.querySelector('button').hidden = kind === 'mapLoading';
  }

  function fitCountry() {
    if (!map || !boundary) return;
    followingCountry = true;
    // getBoundsZoom clamps to minZoom; release the previous desktop fit on resize.
    map.setMinZoom(0);
    const fittedZoom = map.getBoundsZoom(boundary.getBounds(), false, L.point(48, 123));
    map.setMinZoom(Math.min(7, fittedZoom));
    map.fitBounds(boundary.getBounds(), {
      paddingTopLeft: [24, 58], paddingBottomRight: [24, 65],
      animate: false, maxZoom: 7
    });
    followingCountry = true;
  }

  function updateCountryClip() {
    if (!clipPath || !map || !countryRings) return;
    // The tile pane and these projected coordinates share the map-pane origin.
    // Clip rendered map pixels so panning cannot reveal surrounding countries.
    clipPath.setAttribute('d', countryRings.map(ring => ring.map(([lon, lat], i) => {
      const point = map.latLngToLayerPoint([lat, lon]);
      return `${i ? 'L' : 'M'}${point.x} ${point.y}`;
    }).join('') + 'Z').join(''));
    map.getPane('tilePane').style.visibility = '';
  }

  function updateTileState() {
    if (!surface) return;
    const images = [...surface.querySelectorAll('.leaflet-tile[data-vector-state]')];
    const broken = images.some(img => img.dataset.vectorState === 'error');
    const pending = images.some(img => img.dataset.vectorState === 'loading');
    failed = broken;
    notice(broken ? 'mapError' : pending ? 'mapLoading' : null);
  }

  function syncRegions() {
    const seen = new Set();
    wrapper.querySelectorAll('.uzmap-region[data-code]').forEach(source => {
      const code = source.dataset.code;
      const position = regions.find(region => region.code === code);
      if (!position) return;
      seen.add(code);
      let marker = markers.get(code);
      if (!marker) {
        const dot = document.createElement('span');
        dot.className = 'osm-region-dot';
        const name = document.createElement('span');
        name.className = 'osm-region-name';
        const labelBox = document.createElement('span');
        labelBox.className = 'osm-region-label';
        labelBox.append(dot, name);
        marker = L.marker([position.lat, position.lon], {
          icon: L.divIcon({ className: 'osm-region-icon', html: labelBox, iconSize: null }),
          keyboard: true, riseOnHover: true
        }).addTo(map);
        marker.connector = L.polyline([], { interactive: false, className: 'osm-region-connector', weight: .9, opacity: .8 }).addTo(map);
        marker.anchor = L.circleMarker([position.lat, position.lon], { interactive: false, className: 'osm-region-anchor', radius: 2.5, weight: 1, fillOpacity: 1 }).addTo(map);
        marker.bindTooltip(document.createElement('span'), { direction: 'top', offset: [0, -10], opacity: 1 });
        marker.on('click', () => { if (marker.regionHref) location.assign(marker.regionHref); });
        marker.getElement().addEventListener('keydown', event => {
          if (event.key === 'Enter' && marker.regionHref) {
            event.preventDefault();
            event.stopPropagation();
            location.assign(marker.regionHref);
          }
        });
        markers.set(code, marker);
      }
      const state = Object.keys(colors).find(key => source.classList.contains('st-' + key)) || 'nodata';
      const translated = [...wrapper.querySelectorAll('.osm-region-data [data-code]')].find(item => item.dataset.code === code);
      const label = translated?.dataset.label || source.getAttribute('aria-label') || source.dataset.name || position.name;
      const rawHref = source.getAttribute('href');
      marker.regionHref = rawHref && /^\/hudud\/\d+$/.test(rawHref) ? rawHref : null;
      const element = marker.getElement();
      element.dataset.status = state;
      element.dataset.regionCode = code;
      element.querySelector('.osm-region-name').textContent = translated?.dataset.short || source.dataset.name || position.name;
      element.setAttribute('aria-label', label);
      element.setAttribute('role', marker.regionHref ? 'link' : 'img');
      element.setAttribute('tabindex', marker.regionHref ? '0' : '-1');
      const tip = document.createElement('span');
      tip.className = 'osm-region-tip';
      const heading = document.createElement('b');
      const stats = document.createElement('small');
      const divider = label.indexOf(':');
      heading.textContent = divider < 0 ? label : label.slice(0, divider);
      stats.textContent = divider < 0 ? '' : label.slice(divider + 1).trim();
      tip.append(heading, stats);
      marker.setTooltipContent(tip);
    });
    markers.forEach((marker, code) => { if (!seen.has(code)) { marker.connector.remove(); marker.anchor.remove(); marker.remove(); markers.delete(code); } });
    scheduleLabels();
  }

  function attach() {
    const current = document.getElementById('executive-map');
    if (!current || !map) return;
    wrapper = current;
    wrapper.classList.add('is-osm');
    wrapper.append(surface);
    surface.setAttribute('aria-label', wrapper.dataset.mapLabel);
    syncRegions();
    notice(failed ? 'mapError' : null);
    requestAnimationFrame(() => {
      map.invalidateSize({ pan: false });
      if (followingCountry) fitCountry();
      if (focused?.isConnected && document.activeElement === document.body) focused.focus({ preventScroll: true });
      focused = null;
    });
  }

  async function start() {
    wrapper = document.getElementById('executive-map');
    if (!wrapper || loading) return;
    if (map) { attach(); return; }
    if (!window.L) { notice('mapFallback'); return; }
    loading = true;
    notice('mapLoading');
    try {
      const getData = async path => {
        const response = await fetch(path, { signal: AbortSignal.timeout(15000) });
        if (!response.ok) throw new Error('Map data unavailable');
        return response.json();
      };
      const [country, positions, vectorModule, labelModule] = await Promise.all([
        getData('/static/data/uzbekistan-osm.geojson'), getData('/static/data/uz-regions-osm.json'),
        import('./osm-vector-layer.js?v=2'), import('./osm-label-layout.js?v=1')
      ]);
      regions = positions;
      layoutRegionBoxes = labelModule.layoutRegionBoxes;
      wrapper = document.getElementById('executive-map');
      if (!wrapper) return;
      surface = document.createElement('div');
      surface.className = 'osm-surface';
      surface.setAttribute('role', 'region');
      surface.addEventListener('keydown', event => {
        if (event.target === surface && event.key.startsWith('Arrow')) followingCountry = false;
      });
      wrapper.append(surface);
      map = L.map(surface, {
        zoomControl: false, minZoom: 4, maxZoom: 18, zoomSnap: .25, zoomDelta: 1,
        scrollWheelZoom: false, zoomAnimation: false,
        fadeAnimation: !reduceMotion, markerZoomAnimation: false,
        maxBoundsViscosity: 1
      });
      const svgNS = 'http://www.w3.org/2000/svg';
      const clipSvg = document.createElementNS(svgNS, 'svg');
      clipSvg.classList.add('osm-clip-defs');
      clipSvg.setAttribute('width', '0');
      clipSvg.setAttribute('height', '0');
      clipSvg.setAttribute('aria-hidden', 'true');
      const defs = document.createElementNS(svgNS, 'defs');
      const clip = document.createElementNS(svgNS, 'clipPath');
      clip.id = 'osm-country-clip';
      clip.setAttribute('clipPathUnits', 'userSpaceOnUse');
      clipPath = document.createElementNS(svgNS, 'path');
      clipPath.setAttribute('clip-rule', 'evenodd');
      clip.append(clipPath);
      defs.append(clip);
      clipSvg.append(defs);
      surface.append(clipSvg);
      map.getPane('tilePane').style.clipPath = 'url(#osm-country-clip)';
      map.getPane('tilePane').style.visibility = 'hidden';
      map.attributionControl.setPrefix(false);
      L.control.zoom({ position: 'topright', zoomInTitle: wrapper.dataset.mapIn, zoomOutTitle: wrapper.dataset.mapOut }).addTo(map);
      L.control.scale({ imperial: false, maxWidth: 80 }).addTo(map);
      tiles = vectorModule.createOsmVectorLayer(L, surface);
      tiles.on('tileerror load tileload', updateTileState);
      tiles.on('tileunload', () => requestAnimationFrame(updateTileState));
      tiles.addTo(map);
      new MutationObserver(() => tiles.repaint()).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
      // Even-odd rings preserve exclaves and exclude foreign enclaves.
      const rings = [[[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]]];
      for (const feature of country.features) {
        const polygons = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates;
        for (const polygon of polygons) rings.push(...polygon);
      }
      countryRings = rings.slice(1);
      L.geoJSON({ type: 'Feature', geometry: { type: 'Polygon', coordinates: rings } }, {
        interactive: false, style: { stroke: false, fillOpacity: 1, fillRule: 'evenodd', className: 'osm-country-mask' }
      }).addTo(map);
      boundary = L.geoJSON(country, {
        interactive: false, style: { weight: 1.8, opacity: 1, fillOpacity: .08, smoothFactor: 0, className: 'osm-country-boundary' }
      }).addTo(map);
      map.setMaxBounds(boundary.getBounds().pad(.08));
      map.on('viewreset zoom zoomend moveend resize', updateCountryClip);
      map.on('zoom move resize', scheduleLabels);
      document.fonts?.ready.then(scheduleLabels);
      map.on('dragstart', () => { followingCountry = false; });
      map.on('zoomstart', () => { followingCountry = false; });
      fitCountry();
      updateCountryClip();
      attach();
      followingCountry = true;
      new ResizeObserver(() => {
        if (!surface.isConnected) return;
        const fit = followingCountry;
        map.invalidateSize({ pan: false });
        if (fit) { fitCountry(); followingCountry = true; }
      }).observe(surface);
    } catch (error) {
      if (map) map.remove();
      map = null;
      surface?.remove();
      markers.clear();
      wrapper?.classList.remove('is-osm');
      notice('mapFallback');
      console.warn('OpenStreetMap could not initialize:', error.message);
    } finally { loading = false; }
  }

  document.addEventListener('click', event => {
    if (event.target.closest('[data-osm-reset]')) { fitCountry(); followingCountry = true; }
    if (event.target.closest('[data-osm-retry]')) {
      if (tiles && map) { failed = false; notice('mapLoading'); tiles.redraw(); }
      else start();
    }
  });
  document.addEventListener('htmx:beforeSwap', event => {
    if (surface && event.detail.shouldSwap !== false && event.detail.target?.contains(surface)) {
      focused = surface.contains(document.activeElement) ? document.activeElement : null;
      surface.remove();
    }
  });
  document.addEventListener('htmx:afterSwap', () => {
    if (surface && !surface.isConnected) attach();
  });
  document.addEventListener('htmx:afterSettle', () => {
    // HTMX restores server attributes after afterSwap, including the wrapper class.
    if (surface?.isConnected) wrapper.classList.add('is-osm');
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
