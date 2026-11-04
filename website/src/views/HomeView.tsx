import Link from "next/link";
import type { Dictionary, Lang } from "@/types/content";

function withLang(path: string, lang: Lang): string {
  return lang === "en" ? `/en${path}` : path;
}

export function HomeView({ lang, dict }: { lang: Lang; dict: Dictionary }) {
  const d = dict.home;

  return (
    <>
      {/* SECTION 1: Hero */}
      <section className="bg-gradient-to-b from-brand-50 to-white">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            {d.hero.headline}
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-gray-600">{d.hero.subheadline}</p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <a
              href="https://apps.odoo.com/apps/modules/19.0/cool_agristock"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full rounded-md bg-brand-600 px-6 py-3 text-base font-semibold text-white hover:bg-brand-700 sm:w-auto"
            >
              {d.hero.downloadCta}
            </a>
            <Link
              href={withLang("/contact", lang)}
              className="w-full rounded-md border border-gray-300 px-6 py-3 text-base font-semibold text-gray-800 hover:bg-gray-50 sm:w-auto"
            >
              {d.hero.requestCta}
            </Link>
          </div>
        </div>
      </section>

      {/* SECTION 1b: Video */}
      <section className="mx-auto max-w-4xl px-4 py-16 sm:px-6">
        <h2 className="text-center text-2xl font-bold text-gray-900">{d.video.title}</h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-gray-600">{d.video.description}</p>
        <div className="mx-auto mt-8 aspect-video max-w-3xl overflow-hidden rounded-lg border border-gray-200 shadow-sm">
          <iframe
            className="h-full w-full"
            src={`https://www.youtube-nocookie.com/embed/${d.video.youtubeId}`}
            title={d.video.title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        </div>
      </section>

      {/* SECTION 2: The Problem */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <h2 className="text-2xl font-bold text-gray-900">{d.problem.title}</h2>
        <p className="mt-3 max-w-2xl text-gray-600">{d.problem.intro}</p>
        <ul className="mt-8 grid gap-4 sm:grid-cols-2">
          {d.problem.items.map((item) => (
            <li key={item} className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* SECTION 3: The Solution */}
      <section className="bg-gray-50">
        <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
          <h2 className="text-2xl font-bold text-gray-900">{d.solution.title}</h2>
          <p className="mt-3 max-w-2xl text-gray-600">{d.solution.description}</p>

          <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <div className="rounded-lg border border-gray-300 bg-white px-5 py-3 text-center font-semibold text-gray-800">
              {d.solution.diagram.wms}
            </div>
            <span className="text-sm text-gray-400" aria-hidden="true">
              —&nbsp;{d.solution.diagram.api}&nbsp;→
            </span>
            <div className="rounded-lg border border-brand-300 bg-brand-50 px-5 py-3 text-center font-semibold text-brand-800">
              {d.solution.diagram.connector}
            </div>
            <span className="text-sm text-gray-400" aria-hidden="true">
              →
            </span>
            <div className="rounded-lg border border-gray-300 bg-white px-5 py-3 text-center font-semibold text-gray-800">
              {d.solution.diagram.odoo}
            </div>
          </div>
          <p className="mx-auto mt-6 max-w-2xl text-center text-sm text-gray-500">
            {d.solution.initiatedNote}
          </p>
        </div>
      </section>

      {/* SECTION 4: Key Features */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <h2 className="text-2xl font-bold text-gray-900">{d.features.title}</h2>
        <ul className="mt-8 grid gap-3 sm:grid-cols-2">
          {d.features.items.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-gray-700">
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600" aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* SECTION 5: How It Works */}
      <section className="bg-gray-50">
        <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
          <h2 className="text-2xl font-bold text-gray-900">{d.howItWorks.title}</h2>
          <ol className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {d.howItWorks.steps.map((step, i) => (
              <li key={step} className="rounded-lg border border-gray-200 bg-white p-5">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white">
                  {i + 1}
                </span>
                <p className="mt-3 text-sm text-gray-700">{step}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* SECTION 6: Professional Services */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <h2 className="text-2xl font-bold text-gray-900">{d.services.title}</h2>
        <p className="mt-3 max-w-2xl text-gray-600">{d.services.intro}</p>
        <ul className="mt-8 grid gap-4 sm:grid-cols-2">
          {d.services.items.map((item) => (
            <li key={item.name} className="rounded-lg border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900">{item.name}</h3>
              <p className="mt-1 text-sm text-gray-600">{item.description}</p>
            </li>
          ))}
        </ul>
        <Link
          href={withLang("/services", lang)}
          className="mt-6 inline-block text-sm font-semibold text-brand-700 underline"
        >
          {d.services.link} →
        </Link>
      </section>

      {/* SECTION 7: Call to Action */}
      <section className="bg-brand-700">
        <div className="mx-auto max-w-4xl px-4 py-16 text-center sm:px-6">
          <h2 className="text-2xl font-bold text-white">{d.cta.title}</h2>
          <p className="mx-auto mt-3 max-w-xl text-brand-50">{d.cta.description}</p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <a
              href="https://apps.odoo.com/apps/modules/19.0/cool_agristock"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full rounded-md bg-white px-6 py-3 text-base font-semibold text-brand-800 hover:bg-brand-50 sm:w-auto"
            >
              {d.cta.downloadCta}
            </a>
            <Link
              href={withLang("/contact", lang)}
              className="w-full rounded-md border border-brand-300 px-6 py-3 text-base font-semibold text-white hover:bg-brand-600 sm:w-auto"
            >
              {d.cta.requestCta}
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
