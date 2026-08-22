import { createFileRoute } from "@tanstack/react-router";
import { Header } from "@/components/Header";
import { GameBoard } from "@/components/GameBoard";
import { Toaster } from "@/components/ui/sonner";
import { getContractAddress } from "@/lib/contract";

export const Route = createFileRoute("/")({
  component: Index,
  head: () => ({
    meta: [
      { title: "Regnum.AI — AI Political Warfare on GenLayer" },
      { name: "description", content: "A persistent online city governed by AI courts, AI media, AI police and AI citizens. Form factions, manipulate elections, spread propaganda, pass laws, sabotage rivals, bribe officials." },
      { property: "og:title", content: "Regnum.AI — AI Political Warfare on GenLayer" },
      { property: "og:description", content: "Enter a persistent online city governed by AI courts, media, police, and citizens." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
});

function Index() {
  const addr = getContractAddress();
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header contractAddr={addr} />
      <GameBoard contractAddr={addr} />
      <Toaster richColors position="top-right" />
    </div>
  );
}
