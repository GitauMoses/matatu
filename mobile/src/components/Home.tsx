import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert } from "react-native";
import { Ionicons, MaterialIcons, MaterialCommunityIcons } from "@expo/vector-icons";
import { colors, radius, space, type, shadow } from "../theme";

/**
 * Landing screen. The app used to open straight onto the map — this is the
 * thing every commuting app (Moovit, Citymapper, Google Maps) puts in front
 * of it instead: a hero header that establishes place and brand, a single
 * search bar, and quick paths back into a trip you've already taken. The map
 * is where you go to *look at* a route, not where you land to *think about*
 * one.
 */

const QUICK_DESTINATIONS = [
  { name: "Nairobi CBD", icon: "business" as const },
  { name: "Thika", icon: "car" as const },
  { name: "Juja", icon: "school" as const },
  { name: "Rongai", icon: "home" as const },
  { name: "Ngong", icon: "leaf" as const },
  { name: "Kitengela", icon: "storefront" as const },
];

function Skyline() {
  // No photo asset — an abstract skyline silhouette instead, built from
  // plain Views. Reads as deliberate rather than a placeholder.
  const bars = [34, 58, 40, 72, 50, 64, 38, 80, 46, 56, 32];
  return (
    <View style={styles.skyline} pointerEvents="none">
      {bars.map((h, i) => (
        <View key={i} style={[styles.skylineBar, { height: h }]} />
      ))}
    </View>
  );
}

export default function Home({
  originLabel,
  destQuery,
  onOpenSearch,
  favourites,
  onPickFavourite,
}: {
  originLabel: string;
  destQuery: string;
  onOpenSearch: () => void;
  favourites: { home: string | null; work: string | null };
  onPickFavourite: (which: "home" | "work") => void;
}) {
  return (
    <View style={styles.root}>
      <View style={styles.hero}>
        <Skyline />
        <View style={styles.heroTopBar}>
          <TouchableOpacity
            hitSlop={10}
            onPress={() => Alert.alert("Menu", "Coming soon.")}
          >
            <Ionicons name="menu" size={26} color="#fff" />
          </TouchableOpacity>
          <View style={styles.cityPill}>
            <Ionicons name="location" size={13} color="#fff" />
            <Text style={styles.cityText}>Nairobi</Text>
          </View>
        </View>

        <Text style={styles.heroTitle}>Know which one{"\n"}to board.</Text>
      </View>

      <TouchableOpacity style={styles.searchBar} onPress={onOpenSearch} activeOpacity={0.85}>
        <View style={styles.searchIcon}>
          <Ionicons name="search" size={18} color={colors.textMuted} />
        </View>
        <Text style={styles.searchPlaceholder} numberOfLines={1}>
          {destQuery || "Where do you want to go?"}
        </Text>
        <View style={styles.searchGo}>
          <Ionicons name="arrow-forward" size={18} color="#fff" />
        </View>
      </TouchableOpacity>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.sectionLabel}>QUICK DESTINATIONS</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.quickRow}
        >
          {QUICK_DESTINATIONS.map((d) => (
            <TouchableOpacity key={d.name} style={styles.quickChip} onPress={onOpenSearch}>
              <View style={styles.quickIcon}>
                <Ionicons name={d.icon} size={16} color={colors.brand} />
              </View>
              <Text style={styles.quickText}>{d.name}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <Text style={styles.sectionLabel}>FAVOURITES</Text>
        <View style={styles.favCard}>
          <TouchableOpacity style={styles.favRow} onPress={() => onPickFavourite("home")}>
            <View style={[styles.favIcon, { backgroundColor: colors.brandSoft }]}>
              <Ionicons name="home" size={17} color={colors.brand} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.favTitle}>Home</Text>
              <Text style={styles.favSub} numberOfLines={1}>
                {favourites.home ?? "Tap to set"}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={colors.textFaint} />
          </TouchableOpacity>
          <View style={styles.favDivider} />
          <TouchableOpacity style={styles.favRow} onPress={() => onPickFavourite("work")}>
            <View style={[styles.favIcon, { backgroundColor: colors.amberSoft }]}>
              <MaterialCommunityIcons name="briefcase" size={17} color={colors.amber} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.favTitle}>Work</Text>
              <Text style={styles.favSub} numberOfLines={1}>
                {favourites.work ?? "Tap to set"}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={colors.textFaint} />
          </TouchableOpacity>
        </View>

        <Text style={styles.footerNote}>134 routes · 2,485 stages · Nairobi</Text>
      </ScrollView>

      <View style={styles.tabBar}>
        <View style={styles.tabItem}>
          <MaterialIcons name="directions" size={22} color={colors.brand} />
          <Text style={[styles.tabLabel, { color: colors.brand }]}>Directions</Text>
        </View>
        <TouchableOpacity
          style={styles.tabItem}
          onPress={() => Alert.alert("Stations", "Coming soon.")}
        >
          <Ionicons name="location-outline" size={22} color={colors.textFaint} />
          <Text style={styles.tabLabel}>Stations</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.tabItem}
          onPress={() => Alert.alert("Lines", "Coming soon.")}
        >
          <MaterialCommunityIcons name="road-variant" size={22} color={colors.textFaint} />
          <Text style={styles.tabLabel}>Lines</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },

  hero: {
    height: 220,
    backgroundColor: colors.brandDeep,
    paddingTop: 46,
    paddingHorizontal: space.lg,
    overflow: "hidden",
  },
  skyline: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 8,
    paddingHorizontal: space.lg,
    opacity: 0.22,
  },
  skylineBar: { flex: 1, backgroundColor: "#fff", borderTopLeftRadius: 3, borderTopRightRadius: 3 },

  heroTopBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  cityPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: "rgba(255,255,255,0.16)",
    borderRadius: radius.pill,
    paddingHorizontal: space.md,
    paddingVertical: 6,
  },
  cityText: { ...type.small, color: "#fff", fontWeight: "700" },

  heroTitle: {
    color: "#fff",
    fontSize: 26,
    fontWeight: "800",
    letterSpacing: -0.5,
    marginTop: space.xl,
    lineHeight: 32,
  },

  searchBar: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: space.lg,
    marginTop: -26,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: space.sm,
    ...shadow.float,
  },
  searchIcon: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: "center",
    justifyContent: "center",
  },
  searchPlaceholder: { flex: 1, ...type.body, fontSize: 15, color: colors.textMuted },
  searchGo: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.brand,
    alignItems: "center",
    justifyContent: "center",
  },

  content: { paddingTop: space.xl, paddingBottom: space.lg },
  sectionLabel: {
    ...type.micro,
    color: colors.textFaint,
    paddingHorizontal: space.lg,
    marginBottom: space.sm,
  },

  quickRow: { paddingHorizontal: space.lg, gap: space.sm, paddingBottom: space.xl },
  quickChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.surface,
    borderRadius: radius.pill,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    ...shadow.card,
  },
  quickIcon: { width: 20, alignItems: "center" },
  quickText: { ...type.small, fontSize: 13, color: colors.text, fontWeight: "700" },

  favCard: {
    marginHorizontal: space.lg,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    ...shadow.card,
  },
  favRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    padding: space.md,
  },
  favIcon: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: "center",
    justifyContent: "center",
  },
  favTitle: { ...type.title, color: colors.text },
  favSub: { ...type.small, color: colors.textFaint, marginTop: 1 },
  favDivider: { height: 1, backgroundColor: colors.line, marginLeft: 66 },

  footerNote: {
    ...type.small,
    fontSize: 11.5,
    color: colors.textFaint,
    textAlign: "center",
    marginTop: space.xxl,
  },

  tabBar: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderTopColor: colors.line,
    backgroundColor: colors.surface,
    paddingTop: space.sm,
    paddingBottom: space.lg,
  },
  tabItem: { flex: 1, alignItems: "center", gap: 3 },
  tabLabel: { ...type.small, fontSize: 11, color: colors.textFaint, fontWeight: "700" },
});
