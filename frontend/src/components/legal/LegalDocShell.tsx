"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  ArrowUp,
  Check,
  ChevronDown,
  ChevronRight,
  Link2,
  Printer,
} from "lucide-react";

export interface TocItem {
  id: string;
  number: string;
  title: string;
}

export type SecurityCapabilityStatus =
  | "implemented-verified"
  | "implemented-unverified"
  | "partially-implemented"
  | "planned"
  | "not-implemented";

export function SecurityStatusBadge({ status }: { status: SecurityCapabilityStatus }) {
  const styles: Record<SecurityCapabilityStatus, { label: string; cls: string }> = {
    "implemented-verified": {
      label: "Implemented and independently verified",
      cls: "bg-[#EAF7EE] text-[#1E6B36] border-[#2E9D50]/40",
    },
    "implemented-unverified": {
      label: "Implemented but not independently verified",
      cls: "bg-[#FFF7E6] text-[#9A5B00] border-[#F59A23]/40",
    },
    "partially-implemented": {
      label: "Partially implemented",
      cls: "bg-[#EEF4FF] text-[#1D5FBF] border-[#2878D4]/40",
    },
    planned: {
      label: "Planned",
      cls: "bg-[#F3F4F6] text-[#374151] border-[#D1D5DB]",
    },
    "not-implemented": {
      label: "Not implemented",
      cls: "bg-[#FEF2F2] text-[#991B1B] border-[#FCA5A5]",
    },
  };
  const cfg = styles[status];
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-[5px] text-[11px] font-bold border ${cfg.cls}`}
    >
      {cfg.label}
    </span>
  );
}

export function DocSection({
  id,
  number,
  title,
  children,
}: {
  id: string;
  number: string;
  title: string;
  children: React.ReactNode;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (typeof window === "undefined") return;
    const url = `${window.location.origin}${window.location.pathname}#${id}`;
    navigator.clipboard?.writeText(url).catch(() => {});
    window.history.replaceState(null, "", `#${id}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <section
      id={id}
      aria-labelledby={`${id}-heading`}
      className="scroll-mt-24 pb-9 border-b border-[#E8E8E4] last:border-b-0 space-y-4"
    >
      <div className="flex items-start justify-between gap-3 group">
        <h2
          id={`${id}-heading`}
          className="text-[19px] sm:text-[21px] font-bold text-[#141414] tracking-tight leading-snug"
        >
          <span className="text-[#237A3C] mr-2 font-bold">{number}.</span>
          {title}
        </h2>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={`Copy link to section ${number}: ${title}`}
          title="Copy section link"
          className="no-print shrink-0 p-1.5 rounded-[6px] text-[#888888] hover:text-[#1F1F1F] hover:bg-[#F2F2EE] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E9D50] transition-colors"
        >
          {copied ? (
            <Check className="w-4 h-4 text-[#2E9D50]" />
          ) : (
            <Link2 className="w-4 h-4" />
          )}
        </button>
      </div>
      <div className="text-[14.5px] text-[#333333] leading-[1.7] space-y-3.5">
        {children}
      </div>
    </section>
  );
}

export default function LegalDocShell({
  activeRoute,
  breadcrumbLabel,
  title,
  description,
  effectiveDate,
  lastUpdated,
  version,
  toc,
  children,
}: {
  activeRoute: "/privacy" | "/terms" | "/security";
  breadcrumbLabel: string;
  title: string;
  description: string;
  effectiveDate?: string;
  lastUpdated: string;
  version: string;
  toc: TocItem[];
  children: React.ReactNode;
}) {
  const [activeId, setActiveId] = useState<string>(toc[0]?.id || "");
  const [mobileTocOpen, setMobileTocOpen] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setShowBackToTop(window.scrollY > 400);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined" || toc.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: "-96px 0px -65% 0px", threshold: 0.01 }
    );

    toc.forEach((item) => {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [toc]);

  const scrollToSection = (id: string) => {
    setMobileTocOpen(false);
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      window.history.replaceState(null, "", `#${id}`);
      setActiveId(id);
    }
  };

  const navLinks: Array<{ href: "/privacy" | "/terms" | "/security"; label: string }> = [
    { href: "/privacy", label: "Privacy Policy" },
    { href: "/terms", label: "Terms of Service" },
    { href: "/security", label: "Zero-Trust Security" },
  ];

  return (
    <div className="min-h-screen bg-[#FCFCFA] text-[#1F1F1F] flex flex-col">
      {/* Top Bar */}
      <header className="no-print sticky top-0 z-40 bg-[#FFFFFF]/95 backdrop-blur-sm border-b border-[#E8E8E4]">
        <div className="max-w-[1220px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <Link
              href="/"
              className="flex items-center gap-2.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E9D50] rounded-[6px]"
            >
              <div className="w-8 h-8 rounded-[8px] bg-[#EAF7EE] border border-[#2E9D50]/30 flex items-center justify-center p-1">
                <Image
                  src="/logo.png"
                  alt="AGENTGUARD Logo"
                  width={24}
                  height={24}
                  className="object-contain"
                />
              </div>
              <span className="text-[16px] font-bold tracking-tight text-[#141414]">
                AGENTGUARD
              </span>
            </Link>

            <nav aria-label="Legal and security documents" className="hidden md:flex items-center gap-1 text-[13px]">
              {navLinks.map((item) => {
                const isActive = item.href === activeRoute;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={isActive ? "page" : undefined}
                    className={`px-3 py-1.5 rounded-[6px] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E9D50] ${
                      isActive
                        ? "bg-[#EAF7EE] text-[#1E6B36] font-bold"
                        : "text-[#555555] hover:text-[#141414] hover:bg-[#F5F5F2]"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-2.5 text-[12px]">
            <button
              type="button"
              onClick={() => window.print()}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 border border-[#E8E8E4] bg-[#FFFFFF] hover:bg-[#F5F5F2] text-[#333333] font-bold rounded-[6px] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E9D50]"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print</span>
            </button>
            <Link
              href="/login"
              className="px-3.5 py-1.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white font-bold rounded-[6px] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E9D50]"
            >
              Sign In
            </Link>
          </div>
        </div>
      </header>

      {/* Formal Document Masthead */}
      <div className="bg-[#FFFFFF] border-b border-[#E8E8E4]">
        <div className="max-w-[1220px] mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
          <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-[12px] text-[#666666] mb-4">
            <Link href="/" className="hover:text-[#141414]">
              AGENTGUARD
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-[#999999]" />
            <span>Legal &amp; Security</span>
            <ChevronRight className="w-3.5 h-3.5 text-[#999999]" />
            <span className="text-[#141414] font-bold">{breadcrumbLabel}</span>
          </nav>

          <h1 className="text-[30px] sm:text-[38px] font-bold text-[#141414] tracking-tight leading-tight">
            {title}
          </h1>
          <p className="mt-3 text-[15px] sm:text-[16px] text-[#555555] max-w-[74ch] leading-relaxed">
            {description}
          </p>

          <dl className="mt-6 pt-5 border-t border-[#E8E8E4] flex flex-wrap gap-x-8 gap-y-2 text-[12px] text-[#666666]">
            {effectiveDate && (
              <div className="flex items-center gap-1.5">
                <dt className="font-bold text-[#141414]">Effective Date:</dt>
                <dd>{effectiveDate}</dd>
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <dt className="font-bold text-[#141414]">Last Updated:</dt>
              <dd>{lastUpdated}</dd>
            </div>
            <div className="flex items-center gap-1.5">
              <dt className="font-bold text-[#141414]">Version:</dt>
              <dd>{version}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Main Two-Column Documentation Body */}
      <main className="flex-1 max-w-[1220px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* Mobile Collapsible TOC */}
        <div className="no-print lg:hidden mb-6 border border-[#E8E8E4] rounded-[10px] bg-[#FFFFFF]">
          <button
            type="button"
            onClick={() => setMobileTocOpen(!mobileTocOpen)}
            aria-expanded={mobileTocOpen}
            className="w-full px-4 py-3 flex items-center justify-between text-[13px] font-bold text-[#141414]"
          >
            <span>Table of Contents ({toc.length} sections)</span>
            <ChevronDown
              className={`w-4 h-4 text-[#666666] transition-transform ${
                mobileTocOpen ? "rotate-180" : ""
              }`}
            />
          </button>
          {mobileTocOpen && (
            <nav aria-label="Mobile table of contents" className="border-t border-[#E8E8E4] px-3 py-2 max-h-72 overflow-y-auto space-y-0.5">
              {toc.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => scrollToSection(item.id)}
                  className={`w-full text-left px-2.5 py-1.5 rounded-[6px] text-[12.5px] transition-colors ${
                    activeId === item.id
                      ? "bg-[#EAF7EE] text-[#1E6B36] font-bold"
                      : "text-[#555555] hover:bg-[#F5F5F2]"
                  }`}
                >
                  <span className="mr-1.5 text-[#237A3C]">{item.number}.</span>
                  {item.title}
                </button>
              ))}
            </nav>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)] gap-10 items-start">
          {/* Desktop Sticky Left TOC */}
          <aside className="no-print hidden lg:block sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto pr-3 border-r border-[#E8E8E4]">
            <div className="text-[11px] font-bold uppercase tracking-wider text-[#666666] mb-3 px-2">
              On This Page
            </div>
            <nav aria-label="Table of contents" className="space-y-0.5">
              {toc.map((item) => {
                const isActive = activeId === item.id;
                return (
                  <a
                    key={item.id}
                    href={`#${item.id}`}
                    onClick={(e) => {
                      e.preventDefault();
                      scrollToSection(item.id);
                    }}
                    className={`block px-2.5 py-1.5 rounded-[6px] text-[12.5px] leading-snug transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E9D50] ${
                      isActive
                        ? "bg-[#EAF7EE] text-[#1E6B36] font-bold border-l-2 border-[#2E9D50]"
                        : "text-[#555555] hover:text-[#141414] hover:bg-[#F5F5F2]"
                    }`}
                  >
                    <span className="mr-1.5 text-[#237A3C]">{item.number}.</span>
                    {item.title}
                  </a>
                );
              })}
            </nav>
          </aside>

          {/* Right Legal / Technical Content */}
          <article className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 sm:p-10 max-w-[82ch] space-y-9">
            {children}
          </article>
        </div>
      </main>

      {/* Back to Top Button */}
      {showBackToTop && (
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          aria-label="Back to top"
          className="no-print fixed bottom-6 right-6 z-40 inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-[#1F1F1F] hover:bg-[#333333] text-white text-[12px] font-bold shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2E9D50] transition-colors"
        >
          <ArrowUp className="w-3.5 h-3.5" />
          <span>Top</span>
        </button>
      )}

      {/* Enterprise Footer */}
      <footer className="no-print bg-[#FFFFFF] border-t border-[#E8E8E4] py-10 mt-10 text-[12.5px] text-[#555555]">
        <div className="max-w-[1220px] mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="font-bold text-[#141414] text-[14px]">AGENTGUARD</div>
              <p className="text-[12px] text-[#666666]">
                Enterprise AI Agent Governance &amp; Runtime Control Plane
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-6 font-medium">
              <Link
                href="/privacy"
                className={activeRoute === "/privacy" ? "text-[#1E6B36] font-bold" : "hover:text-[#141414]"}
              >
                Privacy Policy
              </Link>
              <Link
                href="/terms"
                className={activeRoute === "/terms" ? "text-[#1E6B36] font-bold" : "hover:text-[#141414]"}
              >
                Terms of Service
              </Link>
              <Link
                href="/security"
                className={activeRoute === "/security" ? "text-[#1E6B36] font-bold" : "hover:text-[#141414]"}
              >
                Zero-Trust Security
              </Link>
              <Link href="/login" className="hover:text-[#141414]">
                Control Plane Sign In
              </Link>
            </div>
          </div>

          <div className="pt-5 border-t border-[#E8E8E4] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[11.5px] text-[#666666]">
            <span>
              &copy; {new Date().getFullYear()} [COMPANY INFORMATION REQUIRED: Legal Entity Name]. All rights reserved.
            </span>
            <span>
              Contact: [COMPANY INFORMATION REQUIRED: Legal, Privacy &amp; Security Contact Email]
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
