import type { Metadata } from "next";
import "./globals.css";
import "./home.css";
import Sidebar from "./components/Sidebar";

export const metadata: Metadata = {
  title: "Agentic AI OS — Control Plane",
  description: "Long-horizon autonomous mission runtime — control plane",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="app">
          <Sidebar />
          <main className="content">{children}</main>
        </div>
      </body>
    </html>
  );
}
