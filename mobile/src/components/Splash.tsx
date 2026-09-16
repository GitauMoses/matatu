import React, { useEffect, useRef } from "react";
import { View, Text, StyleSheet, Animated, Easing, Dimensions } from "react-native";
import { colors, space, type } from "../theme";

/**
 * Opening screen. Sets the tone before the map appears, and covers the
 * moment the backend is warming up.
 */

const { width: W } = Dimensions.get("window");

export default function Splash({ onDone }: { onDone: () => void }) {
  const fade = useRef(new Animated.Value(0)).current;
  const rise = useRef(new Animated.Value(18)).current;
  const line = useRef(new Animated.Value(0)).current;
  const out = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.sequence([
      Animated.parallel([
        Animated.timing(fade, { toValue: 1, duration: 420, useNativeDriver: true }),
        Animated.timing(rise, { toValue: 0, duration: 480, easing: Easing.out(Easing.cubic), useNativeDriver: true }),
      ]),
      Animated.timing(line, { toValue: 1, duration: 620, easing: Easing.inOut(Easing.cubic), useNativeDriver: false }),
      Animated.delay(280),
      Animated.timing(out, { toValue: 0, duration: 320, useNativeDriver: true }),
    ]).start(({ finished }) => finished && onDone());
  }, [fade, rise, line, out, onDone]);

  const width = line.interpolate({ inputRange: [0, 1], outputRange: [0, W * 0.52] });

  return (
    <Animated.View style={[styles.root, { opacity: out }]}>
      <Animated.View style={{ opacity: fade, transform: [{ translateY: rise }] }}>
        <Text style={styles.brand}>MATATU</Text>
        <Text style={styles.tagline}>Know which one to board.</Text>
      </Animated.View>

      <View style={styles.lineWrap}>
        <View style={styles.dotStart} />
        <Animated.View style={[styles.line, { width }]} />
        <Animated.View style={[styles.dotEnd, { opacity: line }]} />
      </View>

      <Animated.Text style={[styles.footer, { opacity: fade }]}>
        134 routes · 2,485 stages · Nairobi
      </Animated.Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: {
    position: "absolute",
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: colors.brandDeep,
    alignItems: "center",
    justifyContent: "center",
    zIndex: 100,
  },
  brand: {
    color: colors.textOnInk,
    fontSize: 42,
    fontWeight: "800",
    letterSpacing: 6,
    textAlign: "center",
  },
  tagline: {
    color: "#D8D2FA",
    fontSize: 15,
    textAlign: "center",
    marginTop: space.sm,
  },
  lineWrap: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: space.xxl,
    height: 12,
  },
  dotStart: {
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 2.5,
    borderColor: "#D8D2FA",
  },
  line: { height: 2.5, backgroundColor: colors.accent, borderRadius: 2 },
  dotEnd: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.accent },
  footer: {
    position: "absolute",
    bottom: 56,
    color: "#D8D2FA",
    fontSize: 12,
    letterSpacing: 0.6,
  },
});
