import type { MetadataRoute } from "next";

const BASE_URL = "https://coolagristock.agricarecentres.com";

const paths = [
  "/",
  "/product",
  "/services",
  "/documentation",
  "/contact",
  "/en",
  "/en/product",
  "/en/services",
  "/en/documentation",
  "/en/contact",
];

export default function sitemap(): MetadataRoute.Sitemap {
  return paths.map((path) => ({
    url: `${BASE_URL}${path}`,
    lastModified: new Date(),
    changeFrequency: "monthly",
    priority: path === "/" ? 1 : 0.7,
  }));
}
