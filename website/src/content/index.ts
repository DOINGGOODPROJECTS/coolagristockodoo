import type { Dictionary, Lang } from "@/types/content";
import { en } from "./en";
import { fr } from "./fr";

export const dictionaries: Record<Lang, Dictionary> = { en, fr };

export function getDictionary(lang: Lang): Dictionary {
  return dictionaries[lang];
}

export const GITHUB_REPO_URL = "https://github.com/DOINGGOODPROJECTS/coolagristockodoo";
export const MARKETPLACE_URL = "https://apps.odoo.com/apps/modules/19.0/agriware_connector";
