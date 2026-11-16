"""One parameter set drives geometry, takeoff and stock layout. Dimensions in mm."""
from dataclasses import dataclass
from math import ceil, hypot


@dataclass(frozen=True)
class Part:
    name: str
    group: str
    ifc_class: str
    vertices: list
    faces: list
    blank: tuple | None = None


def prism(name, group, ifc_class, polygon, offset, blank=None):
    """Extrude a consistently wound polygon along its outward normal."""
    n = len(polygon)
    upper = [tuple(a + b for a, b in zip(p, offset)) for p in polygon]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return Part(name, group, ifc_class, polygon + upper, faces, blank)


def box(name, group, ifc_class, low, high, blank=None):
    x, y, z = low
    a, b, c = high
    return prism(name, group, ifc_class, [(x,y,z),(a,y,z),(a,b,z),(x,b,z)], (0,0,c-z), blank)


def segments(start, end, maximum):
    count = ceil((end - start) / maximum)
    return [(start + i*(end-start)/count, start + (i+1)*(end-start)/count) for i in range(count)]


def generate(d):
    w, l, f, h, g, t = [d[k] for k in
        ("width_mm", "depth_mm", "floor_level_mm", "wall_height_mm", "gable_rise_mm", "panel_thickness_mm")]
    limit_x, limit_y = [size - 2*d["board_edge_margin_mm"] for size in d["board_mm"]]
    skin, ribs, fits, base = [], [], [], []
    walls = {
        "south": (w, lambda u,v: (u,0,f+v), (0,-t,0)),
        "north": (w, lambda u,v: (w-u,l,f+v), (0,t,0)),
        "east": (l, lambda u,v: (w,u,f+v), (t,0,0)),
        "west": (l, lambda u,v: (0,l-u,f+v), (-t,0,0)),
    }
    for wall, (span, point, outward) in walls.items():
        openings = [o for o in d["openings"] if o["wall"] == wall]
        xs, zs = {0, span}, {0, h}
        for o in openings:
            if not (0 <= o["u"] < o["u"]+o["w"] <= span and 0 <= o["v"] < o["v"]+o["h"] <= h):
                raise ValueError(f"Opening outside {wall}")
            if any(p is not o and o["u"] < p["u"]+p["w"] and o["u"]+o["w"] > p["u"] and o["v"] < p["v"]+p["h"] and o["v"]+o["h"] > p["v"] for p in openings):
                raise ValueError(f"Overlapping openings on {wall}")
            xs.update([o["u"], o["u"]+o["w"]])
            zs.update([o["v"], o["v"]+o["h"]])
            if o["kind"] == "window":
                u, v, a, b = o["u"], o["v"], o["u"]+o["w"], o["v"]+o["h"]
                fits.append(prism(f"{wall}-glazing-{len(fits)+1:02d}", "glazing", "IfcWindow",
                                  [point(u,v),point(a,v),point(a,b),point(u,b)], tuple(x*0.3 for x in outward)))
        xx = sorted(xs); zz = sorted(zs)
        for u0,u1 in zip(xx,xx[1:]):
            for v0,v1 in zip(zz,zz[1:]):
                if any(o["u"] < (u0+u1)/2 < o["u"]+o["w"] and o["v"] < (v0+v1)/2 < o["v"]+o["h"] for o in openings):
                    continue
                for a,b in segments(u0,u1,limit_x):
                    for c,e in segments(v0,v1,limit_y):
                        skin.append(prism(f"{wall}-panel-{len(skin)+1:03d}", "wall_skin", "IfcWall",
                                          [point(a,c),point(b,c),point(b,e),point(a,e)], outward, (b-a,e-c)))
        if wall in ("south","north"):
            skin.append(prism(f"{wall}-gable", "gable", "IfcWall",
                              [point(0,h), point(w,h), point(w/2,h+g)], outward))
        for i,(u0,u1) in enumerate(segments(0,span,600),1):
            u = min(span-t, u0+1)
            cuts={0,h}
            for o in openings:
                if u < o["u"]+o["w"] and u+t > o["u"]:
                    cuts.update([o["v"],o["v"]+o["h"]])
            cc=sorted(cuts)
            for j,(a,b) in enumerate(zip(cc,cc[1:]),1):
                if any(u < o["u"]+o["w"] and u+t > o["u"] and o["v"] < (a+b)/2 < o["v"]+o["h"] for o in openings):
                    continue
                out = tuple(-x/t for x in outward)
                p = [point(u,a),point(u+t,a),point(u+t,b),point(u,b)]
                ribs.append(prism(f"{wall}-rib-{i:02d}-{j:02d}","illustrative_ribs","IfcMember",
                                  list(reversed(p)), tuple(125*x for x in out)))
    for a,b in segments(0,w,limit_x):
        for c,e in segments(0,l,limit_y):
            base.append(box(f"floor-{len(base)+1:02d}","floor_skin","IfcSlab",(a,c,f-t),(b,e,f),(b-a,e-c)))

    slope_length = hypot(w/2,g)
    for side in ("left","right"):
        for y0,y1 in segments(0,l,limit_x):
            for s0,s1 in segments(0,slope_length,limit_y):
                def point(s,y):
                    x = s*w/2/slope_length
                    return (x if side=="left" else w-x, y, f+h+s*g/slope_length)
                polygon=[point(s0,y0),point(s1,y0),point(s1,y1),point(s0,y1)]
                normal = ((-1 if side=="left" else 1)*t*g/slope_length,0,t*w/2/slope_length)
                skin.append(prism(f"{side}-roof-{len(skin)+1:03d}","roof_skin","IfcSlab",
                                  polygon if side=="left" else list(reversed(polygon)),normal,(y1-y0,s1-s0)))
    for ix,x in enumerate((180,w-180),1):
        for iy,y in enumerate((200,l/2,l-200),1):
            base.append(box(f"pier-{ix}-{iy}","foundation_placeholders","IfcFooting",
                            (x-110,y-110,0),(x+110,y+110,f-t)))
    door = next((o for o in d["openings"] if o["wall"]=="south" and o["kind"]=="door"),None)
    if door:
        for i in range(3):
            a,b=door["u"]-30,door["u"]+door["w"]+30
            base.append(box(f"step-{i+1}","access_placeholders","IfcStairFlight",
                            (a,-825+275*i,0),(b,-550+275*i,f*(i+1)/3)))
    return base+skin+ribs+fits
