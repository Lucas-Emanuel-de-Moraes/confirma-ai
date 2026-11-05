import { AppShell } from "@/components/AppShell";

export default function LayoutAutenticado({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
