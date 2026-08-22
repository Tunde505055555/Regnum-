import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useWallet } from "@/hooks/use-wallet";
import { readState, callWrite } from "@/lib/contract";
import type { Address } from "viem";
import { Megaphone, Scale, Shield, Coins, Vote, Swords, Users, Loader2 } from "lucide-react";

type State = {
  city: string;
  players: any[];
  factions: any[];
  propaganda: any[];
  laws: any[];
  accusations: any[];
  bribes: any[];
  sabotages: any[];
  elections: any[];
};

export function GameBoard({ contractAddr }: { contractAddr: Address }) {
  const { address, chainOk } = useWallet();
  const [state, setState] = useState<State | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const s = (await readState(contractAddr)) as State;
      setState(s);
    } catch (e: any) {
      console.error(e);
      toast.error("Read failed: " + (e?.message ?? "unknown"));
    }
  };

  useEffect(() => { refresh(); const i = setInterval(refresh, 8000); return () => clearInterval(i); }, [contractAddr]);

  const tx = async (label: string, fn: string, args: any[]) => {
    if (!address) return toast.error("Connect wallet first");
    if (!chainOk) return toast.error("Switch to GenLayer Studio");
    setBusy(label);
    try {
      toast.loading(`${label}…`, { id: label });
      await callWrite(address, contractAddr, fn, args);
      toast.success(`${label} accepted by validators`, { id: label });
      await refresh();
    } catch (e: any) {
      toast.error(e?.shortMessage ?? e?.message ?? "tx failed", { id: label });
    } finally { setBusy(null); }
  };

  const me = state?.players.find((p) => p.address?.toLowerCase() === address?.toLowerCase());

  return (
    <div className="container mx-auto px-4 py-6">
      <Hero state={state} me={me} />
      <Tabs defaultValue="citizen" className="mt-6">
        <TabsList className="grid h-auto w-full grid-cols-4 gap-1 bg-card p-1 md:grid-cols-7">
          <TabsTrigger value="citizen"><Users className="mr-1 h-4 w-4" /> Citizen</TabsTrigger>
          <TabsTrigger value="propaganda"><Megaphone className="mr-1 h-4 w-4" /> Propaganda</TabsTrigger>
          <TabsTrigger value="laws"><Scale className="mr-1 h-4 w-4" /> Laws</TabsTrigger>
          <TabsTrigger value="court"><Shield className="mr-1 h-4 w-4" /> Court</TabsTrigger>
          <TabsTrigger value="bribes"><Coins className="mr-1 h-4 w-4" /> Bribes</TabsTrigger>
          <TabsTrigger value="sabotage"><Swords className="mr-1 h-4 w-4" /> Sabotage</TabsTrigger>
          <TabsTrigger value="election"><Vote className="mr-1 h-4 w-4" /> Election</TabsTrigger>
        </TabsList>

        <TabsContent value="citizen" className="mt-4 grid gap-4 md:grid-cols-2">
          <RegisterCard onSubmit={(name: string, faction: string) => tx("Register", "register_player", [name, faction])} disabled={!!me} factions={state?.factions ?? []} />
          <FactionCard onSubmit={(name: string, ideology: string) => tx("Create faction", "create_faction", [name, ideology])} factions={state?.factions ?? []} />
        </TabsContent>

        <TabsContent value="propaganda" className="mt-4 grid gap-4 md:grid-cols-2">
          <PropagandaCard busy={busy} factions={state?.factions ?? []} onSubmit={(h: string, t: string) => tx("Spread propaganda", "spread_propaganda", [h, t])} />
          <FeedCard title="Media Feed" items={state?.propaganda ?? []} render={(p, i) => (
            <FeedItem key={i} chip={p.verdict?.verdict ?? "—"} chipColor={p.verdict?.verdict === "viral" ? "bg-[var(--propaganda)]" : "bg-muted"}
              title={p.headline} subtitle={`vs ${p.target} · by ${short(p.by)}`} body={p.verdict?.summary} />
          )} />
        </TabsContent>

        <TabsContent value="laws" className="mt-4 grid gap-4 md:grid-cols-2">
          <LawCard busy={busy} onSubmit={(t: string, b: string) => tx("Propose law", "propose_law", [t, b])} />
          <FeedCard title="Constitutional Court Rulings" items={state?.laws ?? []} render={(l, i) => (
            <FeedItem key={i} chip={l.ruling?.legitimate ? "LEGITIMATE" : "UNCONSTITUTIONAL"}
              chipColor={l.ruling?.legitimate ? "bg-[var(--court)]" : "bg-destructive"}
              title={l.title} subtitle={`by ${short(l.by)}`} body={l.ruling?.ruling} />
          )} />
        </TabsContent>

        <TabsContent value="court" className="mt-4 grid gap-4 md:grid-cols-2">
          <AccuseCard busy={busy} players={state?.players ?? []} onSubmit={(t: string, c: string, e: string) => tx("File accusation", "accuse", [t, c, e])} />
          <FeedCard title="Court Verdicts" items={state?.accusations ?? []} render={(a, i) => (
            <FeedItem key={i} chip={a.verdict?.guilty ? "GUILTY" : "ACQUITTED"}
              chipColor={a.verdict?.guilty ? "bg-destructive" : "bg-[var(--police)]"}
              title={a.crime} subtitle={`${short(a.target)} · by ${short(a.by)}`} body={a.verdict?.opinion} />
          )} />
        </TabsContent>

        <TabsContent value="bribes" className="mt-4 grid gap-4 md:grid-cols-2">
          <BribeCard busy={busy} onSubmit={(o: string, a: number, p: string) => tx("Bribe official", "bribe_official", [o, a, p])} balance={me?.money ?? 0} />
          <FeedCard title="Black Market Ledger" items={state?.bribes ?? []} render={(b, i) => (
            <FeedItem key={i} chip={b.outcome?.accepted ? "ACCEPTED" : "REJECTED"}
              chipColor={b.outcome?.accepted ? "bg-[var(--bribe)]" : "bg-muted"}
              title={`${b.amount} GEN → ${b.official}`} subtitle={`by ${short(b.by)}`} body={`${b.purpose} — ${b.outcome?.reason ?? ""}`} />
          )} />
        </TabsContent>

        <TabsContent value="sabotage" className="mt-4 grid gap-4 md:grid-cols-2">
          <SabotageCard busy={busy} factions={state?.factions ?? []} onSubmit={(t: string, p: string) => tx("Sabotage", "sabotage", [t, p])} />
          <FeedCard title="Police Reports" items={state?.sabotages ?? []} render={(s, i) => (
            <FeedItem key={i} chip={s.outcome?.caught ? "CAUGHT" : s.outcome?.success ? "SUCCESS" : "FAILED"}
              chipColor={s.outcome?.caught ? "bg-destructive" : s.outcome?.success ? "bg-[var(--police)]" : "bg-muted"}
              title={`vs ${s.target}`} subtitle={`by ${short(s.by)}`} body={s.outcome?.report} />
          )} />
        </TabsContent>

        <TabsContent value="election" className="mt-4 grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Hold an Election</CardTitle><CardDescription>AI citizens cast subjective votes weighted by faction influence and recent media coverage.</CardDescription></CardHeader>
            <CardContent><Button onClick={() => tx("Election", "hold_election", [])} disabled={busy === "Election"} className="w-full">
              {busy === "Election" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Vote className="mr-2 h-4 w-4" />} Open Polls
            </Button></CardContent>
          </Card>
          <FeedCard title="Election History" items={state?.elections ?? []} render={(e, i) => (
            <FeedItem key={i} chip={`turnout ${e.turnout ?? "?"}`} chipColor="bg-primary" title={`Winner: ${e.winner}`} subtitle="" body={e.summary} />
          )} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function short(a?: string) { return a ? `${a.slice(0, 6)}…${a.slice(-4)}` : "—"; }

function Hero({ state, me }: { state: State | null; me: any }) {
  return (
    <section className="relative overflow-hidden rounded-2xl border border-border p-6 md:p-10" style={{ background: "var(--gradient-hero)" }}>
      <div className="relative z-10">
        <p className="text-xs uppercase tracking-[0.2em] text-primary">AI Political Warfare · GenLayer Studio</p>
        <h1 className="mt-2 text-3xl font-bold md:text-5xl">{state?.city ?? "Loading the city…"}</h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">A persistent online city governed by AI courts, AI media, AI police and AI citizens. Form factions. Manipulate elections. Spread propaganda. Pass laws. Sabotage rivals. Bribe officials.</p>
        <div className="mt-5 flex flex-wrap gap-2 text-xs">
          <Stat label="Players" value={state?.players.length ?? 0} />
          <Stat label="Factions" value={state?.factions.length ?? 0} />
          <Stat label="Headlines" value={state?.propaganda.length ?? 0} />
          <Stat label="Laws" value={state?.laws.length ?? 0} />
          <Stat label="Verdicts" value={state?.accusations.length ?? 0} />
          {me && <Stat label="You" value={`${me.name} · ${me.faction} · rep ${me.reputation} · ${me.money} GEN${me.in_jail ? " · 🔒" : ""}`} />}
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return <span className="rounded-md border border-border bg-card/60 px-2.5 py-1 backdrop-blur"><span className="text-muted-foreground">{label}:</span> <span className="font-semibold text-foreground">{value}</span></span>;
}

function RegisterCard({ onSubmit, disabled, factions }: any) {
  const [name, setName] = useState(""); const [f, setF] = useState("");
  return (<Card><CardHeader><CardTitle>Register as Citizen</CardTitle><CardDescription>Pick a name and a faction to join.</CardDescription></CardHeader>
    <CardContent className="space-y-2">
      <Input placeholder="Citizen name" value={name} onChange={(e) => setName(e.target.value)} disabled={disabled} />
      <Input placeholder="Faction (existing or new)" value={f} onChange={(e) => setF(e.target.value)} disabled={disabled} list="facs" />
      <datalist id="facs">{factions.map((x: any) => <option key={x.name} value={x.name} />)}</datalist>
      <Button className="w-full" disabled={disabled || !name || !f} onClick={() => onSubmit(name, f)}>{disabled ? "Already registered" : "Enter the city"}</Button>
    </CardContent></Card>);
}

function FactionCard({ onSubmit, factions }: any) {
  const [n, setN] = useState(""); const [i, setI] = useState("");
  return (<Card><CardHeader><CardTitle>Found a Faction</CardTitle><CardDescription>Define an ideology. AI media will judge it.</CardDescription></CardHeader>
    <CardContent className="space-y-2">
      <Input placeholder="Faction name" value={n} onChange={(e) => setN(e.target.value)} />
      <Input placeholder="Ideology (e.g. radical agrarian, techno-monarchist)" value={i} onChange={(e) => setI(e.target.value)} />
      <Button className="w-full" disabled={!n || !i} onClick={() => onSubmit(n, i)}>Found</Button>
      <div className="mt-3 flex flex-wrap gap-1">{factions.map((x: any) => (
        <Badge key={x.name} variant="secondary">{x.name} · {x.ideology} · infl {x.influence}</Badge>
      ))}</div>
    </CardContent></Card>);
}

function PropagandaCard({ onSubmit, factions, busy }: any) {
  const [h, setH] = useState(""); const [t, setT] = useState("");
  return (<Card><CardHeader><CardTitle>Publish Propaganda</CardTitle><CardDescription>AI media judges believability and viral pull.</CardDescription></CardHeader>
    <CardContent className="space-y-2">
      <Textarea rows={3} placeholder="BREAKING: …" value={h} onChange={(e) => setH(e.target.value)} />
      <Input placeholder="Target faction" value={t} onChange={(e) => setT(e.target.value)} list="facs2" />
      <datalist id="facs2">{factions.map((x: any) => <option key={x.name} value={x.name} />)}</datalist>
      <Button className="w-full" disabled={!h || !t || busy === "Spread propaganda"} onClick={() => onSubmit(h, t)}>
        {busy === "Spread propaganda" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Publish
      </Button>
    </CardContent></Card>);
}

function LawCard({ onSubmit, busy }: any) {
  const [t, setT] = useState(""); const [b, setB] = useState("");
  return (<Card><CardHeader><CardTitle>Propose a Law</CardTitle><CardDescription>The AI Constitutional Court rules subjectively.</CardDescription></CardHeader>
    <CardContent className="space-y-2">
      <Input placeholder="Law title" value={t} onChange={(e) => setT(e.target.value)} />
      <Textarea rows={4} placeholder="Full text of the bill…" value={b} onChange={(e) => setB(e.target.value)} />
      <Button className="w-full" disabled={!t || !b || busy === "Propose law"} onClick={() => onSubmit(t, b)}>
        {busy === "Propose law" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Submit
      </Button>
    </CardContent></Card>);
}

function AccuseCard({ onSubmit, players, busy }: any) {
  const [t, setT] = useState(""); const [c, setC] = useState(""); const [e, setE] = useState("");
  return (<Card><CardHeader><CardTitle>File Accusation</CardTitle><CardDescription>The AI Judge weighs your evidence subjectively.</CardDescription></CardHeader>
    <CardContent className="space-y-2">
      <Input placeholder="Target wallet address (0x…)" value={t} onChange={(x) => setT(x.target.value)} list="ppl" className="font-mono" />
      <datalist id="ppl">{players.map((p: any) => <option key={p.address} value={p.address}>{p.name}</option>)}</datalist>
      <Input placeholder="Alleged crime" value={c} onChange={(x) => setC(x.target.value)} />
      <Textarea rows={3} placeholder="Evidence presented to court…" value={e} onChange={(x) => setE(x.target.value)} />
      <Button className="w-full" disabled={!t || !c || !e || busy === "File accusation"} onClick={() => onSubmit(t, c, e)}>
        {busy === "File accusation" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Indict
      </Button>
    </CardContent></Card>);
}

function BribeCard({ onSubmit, busy, balance }: any) {
  const [o, setO] = useState("Judge"); const [a, setA] = useState(100); const [p, setP] = useState("");
  return (<Card><CardHeader><CardTitle>Bribe an AI Official</CardTitle><CardDescription>Balance: {balance} GEN. Some officials are corrupt, others will leak.</CardDescription></CardHeader>
    <CardContent className="space-y-2">
      <Input placeholder="Official role (Judge, Police Chief, Mayor…)" value={o} onChange={(e) => setO(e.target.value)} />
      <Input type="number" placeholder="Amount" value={a} onChange={(e) => setA(parseInt(e.target.value || "0"))} />
      <Textarea rows={3} placeholder="What do you want them to do?" value={p} onChange={(e) => setP(e.target.value)} />
      <Button className="w-full" disabled={!o || !p || a <= 0 || busy === "Bribe official"} onClick={() => onSubmit(o, a, p)}>
        {busy === "Bribe official" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Slip envelope
      </Button>
    </CardContent></Card>);
}

function SabotageCard({ onSubmit, factions, busy }: any) {
  const [t, setT] = useState(""); const [p, setP] = useState("");
  return (<Card><CardHeader><CardTitle>Sabotage a Faction</CardTitle><CardDescription>AI Police decides if you succeed — and if you get caught.</CardDescription></CardHeader>
    <CardContent className="space-y-2">
      <Input placeholder="Target faction" value={t} onChange={(e) => setT(e.target.value)} list="facs3" />
      <datalist id="facs3">{factions.map((x: any) => <option key={x.name} value={x.name} />)}</datalist>
      <Textarea rows={3} placeholder="Describe your plan…" value={p} onChange={(e) => setP(e.target.value)} />
      <Button className="w-full" disabled={!t || !p || busy === "Sabotage"} onClick={() => onSubmit(t, p)}>
        {busy === "Sabotage" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Execute plan
      </Button>
    </CardContent></Card>);
}

function FeedCard({ title, items, render }: { title: string; items: any[]; render: (x: any, i: number) => React.ReactNode }) {
  return (<Card><CardHeader><CardTitle>{title}</CardTitle></CardHeader>
    <CardContent className="max-h-[480px] space-y-2 overflow-y-auto">
      {items.length === 0 ? <p className="text-sm text-muted-foreground">No entries yet.</p> : [...items].reverse().map(render)}
    </CardContent></Card>);
}

function FeedItem({ chip, chipColor, title, subtitle, body }: any) {
  return (<div className="rounded-md border border-border bg-muted/40 p-3">
    <div className="flex items-center justify-between gap-2">
      <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-background ${chipColor}`}>{chip}</span>
      <span className="font-mono text-[10px] text-muted-foreground">{subtitle}</span>
    </div>
    <p className="mt-1.5 text-sm font-semibold">{title}</p>
    {body && <p className="mt-1 text-xs text-muted-foreground">{body}</p>}
  </div>);
}