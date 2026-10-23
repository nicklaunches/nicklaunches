"""Manim sample (3Blue1Brown-style 2D explainer) in 9:16.
Beat: 'what hashing does to your password' - text morphs, arrows draw, counters.
Run: manim -qm -r 1080,1920 hashing.py HashExplainer
"""
from manim import *

config.frame_height = 8.0; config.frame_width = 4.5   # portrait frame units for 1080x1920
BG = "#0b0f1a"; INK = "#f5f7ff"; ACCENT = "#c8ff3d"; PINK = "#ff5fa8"; CYAN = "#4df0ff"; MUTED = "#8d95b3"

class HashExplainer(Scene):
    def construct(self):
        self.camera.background_color = BG
        # 9:16 at 1080x1920 -> frame is 4.5 wide x 8 tall; everything is laid out in those units
        W = 4.0

        # --- hook
        hook = Text("Why can't a site\n'see' your password?", font="Inter", weight=BOLD, font_size=48, color=INK, line_spacing=1.0).scale_to_fit_width(W)
        self.play(FadeIn(hook, shift=UP * 0.5, scale=0.9), run_time=0.6)
        self.wait(1.2)
        self.play(hook.animate.scale(0.55).to_edge(UP, buff=0.5).set_color(MUTED), run_time=0.6)

        # --- password box
        pw = Text("hunter2", font="DejaVu Sans Mono", font_size=44, color=CYAN)
        box = RoundedRectangle(corner_radius=0.2, width=3, height=1, color=CYAN, stroke_width=4).surround(pw, buff=0.35)
        grp = VGroup(box, pw).move_to(UP * 2.1)
        self.play(Create(box), Write(pw), run_time=0.8)

        # --- hash function block
        fn = Text("SHA-256", font="Inter", weight=BOLD, font_size=40, color=ACCENT)
        fnbox = RoundedRectangle(corner_radius=0.2, width=3, height=1, color=ACCENT, stroke_width=4).surround(fn, buff=0.35)
        fgrp = VGroup(fnbox, fn).move_to(UP * 0.5)
        arrow1 = Arrow(grp.get_bottom(), fgrp.get_top(), buff=0.2, color=MUTED, stroke_width=6)
        self.play(GrowArrow(arrow1), run_time=0.4)
        self.play(FadeIn(fgrp, scale=0.6), run_time=0.5)

        # --- digest: scrambling text effect
        digest_final = "2ab96390c7dbe3439de74d0c9b0b1767"
        fmt = lambda d: d[:16] + "\n" + d[16:]
        digest = Text(fmt(digest_final), font="DejaVu Sans Mono", font_size=26, color=PINK, line_spacing=0.9).move_to(DOWN * 1.2)
        arrow2 = Arrow(fgrp.get_bottom(), digest.get_top(), buff=0.2, color=MUTED, stroke_width=6)
        self.play(GrowArrow(arrow2), run_time=0.4)
        import random
        random.seed(7)
        chars = "0123456789abcdef"
        scr = Text(fmt("".join(random.choice(chars) for _ in digest_final)), font="DejaVu Sans Mono", font_size=26, color=PINK, line_spacing=0.9).move_to(digest)
        self.add(scr)
        for _ in range(8):
            new = Text(fmt("".join(random.choice(chars) for _ in digest_final)), font="DejaVu Sans Mono", font_size=26, color=PINK, line_spacing=0.9).move_to(digest)
            self.remove(scr); scr = new; self.add(scr); self.wait(0.07)
        self.remove(scr); self.play(FadeIn(digest, scale=1.1), run_time=0.3)

        # --- caption
        cap = Text("one-way. same input, same output.\nno way back.", font="Inter", weight=BOLD, font_size=30, color=INK, line_spacing=1.0).scale_to_fit_width(W).to_edge(DOWN, buff=1.0)
        self.play(FadeIn(cap, shift=UP * 0.3), run_time=0.5)
        self.wait(1.0)

        # --- 'reverse?' attempt: arrow flips and gets crossed out
        back = Arrow(digest.get_top(), fgrp.get_bottom(), buff=0.2, color=PINK, stroke_width=8)
        cross = Cross(back, stroke_color=PINK, stroke_width=10).scale(0.5)
        self.play(Transform(arrow2, back), run_time=0.4)
        self.play(Create(cross), Flash(cross, color=PINK, line_length=0.4), run_time=0.5)
        self.wait(0.6)

        # --- counter: brute-force guesses needed
        n = ValueTracker(0)
        label = Text("guesses to reverse it", font="Inter", font_size=24, color=MUTED).move_to(DOWN * 2.9)
        num = always_redraw(lambda: Text(f"{int(n.get_value()):,}", font="Inter", weight=BOLD, font_size=44, color=ACCENT).scale_to_fit_width(min(W, 0.33 * len(f"{int(n.get_value()):,}"))).next_to(label, UP, buff=0.15))
        self.play(FadeOut(cap), FadeIn(label), FadeIn(num), run_time=0.4)
        self.play(n.animate.set_value(10**9), run_time=1.6, rate_func=rush_from)
        big = Text("...per second, for 10^60 years", font="Inter", font_size=22, color=MUTED).scale_to_fit_width(W).next_to(label, DOWN, buff=0.15)
        self.play(FadeIn(big), run_time=0.4)
        self.wait(1.0)

        # --- payoff
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
        payoff = Text("Sites store the hash.\nNever the password.", font="Inter", weight=BOLD, font_size=48, color=INK, line_spacing=1.0).scale_to_fit_width(W)
        payoff[len("Sites store the hash."):].set_color(ACCENT)
        self.play(FadeIn(payoff, scale=0.8), run_time=0.6)
        self.wait(1.5)
