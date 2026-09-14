import json, math
g = json.load(open('uzb_adm1.geojson', encoding='utf-8'))
NAMES = {
 'UZ-QR': ("Qoraqalpog'iston R.", "Qoraqalpog'iston Respublikasi"),
 'UZ-XO': ("Xorazm", "Xorazm viloyati"),
 'UZ-NW': ("Navoiy", "Navoiy viloyati"),
 'UZ-BU': ("Buxoro", "Buxoro viloyati"),
 'UZ-SA': ("Samarqand", "Samarqand viloyati"),
 'UZ-QA': ("Qashqadaryo", "Qashqadaryo viloyati"),
 'UZ-SU': ("Surxondaryo", "Surxondaryo viloyati"),
 'UZ-JI': ("Jizzax", "Jizzax viloyati"),
 'UZ-SI': ("Sirdaryo", "Sirdaryo viloyati"),
 'UZ-TO': ("Toshkent vil.", "Toshkent viloyati"),
 'UZ-TK': ("Toshkent sh.", "Toshkent shahri"),
 'UZ-NG': ("Namangan", "Namangan viloyati"),
 'UZ-AN': ("Andijon", "Andijon viloyati"),
 'UZ-FA': ("Farg'ona", "Farg'ona viloyati"),
}
# bounds
lons=[]; lats=[]
def rings(geom):
    if geom['type']=='Polygon':
        for r in geom['coordinates']: yield r
    else:
        for poly in geom['coordinates']:
            for r in poly: yield r
for f in g['features']:
    for r in rings(f['geometry']):
        for x,y in r: lons.append(x); lats.append(y)
lon0,lon1,lat0,lat1=min(lons),max(lons),min(lats),max(lats)
latm=(lat0+lat1)/2; k=math.cos(math.radians(latm))
W=800; PAD=8
sx=(W-2*PAD)/((lon1-lon0)*k)
H=int((lat1-lat0)*sx+2*PAD)
def P(lon,lat):
    return (PAD+(lon-lon0)*k*sx, PAD+(lat1-lat)*sx)
def dp(pts,eps):
    # Douglas-Peucker
    if len(pts)<3: return pts
    def d(p,a,b):
        (x,y),(x1,y1),(x2,y2)=p,a,b
        dx,dy=x2-x1,y2-y1
        if dx==dy==0: return math.hypot(x-x1,y-y1)
        t=max(0,min(1,((x-x1)*dx+(y-y1)*dy)/(dx*dx+dy*dy)))
        return math.hypot(x-(x1+t*dx),y-(y1+t*dy))
    idx=0; dmax=0
    for i in range(1,len(pts)-1):
        dd=d(pts[i],pts[0],pts[-1])
        if dd>dmax: idx=i; dmax=dd
    if dmax>eps:
        return dp(pts[:idx+1],eps)[:-1]+dp(pts[idx:],eps)
    return [pts[0],pts[-1]]
out={}; total=0
for f in g['features']:
    iso=f['properties']['shapeISO']
    paths=[]; cx=cy=n=0
    for r in rings(f['geometry']):
        pts=[P(x,y) for x,y in r]
        pts=dp(pts,0.9)
        if len(pts)<4: continue
        total+=len(pts)
        paths.append('M'+' L'.join('%.1f %.1f'%(x,y) for x,y in pts)+' Z')
        for x,y in pts: cx+=x; cy+=y; n+=1
    # centroid by polygon area of largest ring for better label placement
    best=None; bestA=0
    for r in rings(f['geometry']):
        pts=[P(x,y) for x,y in r]
        A=0; Cx=0; Cy=0
        for i in range(len(pts)-1):
            x1,y1=pts[i]; x2,y2=pts[i+1]; cr=x1*y2-x2*y1; A+=cr; Cx+=(x1+x2)*cr; Cy+=(y1+y2)*cr
        if abs(A)>bestA and A!=0: bestA=abs(A); best=(Cx/(3*A), Cy/(3*A))
    short,full=NAMES[iso]
    out[iso]={'short':short,'name':full,'d':' '.join(paths),'cx':round(best[0],1),'cy':round(best[1],1)}
json.dump({'w':W,'h':H,'regions':out},open('uz_regions.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d"><rect width="100%%" height="100%%" fill="#0f1720"/>'%(W,H,W,H)]
for iso,r in out.items():
    svg.append('<path d="%s" fill="#1f2d3a" stroke="#8aa0b4" stroke-width="1"/>'%r['d'])
    svg.append('<text x="%.1f" y="%.1f" font-size="12" fill="#e6edf3" text-anchor="middle" font-family="Arial">%s</text>'%(r['cx'],r['cy'],r['short']))
svg.append('</svg>')
open('uz_preview.svg','w',encoding='utf-8').write('\n'.join(svg))
print('viewBox', W, H, '| total points', total, '| bounds', round(lon0,2), round(lon1,2), round(lat0,2), round(lat1,2))
for iso,r in out.items(): print(iso, r['short'], 'centroid', r['cx'], r['cy'], 'pathlen', len(r['d']))
