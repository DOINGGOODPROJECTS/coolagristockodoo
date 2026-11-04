"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useState } from "react";
import type { Dictionary, Lang } from "@/types/content";

function withLang(path: string, lang: Lang): string {
  return lang === "en" ? `/en${path}` : path;
}

function otherLangHref(pathname: string, lang: Lang): string {
  const isEnglish = pathname === "/en" || pathname.startsWith("/en/");
  if (lang === "en") {
    // currently English -> strip /en prefix for French
    const rest = pathname.replace(/^\/en/, "");
    return rest === "" ? "/" : rest;
  }
  // currently French -> add /en prefix
  if (isEnglish) return pathname; // shouldn't happen given lang="fr" here
  return pathname === "/" ? "/en" : `/en${pathname}`;
}

export function Header({ lang, dict }: { lang: Lang; dict: Dictionary }) {
  const pathname = usePathname() ?? "/";
  const [open, setOpen] = useState(false);

  const navItems: { label: string; href: string }[] = [
    { label: dict.nav.home, href: withLang("/", lang) },
    { label: dict.nav.product, href: withLang("/product", lang) },
    { label: dict.nav.services, href: withLang("/services", lang) },
    { label: dict.nav.documentation, href: withLang("/documentation", lang) },
    { label: dict.nav.contact, href: withLang("/contact", lang) },
  ];

  const switchHref = otherLangHref(pathname, lang);

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <Link href={withLang("/", lang)} className="flex items-center gap-2 font-semibold text-brand-700">
          <Image src="/images/icon.png" alt="" width={32} height={32} className="rounded" />
          <span>{dict.meta.siteName}</span>
        </Link>

        <nav className="hidden items-center gap-6 md:flex" aria-label="Primary">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-sm font-medium text-gray-700 hover:text-brand-700"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-4 md:flex">
          <Link
            href={switchHref}
            className="text-sm font-medium text-gray-500 hover:text-brand-700"
            hrefLang={lang === "en" ? "fr" : "en"}
          >
            {dict.nav.switchLabel}
          </Link>
          <a
            href="https://apps.odoo.com/apps/modules/19.0/cool_agristock"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            {dict.nav.downloadFree}
          </a>
        </div>

        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md p-2 text-gray-700 md:hidden"
          aria-expanded={open}
          aria-controls="mobile-menu"
          aria-label="Toggle navigation menu"
          onClick={() => setOpen((v) => !v)}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M4 6h16M4 12h16M4 18h16"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>

      {open && (
        <div id="mobile-menu" className="border-t border-gray-200 md:hidden">
          <nav className="flex flex-col gap-1 px-4 py-3" aria-label="Primary mobile">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-md px-2 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                onClick={() => setOpen(false)}
              >
                {item.label}
              </Link>
            ))}
            <Link
              href={switchHref}
              className="rounded-md px-2 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50"
            >
              {dict.nav.switchLabel}
            </Link>
            <a
              href="https://apps.odoo.com/apps/modules/19.0/cool_agristock"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 rounded-md bg-brand-600 px-4 py-2 text-center text-sm font-semibold text-white"
            >
              {dict.nav.downloadFree}
            </a>
          </nav>
        </div>
      )}
    </header>
  );
}
