/** Human labels, plain-English explanations and editing controls for the 16 style attributes. */

export type AttributeCategory = "Structure" | "Formatting" | "Writing";

export type ControlKind = "text" | "number" | "select" | "boolean" | "list" | "readonly";

export interface AttributeMeta {
  label: string;
  category: AttributeCategory;
  /** What this attribute means, in the user's terms rather than the schema's. */
  help: string;
  control: ControlKind;
  options?: string[];
  /** Turns a raw value into a sentence a person can actually act on. */
  describe?: (value: unknown) => string;
  unit?: string;
}

const perThousand = (noun: string) => (value: unknown) => {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n) || n <= 0) return `You rarely use ${noun}.`;
  if (n < 5) return `You use ${noun} occasionally — about ${n.toFixed(1)} per 1,000 words.`;
  if (n < 20) return `You use ${noun} regularly — about ${Math.round(n)} per 1,000 words.`;
  return `You lean heavily on ${noun} — about ${Math.round(n)} per 1,000 words.`;
};

export const STYLE_ATTRIBUTES: Record<string, AttributeMeta> = {
  heading_style: {
    label: "Heading style",
    category: "Structure",
    help: "How you title sections.",
    control: "text",
    describe: (v) => `You title sections like this: ${String(v)}.`,
  },
  heading_depth: {
    label: "Heading depth",
    category: "Structure",
    help: "How many levels of nesting you use.",
    control: "number",
    describe: (v) => {
      const n = Number(v);
      if (!Number.isFinite(n) || n <= 1) return "You keep headings flat — mostly one level.";
      if (n < 2.5) return "You nest about two levels deep.";
      return `You nest deeply — around ${n.toFixed(1)} levels.`;
    },
  },
  section_order: {
    label: "Section order",
    category: "Structure",
    help: "The order your sections usually follow.",
    control: "list",
    describe: (v) =>
      Array.isArray(v) && v.length
        ? `Your notes usually run: ${v.join(" → ")}.`
        : "No consistent section order learned yet.",
  },
  summary_position: {
    label: "Summary position",
    category: "Structure",
    help: "Where you put a summary, if you use one.",
    control: "select",
    options: ["None", "Start", "End"],
    describe: (v) =>
      v === "None" ? "You don't usually write a summary section." : `You put summaries at the ${String(v).toLowerCase()}.`,
  },
  preferred_sections: {
    label: "Preferred sections",
    category: "Structure",
    help: "Sections you tend to include.",
    control: "list",
    describe: (v) =>
      Array.isArray(v) && v.length ? `You often include: ${v.join(", ")}.` : "No recurring sections learned yet.",
  },

  bullet_style: {
    label: "Bullet style",
    category: "Formatting",
    help: "The bullet character and shape you favour.",
    control: "text",
    describe: (v) => `Your bullets look like: ${String(v)}.`,
  },
  bullet_frequency: {
    label: "Bullet frequency",
    category: "Formatting",
    help: "How much of your writing is bulleted rather than prose.",
    control: "number",
    unit: "per 1,000 words",
    describe: perThousand("bullet points"),
  },
  code_block_frequency: {
    label: "Code blocks",
    category: "Formatting",
    help: "How often you include code.",
    control: "number",
    unit: "per 1,000 words",
    describe: perThousand("code blocks"),
  },
  table_frequency: {
    label: "Tables",
    category: "Formatting",
    help: "How often you compare things in a table.",
    control: "number",
    unit: "per 1,000 words",
    describe: perThousand("tables"),
  },
  diagram_frequency: {
    label: "Diagrams",
    category: "Formatting",
    help: "How often notes should include a diagram.",
    control: "number",
    unit: "per 1,000 words",
    describe: perThousand("diagrams"),
  },
  keyword_highlighting: {
    label: "Keyword highlighting",
    category: "Formatting",
    help: "Whether you bold or emphasise key terms.",
    control: "boolean",
    describe: (v) => (v ? "You bold key terms as you go." : "You don't usually highlight key terms."),
  },
  formatting_preferences: {
    label: "Other formatting",
    category: "Formatting",
    help: "Miscellaneous formatting habits picked up from your notes.",
    control: "readonly",
    describe: (v) =>
      v && Object.keys(v as object).length
        ? "A few extra formatting habits have been learned."
        : "Nothing extra learned here yet.",
  },

  average_sentence_length: {
    label: "Sentence length",
    category: "Writing",
    help: "Typical words per sentence.",
    control: "number",
    unit: "words",
    describe: (v) => {
      const n = Number(v);
      if (!Number.isFinite(n) || n <= 0) return "No sentence-length pattern learned yet.";
      if (n < 12) return `You write short sentences — around ${Math.round(n)} words.`;
      if (n <= 20) return `You write medium-length sentences — around ${Math.round(n)} words.`;
      return `You write long sentences — around ${Math.round(n)} words.`;
    },
  },
  average_paragraph_length: {
    label: "Paragraph length",
    category: "Writing",
    help: "Typical words per paragraph.",
    control: "number",
    unit: "words",
    describe: (v) => {
      const n = Number(v);
      if (!Number.isFinite(n) || n <= 0) return "No paragraph-length pattern learned yet.";
      if (n < 40) return `You keep paragraphs tight — around ${Math.round(n)} words.`;
      return `Your paragraphs run to about ${Math.round(n)} words.`;
    },
  },
  tone: {
    label: "Tone",
    category: "Writing",
    help: "How formal or conversational your notes read.",
    control: "select",
    options: ["Academic", "Conversational", "Concise", "Explanatory", "Technical"],
    describe: (v) => `Your notes read as ${String(v).toLowerCase()}.`,
  },
  example_density: {
    label: "Example density",
    category: "Writing",
    help: "How much you lean on worked examples.",
    control: "select",
    options: ["Low", "Medium", "High"],
    describe: (v) => {
      const s = String(v).toLowerCase();
      if (s === "high") return "You learn through examples — expect plenty of them.";
      if (s === "low") return "You keep examples sparse.";
      return "You use a moderate number of examples.";
    },
  },
};

export const CATEGORY_ORDER: AttributeCategory[] = ["Structure", "Formatting", "Writing"];

export const CATEGORY_BLURB: Record<AttributeCategory, string> = {
  Structure: "How your notes are organised.",
  Formatting: "What they look like on the page.",
  Writing: "How they read.",
};

/** Plain-English sentence for an attribute, with an honest fallback. */
export function describeAttribute(name: string, value: unknown): string {
  const meta = STYLE_ATTRIBUTES[name];
  if (!meta?.describe) return "";
  try {
    return meta.describe(value);
  } catch {
    return "";
  }
}

/** Confidence below this is still guesswork and shouldn't be shown as a precise figure. */
export const LEARNING_THRESHOLD = 0.5;

export function confidenceLabel(confidence: number, pinned?: boolean): string {
  if (pinned) return "Set by you";
  if (confidence >= 0.8) return "Confident";
  if (confidence >= LEARNING_THRESHOLD) return "Fairly sure";
  return "Still learning";
}
