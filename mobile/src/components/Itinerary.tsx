import React, { useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from "react-native";
import { Ionicons, MaterialIcons } from "@expo/vector-icons";
import { PlanOption, PlanLeg } from "../api";
import { colors, radius, space, type } from "../theme";

/**
 * The journey as a timeline, the way every mapping app shows one: an icon per
 * step down the left, the instruction beside it.
 *
 * Riders identify a matatu by the sacco painted on it, not by a route number,
 * so where to find it and who runs it lead. The route number is a badge.
 */

const SACCOS_SHOWN = 2;

function fmtKm(km: number) {
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
}

function Step({
  icon,
  tint,
  dashed,
  last,
  children,
}: {
  icon: React.ReactNode;
  tint: string;
  dashed?: boolean;
  last?: boolean;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.step}>
      <View style={styles.rail}>
        <View style={[styles.bubble, { backgroundColor: tint }]}>{icon}</View>
        {!last &&
          (dashed ? (
            <View style={styles.dashRail}>
              {[0, 1, 2, 3].map((i) => (
                <View key={i} style={styles.dash} />
              ))}
            </View>
          ) : (
            <View style={[styles.solidRail, { backgroundColor: tint }]} />
          ))}
      </View>
      <View style={styles.body}>{children}</View>
    </View>
  );
}

function Ride({ leg }: { leg: PlanLeg }) {
  const [showAll, setShowAll] = useState(false);
  const [showStages, setShowStages] = useState(false);
  const saccos = [...new Set(leg.terminals?.flatMap((t) => t.saccos) ?? [])];
  const shown = showAll ? saccos : saccos.slice(0, SACCOS_SHOWN);
  const hidden = saccos.length - shown.length;
  const passing = leg.stops.slice(1, -1).map((s) => s.name);

  return (
    <>
      <Text style={styles.kicker}>BOARD AT</Text>
      <Text style={styles.place}>{leg.board_stop.name}</Text>

      <View style={styles.badgeRow}>
        <View style={styles.routeBadge}>
          <Ionicons name="bus" size={12} color="#fff" />
          <Text style={styles.routeBadgeText}>{leg.route_number}</Text>
        </View>
        <Text style={styles.toward} numberOfLines={1}>
          to {leg.headsign}
        </Text>
      </View>

      {saccos.length > 0 ? (
        <View style={styles.saccoCard}>
          <Text style={styles.saccoLabel}>LOOK FOR</Text>
          <Text style={styles.saccoNames}>{shown.join("  ·  ")}</Text>
          {hidden > 0 && (
            <TouchableOpacity onPress={() => setShowAll(true)}>
              <Text style={styles.link}>+{hidden} more saccos</Text>
            </TouchableOpacity>
          )}
        </View>
      ) : (
        leg.likely_saccos?.length > 0 && (
          <View style={styles.likelyCard}>
            <Text style={styles.likelyLabel}>COMMONLY THIS SACCO (UNCONFIRMED)</Text>
            <Text style={styles.likelyNames}>{leg.likely_saccos.join("  ·  ")}</Text>
          </View>
        )
      )}

      {leg.terminals?.length > 1 && (
        <Text style={styles.alsoAt}>
          Also boards at {leg.terminals.slice(1).map((t) => t.name).join(" · ")}
        </Text>
      )}

      {passing.length > 0 && (
        <TouchableOpacity style={styles.stagesBtn} onPress={() => setShowStages((v) => !v)}>
          <Text style={styles.stagesBtnText}>{leg.num_stages} stages</Text>
          <MaterialIcons
            name={showStages ? "expand-less" : "expand-more"}
            size={16}
            color={colors.textMuted}
          />
        </TouchableOpacity>
      )}
      {showStages && <Text style={styles.passing}>{passing.join("  ·  ")}</Text>}
    </>
  );
}

export function ItinerarySummary({ option }: { option: PlanOption }) {
  const first = option.legs[0];
  const saccos = [...new Set(first.terminals?.flatMap((t) => t.saccos) ?? [])];
  return (
    <View style={styles.peek}>
      <View style={styles.peekIcon}>
        <Ionicons name="bus" size={18} color="#fff" />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.peekTitle} numberOfLines={1}>
          {saccos[0] ?? `Matatu to ${first.headsign}`}
        </Text>
        <Text style={styles.peekSub}>
          {option.legs.map((l) => l.route_number).join(" → ")} · {option.estimated_minutes} min
        </Text>
      </View>
      <Text style={styles.peekTime}>{option.estimated_minutes}<Text style={styles.peekTimeUnit}> min</Text></Text>
    </View>
  );
}

export default function Itinerary({ option }: { option: PlanOption }) {
  const totalWalk =
    option.walk_to_board_km + option.walk_from_alight_km + (option.transfer_walk_km ?? 0);
  const endsWithWalk = option.walk_from_alight_km > 0.02;

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.head}>
        <Text style={styles.headTime}>{option.estimated_minutes}<Text style={styles.headUnit}> min</Text></Text>
        <View style={styles.headMeta}>
          <View style={styles.metaChip}>
            <Ionicons name="walk" size={13} color={colors.textMuted} />
            <Text style={styles.metaText}>{fmtKm(totalWalk)}</Text>
          </View>
          <View style={styles.metaChip}>
            <MaterialIcons name="swap-horiz" size={14} color={colors.textMuted} />
            <Text style={styles.metaText}>
              {option.transfers === 0 ? "direct" : `${option.transfers} change`}
            </Text>
          </View>
        </View>
      </View>

      {option.walk_to_board_km > 0.02 && (
        <Step
          dashed
          tint={colors.canvas}
          icon={<Ionicons name="walk" size={16} color={colors.textMuted} />}
        >
          <Text style={styles.walkMain}>Walk {fmtKm(option.walk_to_board_km)}</Text>
          <Text style={styles.walkSub}>to {option.legs[0].board_stop.name}</Text>
        </Step>
      )}

      {option.legs.map((leg, i) => (
        <View key={i}>
          {i > 0 && (
            <Step
              dashed
              tint={colors.canvas}
              icon={<Ionicons name="walk" size={16} color={colors.textMuted} />}
            >
              <Text style={styles.walkMain}>
                {(option.transfer_walk_km ?? 0) > 0.02
                  ? `Walk ${fmtKm(option.transfer_walk_km!)}`
                  : "Change matatu"}
              </Text>
              <Text style={styles.walkSub}>to {leg.board_stop.name}</Text>
            </Step>
          )}

          <Step tint={colors.brand} icon={<Ionicons name="bus" size={16} color="#fff" />}>
            <Ride leg={leg} />
          </Step>

          <Step
            tint={colors.accent}
            icon={<MaterialIcons name="place" size={16} color="#fff" />}
            last={i === option.legs.length - 1 && !endsWithWalk}
            dashed
          >
            <Text style={styles.kicker}>GET OFF AT</Text>
            <Text style={styles.place}>{leg.alight_stop.name}</Text>
            {leg.alight_on_request && (
              <View style={styles.requestPill}>
                <MaterialIcons name="campaign" size={13} color={colors.accent} />
                <Text style={styles.requestText}>Ask the conductor to drop you</Text>
              </View>
            )}
          </Step>
        </View>
      ))}

      {endsWithWalk && (
        <Step
          last
          tint={colors.green}
          icon={<MaterialIcons name="flag" size={16} color="#fff" />}
        >
          <Text style={styles.walkMain}>Walk {fmtKm(option.walk_from_alight_km)}</Text>
          <Text style={styles.walkSub}>to your destination</Text>
        </Step>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  content: { paddingHorizontal: space.lg, paddingBottom: space.lg },

  head: { flexDirection: "row", alignItems: "center", marginBottom: space.lg, gap: space.md },
  headTime: { fontSize: 30, fontWeight: "800", color: colors.text, letterSpacing: -0.8 },
  headUnit: { fontSize: 15, fontWeight: "600", color: colors.textMuted },
  headMeta: { flexDirection: "row", gap: space.sm, flex: 1 },
  metaChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.canvas,
    borderRadius: radius.pill,
    paddingHorizontal: space.sm,
    paddingVertical: 4,
  },
  metaText: { ...type.small, fontSize: 12, color: colors.textMuted },

  step: { flexDirection: "row", gap: space.md },
  rail: { width: 32, alignItems: "center" },
  bubble: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center" },
  solidRail: { flex: 1, width: 3, borderRadius: 2, marginVertical: 4 },
  dashRail: { flex: 1, alignItems: "center", justifyContent: "space-evenly", paddingVertical: 4, minHeight: 20 },
  dash: { width: 3, height: 4, borderRadius: 2, backgroundColor: colors.line },
  body: { flex: 1, paddingBottom: space.lg },

  kicker: { ...type.micro, color: colors.textFaint },
  place: { fontSize: 17, fontWeight: "700", color: colors.text, marginTop: 2, letterSpacing: -0.2 },

  badgeRow: { flexDirection: "row", alignItems: "center", gap: space.sm, marginTop: space.sm },
  routeBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.brand,
    borderRadius: radius.sm,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  routeBadgeText: { ...type.micro, fontSize: 11, color: "#fff" },
  toward: { ...type.small, color: colors.textMuted, flexShrink: 1 },

  saccoCard: {
    marginTop: space.md,
    backgroundColor: colors.brandSoft,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    borderLeftWidth: 3,
    borderLeftColor: colors.brand,
  },
  saccoLabel: { ...type.micro, fontSize: 9.5, color: colors.brandDeep },
  saccoNames: { fontSize: 15, fontWeight: "800", color: colors.brandDeep, marginTop: 2 },
  link: { ...type.small, fontSize: 11.5, color: colors.textMuted, marginTop: 4 },

  likelyCard: {
    marginTop: space.md,
    backgroundColor: colors.canvas,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    borderStyle: "dashed",
    borderWidth: 1,
    borderColor: colors.line,
  },
  likelyLabel: { ...type.micro, fontSize: 9, color: colors.textFaint },
  likelyNames: { fontSize: 14, fontWeight: "600", color: colors.textMuted, marginTop: 2 },
  alsoAt: { ...type.small, color: colors.textFaint, marginTop: space.sm },

  stagesBtn: { flexDirection: "row", alignItems: "center", gap: 2, marginTop: space.md },
  stagesBtnText: { ...type.small, fontSize: 12, color: colors.textMuted, fontWeight: "600" },
  passing: { ...type.small, fontSize: 11.5, color: colors.textFaint, marginTop: space.xs, lineHeight: 17 },

  walkMain: { fontSize: 15, fontWeight: "600", color: colors.text },
  walkSub: { ...type.small, color: colors.textMuted, marginTop: 1 },

  requestPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    alignSelf: "flex-start",
    backgroundColor: colors.accentSoft,
    borderRadius: radius.sm,
    paddingHorizontal: space.sm,
    paddingVertical: 4,
    marginTop: space.sm,
  },
  requestText: { ...type.small, fontSize: 11.5, color: colors.accent, fontWeight: "600" },

  peek: { flexDirection: "row", alignItems: "center", gap: space.md, paddingHorizontal: space.lg },
  peekIcon: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: colors.brand, alignItems: "center", justifyContent: "center",
  },
  peekTitle: { fontSize: 16, fontWeight: "700", color: colors.text },
  peekSub: { ...type.small, color: colors.textMuted, marginTop: 1 },
  peekTime: { fontSize: 22, fontWeight: "800", color: colors.text, letterSpacing: -0.5 },
  peekTimeUnit: { fontSize: 12, fontWeight: "600", color: colors.textMuted },
});
