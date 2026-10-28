import type { Metadata } from "next";

export function buildMetadata({
  title,
  description,
  path,
  locale,
}: {
  title: string;
  description: string;
  path: string;
  locale: "fr_FR" | "en_US";
}): Metadata {
  return {
    title,
    description,
    alternates: {
      canonical: path,
      languages: {
        fr: path.replace(/^\/en/, "") || "/",
        en: path.startsWith("/en") ? path : `/en${path === "/" ? "" : path}`,
      },
    },
    openGraph: {
      title,
      description,
      url: path,
      siteName: "Cool Agristock",
      locale,
      type: "website",
      images: ["/images/icon.png"],
    },
    twitter: {
      card: "summary",
      title,
      description,
      images: ["/images/icon.png"],
    },
  };
}
