# Vendored OSM vector tile decoder

Downloaded 2026-09-14 from pinned npm package bundles provided by esm.sh.
These browser ES modules contain their runtime dependencies and make no network
requests. No npm installation is needed at application runtime.

| Local file | Package | Bundle source | License |
| --- | --- | --- | --- |
| `pbf.js` | `pbf@4.0.2` | <https://esm.sh/pbf@4.0.2/es2022/pbf.bundle.mjs> | BSD-3-Clause, `LICENSE.pbf` |
| `vector-tile.js` | `@mapbox/vector-tile@2.0.5` | <https://esm.sh/@mapbox/vector-tile@2.0.5/es2022/vector-tile.bundle.mjs> | BSD-3-Clause, `LICENSE.vector-tile` |

The vector tile bundle also includes `@mapbox/point-geometry@1.1.0` (ISC,
`LICENSE.point-geometry`). Its code is identified in the upstream bundle source
map; 1.1.0 is the published version satisfying the tile package's `~1.1.0`
dependency. Development-only/type-only package dependencies are not shipped.

Original license files:

- <https://unpkg.com/pbf@4.0.2/LICENSE>
- <https://unpkg.com/@mapbox/vector-tile@2.0.5/LICENSE.txt>
- <https://unpkg.com/@mapbox/point-geometry@1.1.0/LICENSE>

Upstream repositories:

- <https://github.com/mapbox/pbf>
- <https://github.com/mapbox/vector-tile-js>
- <https://github.com/mapbox/point-geometry>

The only local bundle modification is removal of the final `sourceMappingURL`
comment, since source maps are not served with these files. Bundle code is
unchanged.

## API

```js
import Pbf from './pbf.js';
import { VectorTile } from './vector-tile.js';

const tile = new VectorTile(new Pbf(new Uint8Array(arrayBuffer)));
const layer = tile.layers.streets;
if (layer) {
  for (let i = 0; i < layer.length; i += 1) {
    const feature = layer.feature(i);
    // feature.type: 1 = point, 2 = line, 3 = polygon.
    // Geometry uses tile-local coordinates; divide by layer.extent to scale.
    const paths = feature.loadGeometry();
    const properties = feature.properties;
  }
}
```

`pbf.js` exports default `Pbf`. `vector-tile.js` exports `VectorTile`,
`VectorTileFeature`, `VectorTileLayer`, and `classifyRings`. A module import check
and a synthetic MVT round trip verified property decoding, point coordinates,
and `feature.toGeoJSON(x, y, z)`. Neither bundle contains imports or remote module
references.

SHA-256 after source map comment removal:

```text
D23375E6F05D4D1EAB18BF68171A4ACAB0AE1300AB758B6E75CC1B15C5C88EEC  pbf.js
AB7B991AD433037D09050329F564FE80A4D282242E11AB0DF949601002003C3C  vector-tile.js
```

These are decoding libraries, not map data. OpenStreetMap attribution and tile
usage requirements apply separately to the map data rendered by the application.
