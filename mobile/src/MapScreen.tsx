import React, { useEffect, useState, useCallback, useRef, useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  StatusBar,
  Keyboard,
  Alert,
} from "react-native";
import * as Location from "expo-location";
import MapboxGL from "@rnmapbox/maps";
import { planTrip, searchPlaces, fetchStops, Stop, SearchResult, PlanOption, PlanResult } from "./api";
import { Ionicons } from "@expo/vector-icons";
import { colors, radius, space, type, ROUTE_LINE } from "./theme";
import BottomSheet, { SnapPoint } from "./components/BottomSheet";
import Home from "./components/Home";
import SearchScreen from "./components/SearchScreen";
import RouteOptions from "./components/RouteOptions";
import Itinerary, { ItinerarySummary } from "./components/Itinerary";
import Splash from "./components/Splash";
import NavBanner from "./components/NavBanner";
import { useJourneyProgress } from "./useJourneyProgress";

MapboxGL.setAccessToken(process.env.EXPO_PUBLIC_MAPBOX_TOKEN ?? "");

const DEFAULT_CENTER: [number, number] = [36.8278, -1.2841]; // town

type Point = { lat: number; lon: number; label: string };
type Field = "origin" | "destination" | null;
type Screen = "home" | "search" | "results" | "trip";

export default function MapScreen() {
  const [screen, setScreen] = useState<Screen>("home");
  const [favourites, setFavourites] = useState<{ home: Point | null; work: Point | null }>({
    home: null,
    work: null,
  });
  const favouriteTarget = useRef<"home" | "work" | null>(null);
  const [origin, setOrigin] = useState<Point | null>(null);
  const [destination, setDestination] = useState<Point | null>(null);
  const [originQuery, setOriginQuery] = useState("");
  const [destQuery, setDestQuery] = useState("");
  const [suggestions, setSuggestions] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [activeField, setActiveField] = useState<Field>(null);
  const [result, setResult] = useState<PlanResult | null>(null);
  const [selected, setSelected] = useState(0);
  const [loading, setLoading] = useState(false);
  const [snap, setSnap] = useState<SnapPoint>("peek");
  const [showSplash, setShowSplash] = useState(true);
  const [allStages, setAllStages] = useState<Stop[]>([]);
  const [navigating, setNavigating] = useState(false);
  const [livePos, setLivePos] = useState<{ lat: number; lon: number } | null>(null);
  const watcher = useRef<Location.LocationSubscription | null>(null);

  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reqSeq = useRef(0);
  const camera = useRef<MapboxGL.Camera>(null);

  // Every stage in the city, drawn faintly so the network itself is visible.
  useEffect(() => {
    fetchStops().then(setAllStages).catch(() => {});
  }, []);

  useEffect(() => {
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        setOrigin({ lat: DEFAULT_CENTER[1], lon: DEFAULT_CENTER[0], label: "Nairobi CBD" });
        setOriginQuery("Nairobi CBD");
        return;
      }
      const loc = await Location.getCurrentPositionAsync({});
      setOrigin({ lat: loc.coords.latitude, lon: loc.coords.longitude, label: "Current location" });
      setOriginQuery("Current location");
    })();
  }, []);

  useEffect(() => {
    if (!origin || !destination) return;
    setLoading(true);
    setSelected(0);
    planTrip(origin.lat, origin.lon, destination.lat, destination.lon, origin.label, destination.label)
      .then((r) => {
        setResult(r);
        if (r.options?.length > 0 && !r.walk_only) {
          setScreen("results");
        } else if (r.walk_only) {
          const dist =
            r.walk_only.distance_km < 1
              ? `${Math.round(r.walk_only.distance_km * 1000)} m`
              : `${r.walk_only.distance_km} km`;
          Alert.alert(
            "Just walk it",
            `${dist} · about ${r.walk_only.minutes} min on foot. Around town a matatu costs you more time than it saves.`
          );
          setScreen("home");
        }
        setSnap("half");
      })
      .catch((e) => {
        setResult(null);
        Alert.alert("No matatu for that trip", e.message ?? String(e));
        setScreen("home");
        setSnap("peek");
      })
      .finally(() => setLoading(false));
  }, [origin, destination]);

  const option: PlanOption | null = result?.options[selected] ?? null;

  // Watch position only while navigating. A continuous high-accuracy fix is
  // the most expensive thing the app can do to a battery, so it starts when
  // the journey starts and stops the moment it ends.
  useEffect(() => {
    if (!navigating) {
      watcher.current?.remove();
      watcher.current = null;
      return;
    }
    let cancelled = false;
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted" || cancelled) return;
      watcher.current = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          distanceInterval: 10,
          timeInterval: 3000,
        },
        (loc) =>
          setLivePos({ lat: loc.coords.latitude, lon: loc.coords.longitude })
      );
    })();
    return () => {
      cancelled = true;
      watcher.current?.remove();
      watcher.current = null;
    };
  }, [navigating]);

  const progress = useJourneyProgress(
    navigating ? option : null,
    livePos,
    destination ? { lat: destination.lat, lon: destination.lon } : null
  );

  useEffect(() => {
    if (!option || navigating) return;
    const pts = option.legs.flatMap((l) => l.geometry);
    if (pts.length < 2) return;
    const lons = pts.map((p) => p[0]);
    const lats = pts.map((p) => p[1]);
    // Bottom padding is large so the sheet doesn't sit on top of the route.
    camera.current?.fitBounds(
      [Math.max(...lons), Math.max(...lats)],
      [Math.min(...lons), Math.min(...lats)],
      [70, 50, 260, 50],
      700
    );
  }, [option, navigating]);

  const onChange = useCallback(
    (field: Exclude<Field, null>, text: string) => {
      if (field === "origin") setOriginQuery(text);
      else setDestQuery(text);
      setActiveField(field);

      if (debounce.current) clearTimeout(debounce.current);
      if (text.trim().length < 2) {
        setSuggestions([]);
        setSearching(false);
        return;
      }
      setSearching(true);
      debounce.current = setTimeout(async () => {
        const seq = ++reqSeq.current;
        try {
          const found = await searchPlaces(
            text,
            origin ? { lat: origin.lat, lon: origin.lon } : undefined
          );
          if (seq === reqSeq.current) setSuggestions(found);
        } catch {
          if (seq === reqSeq.current) setSuggestions([]);
        } finally {
          if (seq === reqSeq.current) setSearching(false);
        }
      }, 350);
    },
    [origin]
  );

  const pick = useCallback((field: Exclude<Field, null>, s: SearchResult) => {
    const p: Point = { lat: s.lat, lon: s.lon, label: s.name };
    if (field === "origin") {
      setOrigin(p);
      setOriginQuery(s.name);
    } else {
      setDestination(p);
      setDestQuery(s.name);
    }
    if (favouriteTarget.current) {
      setFavourites((f) => ({ ...f, [favouriteTarget.current!]: p }));
      favouriteTarget.current = null;
    }
    setSuggestions([]);
    setActiveField(null);
    Keyboard.dismiss();
  }, []);

  const useMyLocation = useCallback(async () => {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== "granted") return;
    const loc = await Location.getCurrentPositionAsync({});
    setOrigin({ lat: loc.coords.latitude, lon: loc.coords.longitude, label: "Current location" });
    setOriginQuery("Current location");
    setSuggestions([]);
    setActiveField(null);
    Keyboard.dismiss();
  }, []);

  const onOpenSearch = useCallback(() => {
    favouriteTarget.current = null;
    setActiveField("destination");
    setScreen("search");
  }, []);

  const onPickFavourite = useCallback(
    (which: "home" | "work") => {
      const point = favourites[which];
      if (point) {
        // Already set once — re-picking a favourite jumps straight to it.
        setDestination(point);
        setDestQuery(point.label);
        return;
      }
      favouriteTarget.current = which;
      setActiveField("destination");
      setScreen("search");
    },
    [favourites]
  );

  // One feature per leg, tinted by route, so a change of matatu shows on the
  // map as a change of colour rather than one undifferentiated line.
  const routeLine = useMemo(() => {
    if (!option) return null;
    return {
      type: "FeatureCollection",
      features: option.legs.map((leg, i) => ({
        type: "Feature" as const,
        properties: { leg: i },
        geometry: { type: "LineString" as const, coordinates: leg.geometry as GeoJSON.Position[] },
      })),
    } as GeoJSON.FeatureCollection;
  }, [option]);

  // Walking is drawn separately and dashed: the map should make it obvious
  // which part of the journey is on foot, not just the itinerary text.
  const walkLines = useMemo(() => {
    if (!option || !origin || !destination) return null;
    const legs = option.legs;
    const segs: GeoJSON.Position[][] = [];
    const board = legs[0].board_stop;
    const alight = legs[legs.length - 1].alight_stop;
    if (option.walk_to_board_km > 0.02)
      segs.push([[origin.lon, origin.lat], [board.lon, board.lat]]);
    if (option.walk_from_alight_km > 0.02)
      segs.push([[alight.lon, alight.lat], [destination.lon, destination.lat]]);
    if ((option.transfer_walk_km ?? 0) > 0.02 && legs.length > 1)
      segs.push([
        [legs[0].alight_stop.lon, legs[0].alight_stop.lat],
        [legs[1].board_stop.lon, legs[1].board_stop.lat],
      ]);
    if (!segs.length) return null;
    return {
      type: "FeatureCollection",
      features: segs.map((coordinates) => ({
        type: "Feature" as const,
        properties: {},
        geometry: { type: "LineString" as const, coordinates },
      })),
    } as GeoJSON.FeatureCollection;
  }, [option, origin, destination]);

  const allStageDots = useMemo(() => {
    if (!allStages.length) return null;
    return {
      type: "FeatureCollection",
      features: allStages.map((s) => ({
        type: "Feature" as const,
        properties: { name: s.name },
        geometry: { type: "Point" as const, coordinates: [s.lon, s.lat] as GeoJSON.Position },
      })),
    } as GeoJSON.FeatureCollection;
  }, [allStages]);

  const journeyStops = useMemo(() => {
    if (!option) return null;
    return {
      type: "FeatureCollection",
      features: option.legs.flatMap((leg) =>
        leg.stops.slice(1, -1).map((s) => ({
          type: "Feature" as const,
          properties: {},
          geometry: { type: "Point" as const, coordinates: [s.lon, s.lat] as GeoJSON.Position },
        }))
      ),
    } as GeoJSON.FeatureCollection;
  }, [option]);

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={colors.ink} />
      {showSplash && <Splash onDone={() => setShowSplash(false)} />}

      <MapboxGL.MapView
        style={StyleSheet.absoluteFill}
        styleURL={MapboxGL.StyleURL.Street}
        logoEnabled={false}
      >
        <MapboxGL.Camera
          ref={camera}
          defaultSettings={{ centerCoordinate: DEFAULT_CENTER, zoomLevel: 11.5 }}
          followUserLocation={navigating}
          followUserMode={MapboxGL.UserTrackingMode.FollowWithHeading}
          followZoomLevel={16.5}
          followPitch={navigating ? 45 : 0}
          followPadding={{ paddingBottom: 220, paddingTop: 40, paddingLeft: 0, paddingRight: 0 }}
        />

        {navigating && (
          <MapboxGL.UserLocation
            visible
            showsUserHeadingIndicator
            minDisplacement={5}
            androidRenderMode="compass"
          />
        )}

        {allStageDots && (
          <MapboxGL.ShapeSource id="allStages" shape={allStageDots}>
            {/* every matatu stage in Nairobi, quiet until you zoom in */}
            <MapboxGL.CircleLayer
              id="allStageDots"
              minZoomLevel={11}
              style={{
                circleRadius: ["interpolate", ["linear"], ["zoom"], 11, 1.6, 14, 3, 16, 4.5],
                circleColor: colors.brand,
                circleOpacity: ["interpolate", ["linear"], ["zoom"], 11, 0.3, 14, 0.65],
                circleStrokeWidth: ["interpolate", ["linear"], ["zoom"], 13, 0, 15, 1],
                circleStrokeColor: colors.surface,
              }}
            />
            <MapboxGL.SymbolLayer
              id="allStageLabels"
              minZoomLevel={15}
              style={{
                textField: ["get", "name"],
                textSize: 10.5,
                textOffset: [0, 1.1],
                textColor: colors.text,
                textHaloColor: colors.surface,
                textHaloWidth: 1.4,
                textOptional: true,
                textAllowOverlap: false,
              }}
            />
          </MapboxGL.ShapeSource>
        )}

        {routeLine && (
          <MapboxGL.ShapeSource id="route" shape={routeLine}>
            {/* white casing lifts the line off street detail without tinting it */}
            <MapboxGL.LineLayer
              id="routeCasing"
              style={{
                lineColor: colors.surface,
                lineWidth: 10,
                lineCap: "round",
                lineJoin: "round",
              }}
            />
            <MapboxGL.LineLayer
              id="routeLine"
              style={{
                lineColor: ROUTE_LINE,
                lineWidth: 5,
                lineCap: "round",
                lineJoin: "round",
              }}
            />
          </MapboxGL.ShapeSource>
        )}

        {walkLines && (
          <MapboxGL.ShapeSource id="walk" shape={walkLines}>
            <MapboxGL.LineLayer
              id="walkLine"
              style={{
                lineColor: colors.walk,
                lineWidth: 3.5,
                lineDasharray: [1, 1.8],
                lineCap: "round",
              }}
            />
          </MapboxGL.ShapeSource>
        )}

        {journeyStops && (
          <MapboxGL.ShapeSource id="stops" shape={journeyStops}>
            <MapboxGL.CircleLayer
              id="stopDots"
              style={{
                circleRadius: 3,
                circleColor: colors.surface,
                circleStrokeWidth: 1.5,
                circleStrokeColor: colors.ink,
              }}
            />
          </MapboxGL.ShapeSource>
        )}

        {origin && (
          <MapboxGL.PointAnnotation id="origin" coordinate={[origin.lon, origin.lat]}>
            <View style={styles.originPin} />
          </MapboxGL.PointAnnotation>
        )}
        {destination && (
          <MapboxGL.PointAnnotation id="dest" coordinate={[destination.lon, destination.lat]}>
            <View style={styles.destPin} />
          </MapboxGL.PointAnnotation>
        )}
      </MapboxGL.MapView>

      {screen === "trip" &&
        (navigating && option && progress ? (
          <NavBanner
            option={option}
            progress={progress}
            onStop={() => {
              setNavigating(false);
              setLivePos(null);
              setSnap("half");
            }}
          />
        ) : (
          <TouchableOpacity
            style={styles.tripBack}
            onPress={() => setScreen("results")}
            hitSlop={10}
          >
            <Ionicons name="arrow-back" size={20} color={colors.brand} />
          </TouchableOpacity>
        ))}

      {screen === "trip" && (
        <BottomSheet snap={snap} onSnapChange={setSnap}>
          {option &&
            (snap === "peek" ? (
              <ItinerarySummary option={option} />
            ) : (
              <Itinerary option={option} />
            ))}

          {option && !navigating && (
            <TouchableOpacity
              style={styles.startBtn}
              onPress={() => {
                setNavigating(true);
                setSnap("peek");
              }}
            >
              <Text style={styles.startBtnText}>Start</Text>
            </TouchableOpacity>
          )}
        </BottomSheet>
      )}

      {screen === "home" && (
        <Home
          originLabel={originQuery}
          destQuery={destQuery}
          onOpenSearch={onOpenSearch}
          favourites={{
            home: favourites.home?.label ?? null,
            work: favourites.work?.label ?? null,
          }}
          onPickFavourite={onPickFavourite}
        />
      )}

      {screen === "search" && (
        <SearchScreen
          query={destQuery}
          onChangeQuery={(t) => onChange("destination", t)}
          onBack={() => {
            favouriteTarget.current = null;
            setScreen("home");
          }}
          onUseLocation={useMyLocation}
          suggestions={suggestions}
          searching={searching}
          loading={loading}
          onPick={(s) => pick("destination", s)}
          fieldLabel={favouriteTarget.current ? `Set ${favouriteTarget.current}` : "To"}
        />
      )}

      {screen === "results" && result && result.options.length > 0 && !result.walk_only && (
        <RouteOptions
          originLabel={originQuery}
          destLabel={destQuery}
          options={result.options}
          onBack={() => {
            setScreen("home");
            setDestination(null);
            setDestQuery("");
            setResult(null);
          }}
          onSelect={(i) => {
            setSelected(i);
            setScreen("trip");
            setSnap("half");
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.canvas },

  tripBack: {
    position: "absolute",
    top: 50,
    left: space.md,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#000",
    shadowOpacity: 0.16,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },

  originPin: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: colors.surface,
    borderWidth: 4,
    borderColor: colors.brand,
  },
  destPin: {
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: colors.accent,
    borderWidth: 3,
    borderColor: colors.surface,
  },

  startBtn: {
    marginHorizontal: space.lg,
    marginTop: space.sm,
    marginBottom: space.lg,
    backgroundColor: colors.brand,
    borderRadius: radius.pill,
    paddingVertical: 15,
    alignItems: "center",
    shadowColor: colors.brandDeep,
    shadowOpacity: 0.3,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
  startBtnText: { ...type.title, fontSize: 16, color: colors.textOnInk },
});
