import "@/assets/css/icofont.min.css";
import "@/assets/css/popup.css";
import "@/assets/css/video-modal.css";
import AppEffects from "@/components/shared/AppEffects";
import FixedShadow from "@/components/shared/others/FixedShadow";
import PreloaderPrimary from "@/components/shared/others/PreloaderPrimary";
import "aos/dist/aos.css";
import localFont from "next/font/local";
import "swiper/css";
import "swiper/css/effect-cards";
import "swiper/css/navigation";
import "swiper/css/pagination";
import "./globals.css";

import CartContextProvider from "@/contexts/CartContext";
import WishlistContextProvider from "@/contexts/WshlistContext";
import AppToaster from "@/components/shared/AppToaster";
import ReactQueryProvider from "@/providers/ReactQueryProvider";
import SessionProvider from "@/providers/SessionProvider";

export const inter = localFont({
  src: "../assets/fonts/inter/Inter-VariableFont_opsz,wght.ttf",
  display: "swap",
  variable: "--font-inter",
});

export const hind = localFont({
  src: [
    {
      path: "../assets/fonts/hind/Hind-Light.ttf",
      weight: "300",
      style: "normal",
    },
    {
      path: "../assets/fonts/hind/Hind-Regular.ttf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../assets/fonts/hind/Hind-Medium.ttf",
      weight: "500",
      style: "normal",
    },
    {
      path: "../assets/fonts/hind/Hind-SemiBold.ttf",
      weight: "600",
      style: "normal",
    },
    {
      path: "../assets/fonts/hind/Hind-Bold.ttf",
      weight: "700",
      style: "normal",
    },
  ],
  display: "swap",
  variable: "--font-hind",
});

export const metadata = {
  title: "CMCP",
  description: "CMCP system",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${hind.variable}`}>
      <body
        className={`relative z-0 leading-[1.8] bg-ds-page text-ds-text-secondary ${inter.className}`}
      >
        <ReactQueryProvider>
          <SessionProvider>
            <CartContextProvider>
              <WishlistContextProvider>
                <AppEffects />
                <AppToaster />
                <PreloaderPrimary />
                {children}
                <div>
                  <FixedShadow />
                  <FixedShadow align={"right"} />
                </div>
              </WishlistContextProvider>
            </CartContextProvider>
          </SessionProvider>
        </ReactQueryProvider>
      </body>
    </html>
  );
}
