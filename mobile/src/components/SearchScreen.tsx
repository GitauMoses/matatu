import React from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { Ionicons, MaterialIcons } from "@expo/vector-icons";
import { SearchResult } from "../api";
import { colors, radius, space, type, shadow } from "../theme";

/**
 * Full-screen search, not a dropdown over the map. This is its own step in
 * the flow, the way it is in every app used as a reference: back arrow,
 * a single input, results grouped by what they are (a real place vs. a
 * matatu stop) rather than mixed into one list.
 */

function fmtKm(km: number) {
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
}

export default function SearchScreen({
  query,
  onChangeQuery,
  onBack,
  onUseLocation,
  suggestions,
  searching,
  loading,
  onPick,
  fieldLabel,
}: {
  query: string;
  onChangeQuery: (t: string) => void;
  onBack: () => void;
  onUseLocation: () => void;
  suggestions: SearchResult[];
  searching: boolean;
  loading: boolean;
  onPick: (s: SearchResult) => void;
  fieldLabel: string;
}) {
  const places = suggestions.filter((s) => s.source === "place");
  const stops = suggestions.filter((s) => s.source === "stage");

  const sections: { title: string; data: SearchResult[] }[] = [
    ...(places.length ? [{ title: "Places", data: places }] : []),
    ...(stops.length ? [{ title: "Stops", data: stops }] : []),
  ];

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} hitSlop={12} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={20} color={colors.brand} />
        </TouchableOpacity>
        <View style={styles.inputWrap}>
          <Text style={styles.inputLabel}>{fieldLabel}</Text>
          <TextInput
            style={styles.input}
            placeholder="Search a place or matatu stop"
            placeholderTextColor={colors.textFaint}
            value={query}
            onChangeText={onChangeQuery}
            autoFocus
            autoCorrect={false}
          />
        </View>
        {query.length > 0 && (
          <TouchableOpacity onPress={() => onChangeQuery("")} hitSlop={12}>
            <Ionicons name="close-circle" size={20} color={colors.textFaint} />
          </TouchableOpacity>
        )}
      </View>

      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator color={colors.brand} />
          <Text style={styles.centeredText}>Finding your matatu…</Text>
        </View>
      ) : (
        <FlatList
          data={sections}
          keyExtractor={(s) => s.title}
          keyboardShouldPersistTaps="handled"
          ListHeaderComponent={
            <TouchableOpacity style={styles.row} onPress={onUseLocation}>
              <View style={[styles.iconBubble, { backgroundColor: colors.brand }]}>
                <MaterialIcons name="my-location" size={16} color="#fff" />
              </View>
              <Text style={styles.rowTitleAccent}>Use my current location</Text>
            </TouchableOpacity>
          }
          renderItem={({ item: section }) => (
            <View>
              <Text style={styles.sectionLabel}>{section.title}</Text>
              {section.data.map((item) => {
                const isStage = item.source === "stage";
                return (
                  <TouchableOpacity key={item.id} style={styles.row} onPress={() => onPick(item)}>
                    <View
                      style={[
                        styles.iconBubble,
                        { backgroundColor: isStage ? colors.brand : colors.brandSoft },
                      ]}
                    >
                      <Ionicons
                        name={isStage ? "bus" : "location-outline"}
                        size={16}
                        color={isStage ? "#fff" : colors.brand}
                      />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.rowTitle} numberOfLines={1}>
                        {item.name}
                      </Text>
                      {item.context ? (
                        <Text style={styles.rowSub} numberOfLines={1}>
                          {item.context}
                        </Text>
                      ) : null}
                      {item.source === "place" && item.nearest_stage && (
                        <View style={styles.nearestRow}>
                          <Ionicons
                            name={item.reachable ? "walk" : "alert-circle-outline"}
                            size={12}
                            color={item.reachable ? colors.green : colors.accent}
                          />
                          <Text
                            style={item.reachable ? styles.reach : styles.unreach}
                            numberOfLines={1}
                          >
                            {item.reachable
                              ? `${fmtKm(item.nearest_stage.walk_km)} to ${item.nearest_stage.name}`
                              : `no matatu within ${fmtKm(item.nearest_stage.walk_km)}`}
                          </Text>
                        </View>
                      )}
                    </View>
                    <Ionicons name="arrow-up-outline" style={styles.insertIcon} size={16} color={colors.textFaint} />
                  </TouchableOpacity>
                );
              })}
            </View>
          )}
          ListEmptyComponent={
            searching ? (
              <View style={styles.searching}>
                <ActivityIndicator size="small" color={colors.textMuted} />
                <Text style={styles.searchingText}>Searching…</Text>
              </View>
            ) : query.length >= 2 ? (
              <View style={styles.centered}>
                <Text style={styles.centeredText}>Nothing found for "{query}"</Text>
              </View>
            ) : null
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.surface },

  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingTop: 54,
    paddingHorizontal: space.lg,
    paddingBottom: space.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
    ...shadow.card,
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.brandSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  inputWrap: { flex: 1 },
  inputLabel: { ...type.micro, fontSize: 9.5, color: colors.textFaint },
  input: { ...type.body, fontSize: 16, color: colors.text, fontWeight: "700", paddingVertical: 2 },

  sectionLabel: {
    ...type.micro,
    color: colors.textFaint,
    paddingHorizontal: space.lg,
    paddingTop: space.md,
    paddingBottom: space.xs,
  },

  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
  },
  iconBubble: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: "center",
    justifyContent: "center",
  },
  rowTitle: { ...type.title, color: colors.text },
  rowTitleAccent: { ...type.title, color: colors.brand },
  rowSub: { ...type.small, color: colors.textFaint, marginTop: 1 },
  nearestRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 3 },
  reach: { ...type.small, fontSize: 11.5, color: colors.green },
  unreach: { ...type.small, fontSize: 11.5, color: colors.accent },
  insertIcon: { transform: [{ rotate: "45deg" }] },

  searching: { flexDirection: "row", alignItems: "center", gap: space.sm, padding: space.lg },
  searchingText: { ...type.small, color: colors.textMuted },

  centered: { alignItems: "center", justifyContent: "center", paddingTop: space.xxl, gap: space.sm },
  centeredText: { ...type.small, color: colors.textMuted },
});
