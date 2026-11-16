"""Generate teaching drawings from model parameters, in consistent mm coordinates."""
from html import escape


def draw_overview(out, d):
    w, l, floor, h, rise = [d[k] for k in ("width_mm","depth_mm","floor_level_mm","wall_height_mm","gable_rise_mm")]
    scale = min(325/w, 325/l, 330/(floor+h+rise))
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="688" viewBox="0 0 1000 688">',
        '<style>text{font:14px sans-serif;fill:#243548}.major{font-size:28px;font-weight:700}.sub{font-size:17px;font-weight:700}.minor{font-size:12px}.line{stroke:#344454;stroke-width:1;fill:none}.dim{stroke:#66778c;stroke-width:1;fill:none}</style>',
        '<rect width="100%" height="100%" fill="#f5f5ef"/>',
    ]

    def text(x,y,s,kind=""):
        svg.append(f'<text x="{x}" y="{y}" class="{kind}">{escape(s)}</text>')

    def line(x,y,a,b,kind="line"):
        svg.append(f'<path d="M{x:.1f} {y:.1f} L{a:.1f} {b:.1f}" class="{kind}"/>')

    def rect(x,y,a,b,fill,stroke="#344454"):
        svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{a:.1f}" height="{b:.1f}" fill="{fill}" stroke="{stroke}"/>')

    def polygon(points,fill):
        xy=" ".join(f"{x:.1f},{y:.1f}" for x,y in points)
        svg.append(f'<polygon points="{xy}" stroke="#344454" fill="{fill}"/>')

    text(42,48,"Raised gable cabin | coordination drawings","major")
    text(42,74,"MIT 4.500 Lecture 7 interpretation · dimensions in mm · concept geometry")
    text(52,123,"01  PLAN","sub")
    text(526,123,"02  SOUTH ELEVATION","sub")

    x,y=87,501
    a,b=w*scale,l*scale
    rect(x,y-b,a,b,"#fafaf6")
    for o in d["openings"]:
        u, p=o["u"]*scale,o["w"]*scale
        pts={
            "south":(x+u,y,x+u+p,y),
            "north":(x+a-u-p,y-b,x+a-u,y-b),
            "east":(x+a,y-u,x+a,y-u-p),
            "west":(x,y-b+u,x,y-b+u+p)
        }[o["wall"]]
        svg.append(f'<path d="M{pts[0]:.1f},{pts[1]:.1f} L{pts[2]:.1f},{pts[3]:.1f}" stroke="#30827a" stroke-width="4"/>')
        if o["wall"]=="south" and o["kind"]=="door":
            for i in range(3):
                rect(x+u-30*scale,y+275*scale*i,p+60*scale,275*scale,"#e2e7e4")
    line(x+a/2,y-b,x+a/2,y)
    text(x+a/2+7,y-b+23,"ridge above","minor")
    line(x,y+91,x+a,y+91,"dim"); line(x,y+84,x,y+98,"dim"); line(x+a,y+84,x+a,y+98,"dim")
    text(x+a/2-15,y+110,str(w))
    line(x-20,y-b,x-20,y,"dim");line(x-26,y-b,x-14,y-b,"dim");line(x-26,y,x-14,y,"dim")
    text(x-55,y-b/2,str(l),"minor")
    text(52,624,"Teal edges mark modeled openings.","minor")

    x,z=546,512
    deck=z-floor*scale
    eave=deck-h*scale
    ridge=eave-rise*scale
    rect(x, eave, a, deck-eave,"#ead4ad")
    polygon([(x,eave),(x+a,eave),(x+a/2,ridge)],"#dcc099")
    for o in d["openings"]:
        if o["wall"]=="south":
            rect(x+o["u"]*scale,deck-(o["v"]+o["h"])*scale,o["w"]*scale,o["h"]*scale,
                 "#f5f5ef" if o["kind"]=="door" else "#badcda")
    for u in (180,w-180):
        rect(x+(u-110)*scale,deck,220*scale,z-deck,"#cad1cf")
    line(x-18,z,x+a+32,z)
    for v,name in ((deck,f"floor +{floor}"),(eave,f"eave +{floor+h}"),(ridge,f"ridge +{floor+h+rise}")):
        line(x+a+5,v,x+a+20,v,"dim")
        text(x+a+26,v+4,name,"minor")
    text(526,565,"03  JOINT STUDY","sub")
    polygon([(528,578),(620,578),(620,586),(642,586),(642,598),(620,598),(620,606),(528,606)],"#e6c590")
    rect(661,567,35,57,"#a8c6be")
    rect(671,585,14,14,"#f5f5ef")
    line(645,592,666,592,"dim")
    text(708,585,"Rib tab and panel slot, schematic","minor")
    text(708,605,"Joint sizing requires engineering review.","minor")
    text(42,661,"Outline dimensions are model assumptions. Foundation and access are placeholders.","minor")
    svg.append("</svg>")
    (out/"overview.svg").write_text("\n".join(svg),encoding="utf-8")
