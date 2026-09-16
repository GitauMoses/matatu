// app.config.js (not app.json) so the Mapbox native-build download token can
// come from an environment variable instead of being committed to git.
// Set RNMAPBOX_MAPS_DOWNLOAD_TOKEN in your shell (a Mapbox *secret* token with
// the "Downloads:Read" scope, from https://account.mapbox.com/access-tokens/)
// before `npx expo prebuild` / `expo run:android` / EAS build.
module.exports = {
  expo: {
    name: "Matatu App",
    slug: "mobile",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/icon.png",
    userInterfaceStyle: "light",
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.gitaumoses.matatuapp",
    },
    android: {
      package: "com.gitaumoses.matatuapp",
      adaptiveIcon: {
        backgroundColor: "#E6F4FE",
        foregroundImage: "./assets/android-icon-foreground.png",
        backgroundImage: "./assets/android-icon-background.png",
        monochromeImage: "./assets/android-icon-monochrome.png",
      },
      predictiveBackGestureEnabled: false,
    },
    web: { favicon: "./assets/favicon.png" },
    plugins: [
      "@rnmapbox/maps",
      [
        "expo-location",
        {
          locationAlwaysAndWhenInUsePermission:
            "Allow the matatu app to use your location to find nearby stages.",
        },
      ],
    ],
  },
};
