import type { Metadata } from "next";
import "@/styles/globals.css";
import { ToastProvider } from "@/components/platform/Toast";

export const metadata: Metadata = {
  title: "MCP Platform",
  description: "Control plane for bots, tools, MCP servers, and models",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
