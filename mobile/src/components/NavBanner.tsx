import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { Progress, instructionFor } from "../useJourneyProgress";
import { PlanOption } from "../api";
import { colors, radius, space, type } from "../theme";

/**
 * The one instruction that matters right now, at the top of the screen.
 *
 * While navigating, the itinerary is the wrong shape: a rider glancing at a
 * phone on a moving matatu needs one line, not a list. Everything else stays
 * available in the sheet below.
 */
export default function NavBanner({
  option,
  progress,
  onStop,
}: {
  option: PlanOption;
  progress: Progress;
  onStop: () => void;
}) {
  const leg = option.legs[progress.legIndex] ?? option.legs[0];
  const saccos = [...new Set(leg.terminals?.flatMap((t) => t.saccos) ?? [])];
  const { kicker, main, detail } = instructionFor(progress, leg.route_number, saccos);

  const urgent = progress.phase === "approaching_alight";
  const done = progress.phase === "arrived";

  return (
    <View style={[styles.wrap, urgent && styles.wrapUrgent, done && styles.wrapDone]}>
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <Text style={[styles.kicker, urgent && styles.kickerUrgent]}>{kicker}</Text>
          <Text style={styles.main}>{main}</Text>
          {detail ? <Text style={styles.detail}>{detail}</Text> : null}
        </View>
        <TouchableOpacity onPress={onStop} style={styles.stop} hitSlop={8}>
          <Text style={styles.stopText}>{done ? "Done" : "End"}</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.track}>
        <View style={[styles.fill, { width: `${Math.round(progress.fraction * 100)}%` }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: colors.brandDeep,
    paddingTop: space.xxl,
    paddingHorizontal: space.lg,
    paddingBottom: 0,
  },
  wrapUrgent: { backgroundColor: colors.accentDeep },
  wrapDone: { backgroundColor: colors.green },

  row: { flexDirection: "row", alignItems: "flex-start", paddingBottom: space.md },
  kicker: { ...type.micro, color: colors.textOnInkMuted },
  kickerUrgent: { color: "rgba(255,255,255,0.85)" },
  main: { ...type.hero, fontSize: 22, color: colors.textOnInk, marginTop: 3 },
  detail: { ...type.body, color: colors.textOnInkMuted, marginTop: 3 },

  stop: {
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.35)",
    borderRadius: radius.pill,
    paddingHorizontal: space.md,
    paddingVertical: 6,
    marginTop: space.sm,
  },
  stopText: { ...type.small, color: colors.textOnInk, fontWeight: "600" },

  track: { height: 3, backgroundColor: "rgba(255,255,255,0.18)" },
  fill: { height: 3, backgroundColor: colors.textOnInk },
});
