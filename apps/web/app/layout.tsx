import type { Metadata } from "next";
import "./styles.css";
import "./enhancements.css";
import "leaflet/dist/leaflet.css";

export const metadata: Metadata = { title: "Rajkot Traffic Lab", description: "Auditable corridor simulation" };

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
