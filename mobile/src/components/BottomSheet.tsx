import React, { useRef, useEffect, useCallback } from "react";
import {
  Animated,
  PanResponder,
  StyleSheet,
  View,
  Dimensions,
  Platform,
} from "react-native";
import { colors, radius, space } from "../theme";

/**
 * Draggable sheet over the map, built on core Animated + PanResponder.
 *
 * Deliberately not react-native-gesture-handler or reanimated: both are
 * native modules, and adding one would force a fresh `expo prebuild` and
 * native rebuild. This screen needs a sheet, not a gesture framework.
 */

const { height: SCREEN_H } = Dimensions.get("window");

export type SnapPoint = "peek" | "half" | "full";

const SNAP_FRACTIONS: Record<SnapPoint, number> = {
  peek: 0.18,
  half: 0.46,
  full: 0.86,
};

function heightFor(point: SnapPoint) {
  return Math.round(SCREEN_H * SNAP_FRACTIONS[point]);
}

export default function BottomSheet({
  snap,
  onSnapChange,
  children,
}: {
  snap: SnapPoint;
  onSnapChange: (s: SnapPoint) => void;
  children: React.ReactNode;
}) {
  const height = useRef(new Animated.Value(heightFor(snap))).current;
  const startHeight = useRef(heightFor(snap));

  useEffect(() => {
    Animated.spring(height, {
      toValue: heightFor(snap),
      useNativeDriver: false, // animating height, not transform
      damping: 22,
      stiffness: 220,
      mass: 0.7,
    }).start();
  }, [snap, height]);

  const settle = useCallback(
    (finalHeight: number, velocity: number) => {
      // A firm flick should carry to the next stop rather than snapping back
      // to whichever point happens to be numerically closest.
      const order: SnapPoint[] = ["peek", "half", "full"];
      let best: SnapPoint = "peek";
      let bestDist = Infinity;
      for (const p of order) {
        const d = Math.abs(heightFor(p) - finalHeight);
        if (d < bestDist) {
          bestDist = d;
          best = p;
        }
      }
      if (Math.abs(velocity) > 0.5) {
        const idx = order.indexOf(best);
        const next = velocity < 0 ? idx + 1 : idx - 1;
        if (next >= 0 && next < order.length) best = order[next];
      }
      onSnapChange(best);
    },
    [onSnapChange]
  );

  const pan = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_e, g) => Math.abs(g.dy) > 4,
      onPanResponderGrant: () => {
        height.stopAnimation((v: number) => {
          startHeight.current = v;
        });
      },
      onPanResponderMove: (_e, g) => {
        const next = Math.min(
          heightFor("full"),
          Math.max(heightFor("peek") * 0.6, startHeight.current - g.dy)
        );
        height.setValue(next);
      },
      onPanResponderRelease: (_e, g) => {
        settle(startHeight.current - g.dy, g.vy);
      },
    })
  ).current;

  return (
    <Animated.View style={[styles.sheet, { height }]}>
      <View {...pan.panHandlers} style={styles.grabber}>
        <View style={styles.grabberBar} />
      </View>
      <View style={styles.body}>{children}</View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  sheet: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    ...Platform.select({
      android: { elevation: 16 },
      default: {
        shadowColor: "#000",
        shadowOpacity: 0.14,
        shadowRadius: 18,
        shadowOffset: { width: 0, height: -4 },
      },
    }),
  },
  grabber: { paddingTop: space.sm, paddingBottom: space.sm, alignItems: "center" },
  grabberBar: {
    width: 40,
    height: 4,
    borderRadius: radius.pill,
    backgroundColor: colors.line,
  },
  body: { flex: 1 },
});
