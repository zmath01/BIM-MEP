import json
import math
from pathlib import Path
import unittest

from tinyhouse.geometry import generate
from tinyhouse.nest import optimize


class CabinTests(unittest.TestCase):
    def setUp(self):
        self.design=json.loads((Path(__file__).resolve().parents[1]/"design.json").read_text())
        self.parts=generate(self.design)
        self.nest=optimize(self.parts,self.design)

    def test_meshes_are_closed_and_named(self):
        self.assertEqual(len(self.parts),len({p.name for p in self.parts}))
        for part in self.parts:
            counts={}
            for face in part.faces:
                for a,b in zip(face,face[1:]+face[:1]):
                    edge=tuple(sorted((a,b)))
                    counts[edge]=counts.get(edge,0)+1
            self.assertTrue(all(n==2 for n in counts.values()),part.name)

    def test_net_wall_area_matches_analytical_opening_deduction(self):
        d=self.design
        expected=2*(d["width_mm"]+d["depth_mm"])*d["wall_height_mm"]
        expected-=sum(o["w"]*o["h"] for o in d["openings"])
        actual=sum(p.blank[0]*p.blank[1] for p in self.parts if p.group=="wall_skin")
        self.assertAlmostEqual(expected,actual,places=6)

    def test_deck_and_roof_area_match_formulas(self):
        d=self.design
        w,l,g=d["width_mm"],d["depth_mm"],d["gable_rise_mm"]
        for group,target in (("floor_skin",w*l),("roof_skin",2*l*math.hypot(w/2,g))):
            self.assertAlmostEqual(sum(p.blank[0]*p.blank[1] for p in self.parts if p.group==group),target,places=6)

    def test_all_blanks_packed_exactly_once_with_edge_and_gap(self):
        w,h=self.design["board_mm"]
        m,g=self.design["board_edge_margin_mm"],self.design["part_gap_mm"]
        represented=[]
        blanks={p.name:p.blank for p in self.parts if p.blank}
        for sheet in self.nest["sheets"]:
            for i,a in enumerate(sheet):
                self.assertGreaterEqual(a["x"],m)
                self.assertGreaterEqual(a["y"],m)
                self.assertLessEqual(a["x"]+a["w"],w-m+1e-7)
                self.assertLessEqual(a["y"]+a["h"],h-m+1e-7)
                self.assertEqual((a["w"],a["h"]),blanks[a["name"]])
                represented.append(a["name"])
                for b in sheet[:i]:
                    self.assertTrue(
                        a["x"]+a["w"]+g <= b["x"]+1e-7 or b["x"]+b["w"]+g <= a["x"]+1e-7 or
                        a["y"]+a["h"]+g <= b["y"]+1e-7 or b["y"]+b["h"]+g <= a["y"]+1e-7)
        self.assertCountEqual(represented,blanks.keys())

    def test_layout_improves_on_model_order(self):
        result=self.nest
        self.assertEqual(len(result["sheets"]),20)
        self.assertEqual(result["trial_counts"]["as_modelled"],24)
        self.assertEqual(result["area_bound"],18)
        self.assertTrue(0 < result["stock_utilization"] <= 1)

    def test_invalid_openings(self):
        self.design["openings"][0]["w"]=4000
        with self.assertRaisesRegex(ValueError,"Opening outside"):
            generate(self.design)


if __name__=="__main__":
    unittest.main()
