import "./globals.css";
import { AuthProvider } from "@/lib/useAuth";

export const metadata = {
  title: "AGENTGUARD — Runtime Control Plane for Autonomous AI",
  description: "Enterprise runtime control plane and zero-trust governance platform for autonomous AI employees.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#FCFCFA] text-[#1F1F1F] font-sans antialiased min-h-screen">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
