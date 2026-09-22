import React from "react";

export default function PageHeader({ eyebrow, title, children }) {
  return (
    <header className="flex items-end justify-between mb-6">
      <div>
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#a8a8ad] font-mono-i">{eyebrow}</div>
        <h1 className="font-display text-4xl font-black tracking-tighter mt-1">{title}</h1>
      </div>
      {children}
    </header>
  );
}
