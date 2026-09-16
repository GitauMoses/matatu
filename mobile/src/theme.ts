/**
 * Visual language, v2.
 *
 * Nairobi's matatus are themselves a design statement — hand-painted graffiti,
 * neon underglow, loud sound systems. A transit app for this city reading as
 * a grey corporate dashboard is a missed opportunity, not a safe choice. This
 * palette leans into that energy deliberately: a confident violet as the
 * brand color (used for structure — selection, the route line, primary
 * actions), a hot coral for the one instruction that matters right now
 * (board here, get off here), and a clean cool-white canvas so the color
 * reads as intentional rather than noisy. Still one accent per job — the
 * rule that made the first version calm is kept, only the colors changed.
 */

export const colors = {
  /** Brand — structure, selection, the route line, primary buttons. */
  brand: "#5B45E0",
  brandDeep: "#4432B8",
  brandSoft: "#EFECFD",

  /** Chrome. */
  ink: "#13121A",
  ink2: "#201E2B",
  ink3: "#34303F",

  surface: "#FFFFFF",
  /** Cool, faintly violet white — reads calmer than pure #FFF, warmer than grey. */
  canvas: "#F6F5FB",
  line: "#E9E7F3",

  text: "#15131E",
  textMuted: "#726E82",
  textFaint: "#A7A3B5",
  textOnInk: "#FFFFFF",
  textOnInkMuted: "#9490A5",

  /** The one "act on this" color — boarding, alighting, alerts. */
  accent: "#FF5D5D",
  accentDeep: "#E63E4E",
  accentSoft: "#FFEBEC",

  /** Walking is deliberately quiet — it is the part you don't ride. */
  walk: "#9A96AA",

  green: "#0EA36C",
  greenSoft: "#E4F8EF",

  amber: "#F5A623",
  amberSoft: "#FEF3DD",
};

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 28 };

export const radius = { sm: 8, md: 14, lg: 22, xl: 28, pill: 999 };

export const type = {
  display: { fontSize: 26, fontWeight: "800" as const, letterSpacing: -0.6 },
  hero: { fontSize: 19, fontWeight: "800" as const, letterSpacing: -0.3 },
  title: { fontSize: 15, fontWeight: "700" as const, letterSpacing: -0.1 },
  body: { fontSize: 14, fontWeight: "500" as const },
  small: { fontSize: 12.5, fontWeight: "500" as const },
  micro: { fontSize: 10.5, fontWeight: "700" as const, letterSpacing: 0.6 },
};

export const shadow = {
  card: {
    shadowColor: "#2B1F6B",
    shadowOpacity: 0.1,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 5,
  },
  float: {
    shadowColor: "#2B1F6B",
    shadowOpacity: 0.18,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
};

/** Every ridden leg is the same colour. Distinction comes from the itinerary. */
export const ROUTE_LINE = colors.brand;
