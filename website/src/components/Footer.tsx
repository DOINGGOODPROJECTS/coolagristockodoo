import type { Dictionary, Lang } from "@/types/content";

export function Footer({ dict }: { dict: Dictionary; lang: Lang }) {
  return (
    <footer className="border-t border-gray-200 bg-gray-50">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <p className="text-sm text-gray-600">{dict.footer.tagline}</p>
        <p className="mt-2 text-sm font-medium text-brand-700">{dict.footer.freeOpenSource}</p>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <a
            href="https://github.com/DOINGGOODPROJECTS/coolagristockodoo"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-gray-700 underline hover:text-brand-700"
          >
            {dict.footer.githubLabel}
          </a>
        </div>
        <p className="mt-6 text-xs text-gray-400">{dict.footer.rights}</p>
      </div>
    </footer>
  );
}
