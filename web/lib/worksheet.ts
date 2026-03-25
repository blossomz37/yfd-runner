export type WorksheetSection = {
  sectionKey: string;
  sectionNumber: number;
  sectionSuffix: string;
  text: string;
};

const SECTION_HEADING_PATTERN = /^## (section_(\d+)_([^\n]+))\s*$/gm;

export function parseWorksheetSections(worksheetText: string): WorksheetSection[] {
  const matches = Array.from(worksheetText.matchAll(SECTION_HEADING_PATTERN));
  if (!matches.length) {
    return [];
  }

  return matches.map((match, index) => {
    const start = match.index ?? 0;
    const end = index + 1 < matches.length ? (matches[index + 1].index ?? worksheetText.length) : worksheetText.length;
    return {
      sectionKey: match[1],
      sectionNumber: Number(match[2]),
      sectionSuffix: match[3],
      text: worksheetText.slice(start, end).trim()
    };
  });
}

export function normalizeWorksheetSectionContent(section: WorksheetSection, content: string): string {
  const normalized = content.trim();
  if (!normalized) {
    return "";
  }
  const heading = `## ${section.sectionKey}`;
  return normalized.startsWith("## ") ? normalized : `${heading}\n\n${normalized}`;
}

export function worksheetSectionBody(sectionText: string): string {
  return sectionText.replace(/^## [^\n]+\s*\n?/, "").trim();
}

export function worksheetSectionLabel(section: WorksheetSection): string {
  return `#${String(section.sectionNumber).padStart(2, "0")} ${section.sectionSuffix.replace(/_/g, " ")}`;
}
