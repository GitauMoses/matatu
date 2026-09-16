import React, { useMemo, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, FlatList, Platform } from "react-native";
import { Ionicons, MaterialIcons } from "@expo/vector-icons";
import { PlanOption } from "../api";
import { colors, radius, space, type } from "../theme";

type SortMode = "fastest" | "fewest";

/**
 * The routes list, as its own screen rather than a strip of chips.
 *
 * Every commuting app that gets this right shows the choice before the map:
 * a handful of full-width cards, the best one marked, route numbers chained
 * with chevrons so a two-leg trip reads as a sequence rather than a
 * side-by-side comparison. Committing to an option is what opens the map.
 */

function fmtKm(km: number) {
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
}

function RouteBadges({ option }: { option: PlanOption }) {
  return (
    <View style={styles.badgeRow}>
      {option.legs.map((leg, i) => (
        <React.Fragment key={i}>
          {i > 0 && <Ionicons name="chevron-forward" size={14} color={colors.textFaint} />}
          <View style={styles.badge}>
            <Ionicons name="bus" size={11} color="#fff" />
            <Text style={styles.badgeText}>{leg.route_number}</Text>
          </View>
        </React.Fragment>
      ))}
    </View>
  );
}

function Card({
  option,
  recommended,
  onPress,
}: {
  option: PlanOption;
  recommended: boolean;
  onPress: () => void;
}) {
  const totalWalk =
    option.walk_to_board_km + option.walk_from_alight_km + (option.transfer_walk_km ?? 0);

  return (
    <TouchableOpacity
      style={[styles.card, recommended && styles.cardRecommended]}
      onPress={onPress}
      activeOpacity={0.75}
    >
      {recommended && (
        <View style={styles.recommendedPill}>
          <Ionicons name="sparkles" size={11} color={colors.brand} />
          <Text style={styles.recommendedText}>BEST MATCH</Text>
        </View>
      )}

      <View style={styles.cardTop}>
        <Text style={styles.time}>
          {option.estimated_minutes}
          <Text style={styles.timeUnit}> min</Text>
        </Text>
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

      <RouteBadges option={option} />

      <View style={styles.boardRow}>
        <Ionicons name="location" size={13} color={colors.textFaint} />
        <Text style={styles.board} numberOfLines={1}>
          Board at {option.legs[0].board_stop.name}
        </Text>
        <Ionicons name="chevron-forward" size={16} color={colors.textFaint} style={styles.boardChevron} />
      </View>
    </TouchableOpacity>
  );
}

export default function RouteOptions({
  originLabel,
  destLabel,
  options,
  onBack,
  onSelect,
}: {
  originLabel: string;
  destLabel: string;
  options: PlanOption[];
  onBack: () => void;
  onSelect: (index: number) => void;
}) {
  const [sort, setSort] = useState<SortMode>("fastest");

  // Original indices are kept so onSelect still points at the right option
  // in the backend's own ranking, regardless of how the list is displayed.
  const ordered = useMemo(() => {
    const withIndex = options.map((o, i) => ({ o, i }));
    if (sort === "fewest") {
      withIndex.sort((a, b) => a.o.transfers - b.o.transfers || a.o.estimated_minutes - b.o.estimated_minutes);
    }
    return withIndex;
  }, [options, sort]);

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} hitSlop={12} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={20} color={colors.brand} />
        </TouchableOpacity>
        <View style={styles.routeFields}>
          <View style={styles.fieldRow}>
            <View style={styles.fieldDot} />
            <Text style={styles.fieldText} numberOfLines={1}>{originLabel}</Text>
          </View>
          <View style={styles.fieldDivider} />
          <View style={styles.fieldRow}>
            <Ionicons name="location" size={12} color={colors.accent} />
            <Text style={styles.fieldText} numberOfLines={1}>{destLabel}</Text>
          </View>
        </View>
      </View>

      <View style={styles.sortRow}>
        <TouchableOpacity
          style={[styles.sortChip, sort === "fastest" && styles.sortChipActive]}
          onPress={() => setSort("fastest")}
        >
          <Ionicons name="flash" size={13} color={sort === "fastest" ? "#fff" : colors.textMuted} />
          <Text style={[styles.sortChipText, sort === "fastest" && styles.sortChipTextActive]}>
            Fastest
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.sortChip, sort === "fewest" && styles.sortChipActive]}
          onPress={() => setSort("fewest")}
        >
          <MaterialIcons name="swap-horiz" size={14} color={sort === "fewest" ? "#fff" : colors.textMuted} />
          <Text style={[styles.sortChipText, sort === "fewest" && styles.sortChipTextActive]}>
            Fewest transfers
          </Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={ordered}
        keyExtractor={({ i }) => String(i)}
        contentContainerStyle={styles.list}
        renderItem={({ item: { o, i } }) => (
          <Card option={o} recommended={i === 0} onPress={() => onSelect(i)} />
        )}
      />
    </View>
  );
}

const shadow = Platform.select({
  android: { elevation: 3 },
  default: {
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },
});

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },

  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingTop: 54,
    paddingHorizontal: space.lg,
    paddingBottom: space.md,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.brandSoft,
    alignItems: "center",
    justifyContent: "center",
  },

  routeFields: { flex: 1, gap: 6 },
  fieldRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  fieldDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: colors.brand,
  },
  fieldText: { ...type.title, fontSize: 14, color: colors.text, flex: 1 },
  fieldDivider: { height: 1, backgroundColor: colors.line, marginLeft: 4, width: 18 },

  sortRow: {
    flexDirection: "row",
    gap: space.sm,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  sortChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: colors.canvas,
    borderRadius: radius.pill,
    paddingHorizontal: space.md,
    paddingVertical: 7,
  },
  sortChipActive: { backgroundColor: colors.brand },
  sortChipText: { ...type.small, fontSize: 12.5, color: colors.textMuted, fontWeight: "700" },
  sortChipTextActive: { color: "#fff" },

  list: { padding: space.lg, gap: space.md },

  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: space.lg,
    marginBottom: space.md,
    borderWidth: 1.5,
    borderColor: "transparent",
    ...shadow,
  },
  cardRecommended: {
    borderColor: colors.brand,
    backgroundColor: colors.brandSoft,
  },
  recommendedPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    alignSelf: "flex-start",
    backgroundColor: colors.surface,
    borderRadius: radius.sm,
    paddingHorizontal: space.sm,
    paddingVertical: 3,
    marginBottom: space.sm,
  },
  recommendedText: { ...type.micro, fontSize: 10, color: colors.brand },

  cardTop: { flexDirection: "row", alignItems: "center", gap: space.sm, marginBottom: space.md },
  time: { fontSize: 26, fontWeight: "800", color: colors.text, letterSpacing: -0.6 },
  timeUnit: { fontSize: 14, fontWeight: "600", color: colors.textMuted },
  metaChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.canvas,
    borderRadius: radius.pill,
    paddingHorizontal: space.sm,
    paddingVertical: 4,
    marginLeft: "auto",
  },
  metaText: { ...type.small, fontSize: 12, color: colors.textMuted },

  badgeRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: space.sm },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.brand,
    borderRadius: radius.sm,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  badgeText: { ...type.micro, fontSize: 11, color: "#fff" },

  boardRow: { flexDirection: "row", alignItems: "center", gap: 5 },
  board: { ...type.small, color: colors.textFaint, flex: 1 },
  boardChevron: { marginLeft: "auto" },
});
