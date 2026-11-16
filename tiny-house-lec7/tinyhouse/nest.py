"""Rectangular, single-stock sheet packing with an explicit spacing envelope."""
from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def overlaps(self, b):
        return self.x < b.x+b.w and b.x < self.x+self.w and self.y < b.y+b.h and b.y < self.y+self.h

    def contains(self, b):
        return self.x <= b.x and self.y <= b.y and self.x+self.w >= b.x+b.w and self.y+self.h >= b.y+b.h


def split(r, p):
    if not r.overlaps(p):
        return [r]
    pieces = [
        Rect(r.x,r.y,p.x-r.x,r.h), Rect(p.x+p.w,r.y,r.x+r.w-p.x-p.w,r.h),
        Rect(r.x,r.y,r.w,p.y-r.y), Rect(r.x,p.y+p.h,r.w,r.y+r.h-p.y-p.h),
    ]
    return [s for s in pieces if s.w > 1e-7 and s.h > 1e-7]


def pack(items, width, height, margin, gap, key):
    stock = Rect(margin,margin,width-2*margin+gap,height-2*margin+gap)
    if min(stock.w,stock.h) <= gap or margin < 0 or gap < 0:
        raise ValueError("Invalid stock or gap")
    sheets = []
    for name, w, h in sorted(items,key=key):
        rw,rh = w+gap,h+gap
        if w <= 0 or h <= 0 or rw>stock.w+1e-7 or rh>stock.h+1e-7:
            raise ValueError(f"{name} does not fit the declared stock orientation")
        candidates = [(min(r.w-rw,r.h-rh),max(r.w-rw,r.h-rh),i,r.y,r.x)
                      for i,(_, free) in enumerate(sheets) for r in free
                      if r.w+1e-7>=rw and r.h+1e-7>=rh]
        if candidates:
            _,_,i,y,x = min(candidates)
        else:
            i,x,y=len(sheets),stock.x,stock.y
            sheets.append(([],[stock]))
        placed,free = sheets[i]
        used=Rect(x,y,rw,rh)
        remain=list(dict.fromkeys(p for r in free for p in split(r,used)))
        free[:]=[r for r in remain if not any(s!=r and s.contains(r) for s in remain)]
        placed.append({"name":name,"x":x,"y":y,"w":w,"h":h})
    return [placed for placed,_ in sheets]


def optimize(parts, design):
    items=[(p.name,*p.blank) for p in parts if p.blank is not None]
    w,h=design["board_mm"]
    m,g=design["board_edge_margin_mm"],design["part_gap_mm"]
    area=sum(x*y for _,x,y in items)
    orders = {
        "as_modelled":lambda p: 0,
        "area_desc":lambda p: -p[1]*p[2],
        "height_desc":lambda p: (-p[2],-p[1]),
        "width_desc":lambda p: (-p[1],-p[2]),
    }
    runs={name:pack(items,w,h,m,g,key) for name,key in orders.items()}
    winner=min(runs,key=lambda x:len(runs[x]))
    sheets=runs[winner]
    return {"order":winner,"sheets":sheets,"pieces":len(items),
            "trial_counts":{k:len(v) for k,v in runs.items()},
            "area_bound":ceil(area/((w-2*m)*(h-2*m))),
            "net_area_m2":area/1e6,"stock_utilization":area/(len(sheets)*w*h)}
