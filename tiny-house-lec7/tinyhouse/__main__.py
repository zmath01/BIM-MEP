"""Build a review model, material takeoff and nest; uses Python 3.10+."""
import argparse
import csv
import json
from dataclasses import asdict
from html import escape
from math import hypot
from pathlib import Path

from .geometry import generate
from .drawings import draw_overview
from .nest import optimize

ROOT=Path(__file__).resolve().parents[1]


def write_csv(filename, header, rows):
    with filename.open("w",newline="",encoding="utf-8") as file:
        writer=csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def draw_nest(out, design, result):
    w,h=design["board_mm"]
    scale=0.235
    sw,sh=w*scale,h*scale
    dx,dy=sw+34,sh+49
    groups=[]
    for i,sheet in enumerate(result["sheets"]):
        x,y=24+i%2*dx,92+i//2*dy
        groups.append(f'<g transform="translate({x:.2f} {y:.2f})"><text x="0" y="-10">SHEET {i+1:02d}</text><rect width="{sw}" height="{sh}" rx="2" fill="#fff" stroke="#35465a"/>')
        for p in sheet:
            a,b=p["x"]*scale,p["y"]*scale
            c,e=p["w"]*scale,p["h"]*scale
            color="#c1daca" if "roof" in p["name"] else "#dbe7f1" if p["name"].startswith("floor") else "#eddbbc"
            group=f'<rect x="{a:.2f}" y="{b:.2f}" width="{c:.2f}" height="{e:.2f}" fill="{color}" stroke="#35465a" stroke-width="0.55"><title>{escape(p["name"])}</title></rect>'
            groups.append(group)
            if c>50 and e>14:
                label=p["name"].replace("-panel","").upper()
                groups.append(f'<text class="tag" x="{a+3:.2f}" y="{b+12:.2f}">{escape(label)}</text>')
        groups.append("</g>")
    width=round(24+dx*2)
    height=round(92+(len(result["sheets"])+1)//2*dy)
    (out/"stock-layout.svg").write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>text{{font:13px sans-serif;fill:#213248}}.tag{{font-size:9px}}.heading{{font-size:24px;font-weight:700}}</style>
<rect width="100%" height="100%" fill="#f5f5f0"/>
<text x="24" y="34" class="heading">Lecture 7 cabin | plywood stock layout</text>
<text x="24" y="59">{w} × {h} mm · no rotation · review only · rectangular pieces</text>
{''.join(groups)}</svg>''',encoding="utf-8")


def takeoff(d, result, parts):
    w,l,f,h,g,t=[d[k] for k in ("width_mm","depth_mm","floor_level_mm","wall_height_mm","gable_rise_mm","panel_thickness_mm")]
    a=lambda x:round(x/1e6,3)
    openings=sum(o["w"]*o["h"] for o in d["openings"])
    wall=a(2*(w+l)*h-openings)
    gables=a(w*g)
    deck=a(w*l)
    roof=a(2*l*hypot(w/2,g))
    window_area=a(sum(o["w"]*o["h"] for o in d["openings"] if o["kind"]=="window"))
    def row(layer, material, unit, quantity, scope):
        return (layer,material,unit,quantity,scope)
    return [
        row("Flat panel stock",f"Structural plywood candidate, {t} mm in study","sheet",len(result["sheets"]),"Optimized study stock for modeled rectangular skins only; final grade and thickness by design"),
        row("Wall skin","Plywood","m²",wall,"Rectangular wall panels, net of modeled openings; included in flat stock"),
        row("Gables","Plywood","m²",gables,"Both triangular gables; additional nonrectangular layout needed"),
        row("Floor deck","Plywood","m²",deck,"Included in flat stock; excludes finish and structural framing"),
        row("Roof deck","Plywood","m²",roof,"Included in flat stock; no eaves, laps or waste included"),
        row("Wall cavity","Illustrative plywood rib geometry (actual frame subject to structural design)","objects",sum(p.group=="illustrative_ribs" for p in parts),"Object count for visual review only; excludes framing stock, joints and load rating"),
        row("Weathering","Wall wrap, cavity battens, exterior cladding","m² net geometry",round(wall+gables,3),"Each wall layer starts from this net area; add laps, openings detailing and product allowances"),
        row("Roof weathering","Roof underlay, roofing, ridge and edge flashing","m² net geometry",roof,"Roof surface proxy; select approved system and detail eaves, drainage and laps"),
        row("Insulation","Floor, walls, roof or ceiling assembly","m² area proxy",round(deck+wall+gables+roof,3),"Total boundary-area proxy; calculate each assembly separately for local thermal and moisture requirements"),
        row("Glazing","Glazed window units","units",sum(o["kind"]=="window" for o in d["openings"]),f"Gross modeled opening area {window_area} m²; confirm actual rough openings"),
        row("Entry","Door and frame, seals and flashing","units",sum(o["kind"]=="door" for o in d["openings"]),"No door leaf modeled; accessibility and egress require review"),
        row("Water management","Gutters, downpipes, roof drainage","TBD","","Design to roof and site conditions"),
        row("Structure and fixing","Framing, straps, anchors, hold-downs and corrosion-compatible fasteners","TBD","","Connection and load-path design required"),
        row("Base and access","Foundation, moisture separation, access steps and guards","TBD","","Concept blocks shown; design for site, uplift and access"),
        row("MEP and interiors","Ventilation, lighting, wiring and plumbing as needed; lining and finishes","TBD","","Scope depends on intended use and services"),
    ]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design",type=Path,default=ROOT/"design.json")
    parser.add_argument("--out",type=Path,default=ROOT/"outputs")
    options=parser.parse_args()
    design=json.loads(options.design.read_text(encoding="utf-8"))
    out=options.out
    out.mkdir(parents=True,exist_ok=True)
    parts=generate(design)
    layout=optimize(parts,design)
    (out/"model.json").write_text(json.dumps({"unit":"mm","parts":[asdict(p) for p in parts]},separators=(",",":"))+"\n",encoding="utf-8")
    (out/"nesting.json").write_text(json.dumps(layout,indent=2)+"\n",encoding="utf-8")
    write_csv(out/"rectangular-parts.csv",["id","system","length_mm","width_mm","thickness_mm"],
              ((p.name,p.group,round(p.blank[0],3),round(p.blank[1],3),design["panel_thickness_mm"]) for p in parts if p.blank))
    write_csv(out/"materials.csv",["layer","material","unit","modeled_quantity","scope"],takeoff(design,layout,parts))
    draw_nest(out,design,layout)
    draw_overview(out,design)
    print(f'{len(parts)} model objects, {layout["pieces"]} rectangular pieces; {layout["trial_counts"]}')
    print(f'{len(layout["sheets"])} sheets; area lower bound {layout["area_bound"]}; utilization {layout["stock_utilization"]:.2%}')


if __name__=="__main__":
    main()
