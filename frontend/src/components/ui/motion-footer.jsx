import React, { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Marquee from "react-fast-marquee";
import { ArrowUp, Heart } from "lucide-react";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

function MagneticButton({ as = "button", className = "", children, ...props }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ctx = gsap.context(() => {
      const move = (e) => {
        const r = el.getBoundingClientRect();
        const x = e.clientX - r.left - r.width / 2;
        const y = e.clientY - r.top - r.height / 2;
        gsap.to(el, { x: x * 0.3, y: y * 0.3, scale: 1.04, duration: 0.4, ease: "power2.out" });
      };
      const leave = () =>
        gsap.to(el, { x: 0, y: 0, scale: 1, duration: 1, ease: "elastic.out(1,0.3)" });
      el.addEventListener("mousemove", move);
      el.addEventListener("mouseleave", leave);
      return () => {
        el.removeEventListener("mousemove", move);
        el.removeEventListener("mouseleave", leave);
      };
    }, el);
    return () => ctx.revert();
  }, []);
  const Cmp = as;
  return (
    <Cmp ref={ref} className={`cursor-pointer inline-flex ${className}`} {...props}>
      {children}
    </Cmp>
  );
}

export default function MotionFooter() {
  const wrapperRef = useRef(null);
  const giantRef = useRef(null);
  const headingRef = useRef(null);
  const linksRef = useRef(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        giantRef.current,
        { y: 60, scale: 0.9, opacity: 0.2 },
        {
          y: 0, scale: 1, opacity: 1, ease: "power1.out",
          scrollTrigger: { trigger: wrapperRef.current, start: "top 80%", end: "bottom bottom", scrub: 1 },
        }
      );
      gsap.fromTo(
        [headingRef.current, linksRef.current],
        { y: 40, opacity: 0 },
        {
          y: 0, opacity: 1, stagger: 0.15, ease: "power3.out",
          scrollTrigger: { trigger: wrapperRef.current, start: "top 60%", end: "bottom bottom", scrub: 1 },
        }
      );
    }, wrapperRef);
    return () => ctx.revert();
  }, []);

  return (
    <footer
      ref={wrapperRef}
      data-testid="motion-footer"
      className="relative w-full overflow-hidden border-t border-[#2a2a2e] bg-[#060607] text-white mt-20"
      style={{ minHeight: "70vh" }}
    >
      {/* Aurora */}
      <div className="absolute left-1/2 top-1/2 h-[60vh] w-[80vw] -translate-x-1/2 -translate-y-1/2 rounded-[999px] pointer-events-none z-0 acos-aurora opacity-70" />
      {/* Grid */}
      <div className="absolute inset-0 z-0 pointer-events-none acos-grid-bg opacity-40" />

      {/* Giant background text */}
      <div
        ref={giantRef}
        className="font-display absolute -bottom-[3vh] left-1/2 -translate-x-1/2 whitespace-nowrap z-0 pointer-events-none select-none font-black tracking-tighter text-white/5"
        style={{ fontSize: "26vw", lineHeight: 0.8 }}
      >
        ACOS
      </div>

      {/* Marquee */}
      <div className="relative z-10 border-y border-[#2a2a2e] bg-[#0f0f11] py-4 mt-6">
        <Marquee gradient={false} speed={40}>
          <div className="flex items-center gap-10 px-6 text-xs md:text-sm font-bold tracking-[0.3em] text-[#8c8c93] uppercase font-mono-i">
            <span>Orchestrator online</span><span className="text-[#a8a8ad]/60">◆</span>
            <span>HR agent v1.3</span><span className="text-[#e2726f]/60">◆</span>
            <span>Finance agent auditing invoices</span><span className="text-[#a8a8ad]/60">◆</span>
            <span>Inventory agent — reorder queued</span><span className="text-[#e2726f]/60">◆</span>
            <span>Compliance clean</span><span className="text-[#a8a8ad]/60">◆</span>
            <span>All human approvals within SLA</span><span className="text-[#e2726f]/60">◆</span>
          </div>
        </Marquee>
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-col items-center justify-center px-6 py-20 max-w-5xl mx-auto text-center">
        <h2
          ref={headingRef}
          className="font-display text-5xl md:text-7xl font-black tracking-tighter mb-10 text-white"
        >
          Ship your company on autopilot.
        </h2>

        <div ref={linksRef} className="flex flex-wrap justify-center gap-3 md:gap-5">
          <MagneticButton
            as="a"
            href="#"
            data-testid="footer-cta-book-demo"
            className="px-8 py-4 rounded-[999px] bg-white text-black font-bold text-sm tracking-widest uppercase hover:bg-[#29292d] transition-colors"
          >
            Book a demo
          </MagneticButton>
          <MagneticButton
            as="a"
            href="#"
            data-testid="footer-cta-docs"
            className="px-8 py-4 rounded-full border border-[#2a2a2e] bg-white/5 text-white/90 font-bold text-sm tracking-widest uppercase hover:bg-white/10 transition-colors"
          >
            Read the docs
          </MagneticButton>
          <MagneticButton
            as="a"
            href="#"
            data-testid="footer-cta-support"
            className="px-8 py-4 rounded-full border border-[#2a2a2e] bg-white/5 text-white/90 font-bold text-sm tracking-widest uppercase hover:bg-white/10 transition-colors"
          >
            Support
          </MagneticButton>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="relative z-10 border-t border-[#2a2a2e] px-6 md:px-12 py-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="text-[#6f6f76] text-[10px] md:text-xs font-semibold tracking-widest uppercase font-mono-i">
          © 2026 ACOS — Autonomous Company OS. All rights reserved.
        </div>
        <div className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-[#2a2a2e] bg-white/5">
          <span className="text-[#8c8c93] text-[10px] md:text-xs font-bold uppercase tracking-widest">Made with</span>
          <Heart className="w-4 h-4 text-[#e2726f] fill-pink-500" />
          <span className="text-[#8c8c93] text-[10px] md:text-xs font-bold uppercase tracking-widest">by humans + agents</span>
        </div>
        <MagneticButton
          as="button"
          data-testid="footer-back-to-top"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="w-11 h-11 rounded-full border border-[#2a2a2e] bg-white/5 items-center justify-center text-[#f7f7f8] hover:text-white hover:bg-white/10 transition-colors"
        >
          <ArrowUp className="w-5 h-5 mx-auto" />
        </MagneticButton>
      </div>
    </footer>
  );
}
