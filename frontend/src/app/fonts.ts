import { Inter, Vazirmatn } from "next/font/google";

export const englishFont = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-ui-en",
});

export const persianFont = Vazirmatn({
  subsets: ["arabic", "latin"],
  display: "swap",
  variable: "--font-ui-fa",
});
