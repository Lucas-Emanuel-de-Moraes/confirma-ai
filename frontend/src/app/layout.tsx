import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import { AvisosProvider } from "@/components/ui/Aviso";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Confirma Aí", template: "%s · Confirma Aí" },
  description: "Confirmação de consultas e recuperação de vagas perdidas",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        <AuthProvider>
          <AvisosProvider>{children}</AvisosProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
