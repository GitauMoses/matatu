import { useMemo } from "react";
import { PlanOption } from "./api";

/**
 * Works out where you are in the journey from your live position.
 *
 * There is no vehicle feed to ask, so the phase is inferred from geometry:
 * how far you are along the route line, and how close to each boarding and
 * alighting point. That is enough to say "walk to the stage", "you're on the
 * matatu", or "get off next" without any live transit data.
 */

export type Phase =
  | "walk_to_board"
  | "riding"
  | "approaching_alight"
  | "changing"
  | "walk_to_destination"
  | "arrived";

export type Progress = {
  phase: Phase;
  legIndex: number;
  /** Metres to the next thing that matters (the stage, or your destination). */
  metresToNext: number;
  /** Name of that next thing. */
  nextName: string;
  /** 0–1 along the whole journey, for the progress bar. */
  fraction: number;
  /** Stages left on the current matatu, when riding. */
  stagesRemaining: number;
};

export type Coords = { lat: number; lon: number };

const R = 6371000;

export function metresBetween(a: Coords, b: Coords): number {
  const p1 = (a.lat * Math.PI) / 180;
  const p2 = (b.lat * Math.PI) / 180;
  const dp = ((b.lat - a.lat) * Math.PI) / 180;
  const dl = ((b.lon - a.lon) * Math.PI) / 180;
  const x =
    Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}

/** How close counts as "you're there". GPS in town is rarely better than this. */
const ARRIVED_M = 45;
/** Within this of the route line, treat the rider as aboard. */
const ON_ROUTE_M = 90;
/** Start warning about the next stop this far out. */
const APPROACHING_M = 350;

function nearestOnLine(pos: Coords, line: [number, number][]) {
  let best = Infinity;
  let idx = 0;
  for (let i = 0; i < line.length; i++) {
    const d = metresBetween(pos, { lat: line[i][1], lon: line[i][0] });
    if (d < best) {
      best = d;
      idx = i;
    }
  }
  return { distance: best, index: idx };
}

export function computeProgress(
  option: PlanOption,
  pos: Coords,
  destination: Coords
): Progress {
  const legs = option.legs;
  const lastLeg = legs[legs.length - 1];

  // Arrived?
  const toDest = metresBetween(pos, destination);
  if (toDest <= ARRIVED_M) {
    return {
      phase: "arrived",
      legIndex: legs.length - 1,
      metresToNext: 0,
      nextName: "your destination",
      fraction: 1,
      stagesRemaining: 0,
    };
  }

  // Which leg are we closest to being on?
  let legIndex = 0;
  let onLine = { distance: Infinity, index: 0 };
  legs.forEach((leg, i) => {
    if (!leg.geometry?.length) return;
    const n = nearestOnLine(pos, leg.geometry);
    if (n.distance < onLine.distance) {
      onLine = n;
      legIndex = i;
    }
  });

  const leg = legs[legIndex];
  const board = { lat: leg.board_stop.lat, lon: leg.board_stop.lon };
  const alight = { lat: leg.alight_stop.lat, lon: leg.alight_stop.lon };
  const toBoard = metresBetween(pos, board);
  const toAlight = metresBetween(pos, alight);

  // Past the last alighting point → walking the final stretch.
  const finalAlight = {
    lat: lastLeg.alight_stop.lat,
    lon: lastLeg.alight_stop.lon,
  };
  if (
    metresBetween(pos, finalAlight) <= ARRIVED_M ||
    (toDest < metresBetween(finalAlight, destination) && onLine.distance > ON_ROUTE_M)
  ) {
    return {
      phase: "walk_to_destination",
      legIndex: legs.length - 1,
      metresToNext: Math.round(toDest),
      nextName: "your destination",
      fraction: 0.95,
      stagesRemaining: 0,
    };
  }

  // Not yet at the boarding stage, and not on the line → still walking to it.
  if (toBoard > ARRIVED_M && onLine.distance > ON_ROUTE_M) {
    const changing = legIndex > 0;
    return {
      phase: changing ? "changing" : "walk_to_board",
      legIndex,
      metresToNext: Math.round(toBoard),
      nextName: leg.board_stop.name,
      fraction: legIndex / Math.max(legs.length, 1) * 0.5,
      stagesRemaining: leg.num_stages,
    };
  }

  // On the line, or at the stage → riding.
  const total = leg.geometry?.length || 1;
  const along = onLine.index / total;
  const stagesRemaining = Math.max(0, Math.round(leg.num_stages * (1 - along)));

  return {
    phase: toAlight <= APPROACHING_M ? "approaching_alight" : "riding",
    legIndex,
    metresToNext: Math.round(toAlight),
    nextName: leg.alight_stop.name,
    fraction: 0.1 + (legIndex + along) / Math.max(legs.length, 1) * 0.85,
    stagesRemaining,
  };
}

export function useJourneyProgress(
  option: PlanOption | null,
  pos: Coords | null,
  destination: Coords | null
): Progress | null {
  return useMemo(() => {
    if (!option || !pos || !destination) return null;
    return computeProgress(option, pos, destination);
  }, [option, pos, destination]);
}

/** The line to speak at the top of the screen. */
export function instructionFor(p: Progress, routeNumber: string, saccos: string[]): {
  kicker: string;
  main: string;
  detail: string;
} {
  const dist =
    p.metresToNext >= 1000
      ? `${(p.metresToNext / 1000).toFixed(1)} km`
      : `${p.metresToNext} m`;

  switch (p.phase) {
    case "walk_to_board":
      return {
        kicker: "WALK",
        main: `${dist} to ${p.nextName}`,
        detail: saccos.length ? `Look for ${saccos.slice(0, 2).join(" or ")}` : `Take ${routeNumber}`,
      };
    case "changing":
      return {
        kicker: "CHANGE MATATU",
        main: `${dist} to ${p.nextName}`,
        detail: saccos.length ? `Look for ${saccos.slice(0, 2).join(" or ")}` : `Take ${routeNumber}`,
      };
    case "riding":
      return {
        kicker: `ON ${routeNumber}`,
        main: `${p.stagesRemaining} stage${p.stagesRemaining === 1 ? "" : "s"} to go`,
        detail: `Get off at ${p.nextName}`,
      };
    case "approaching_alight":
      return {
        kicker: "GET READY",
        main: `${p.nextName} in ${dist}`,
        detail: "Tell the conductor now",
      };
    case "walk_to_destination":
      return { kicker: "WALK", main: `${dist} to go`, detail: "Almost there" };
    case "arrived":
      return { kicker: "ARRIVED", main: "You're here", detail: "" };
  }
}
