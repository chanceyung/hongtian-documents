import "dotenv/config";

export const env = {
  isDesktop: process.env.DESKTOP_MODE === "true",
  isProduction: process.env.NODE_ENV === "production",
  desktopUserId: "desktop-user",
};
