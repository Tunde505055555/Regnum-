import { Button } from "@/components/ui/button";
import { useWallet } from "@/hooks/use-wallet";

export function Header({ contractAddr }: { contractAddr: string | null }) {
  const { address, chainOk, connect, switchChain } = useWallet();
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur">
      <div className="container mx-auto flex h-14 items-center justify-between gap-3 px-4">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-primary shadow-[var(--shadow-glow)]" />
          <span className="font-bold tracking-wide">REGNUM<span className="text-primary">.AI</span></span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded-md border border-border bg-muted px-2 py-1 font-mono text-[11px]">
            {contractAddr ? `${contractAddr.slice(0, 6)}…${contractAddr.slice(-4)}` : "—"}
          </span>
          {!address ? (
            <Button size="sm" onClick={connect}>Connect Wallet</Button>
          ) : !chainOk ? (
            <Button size="sm" variant="destructive" onClick={switchChain}>Switch to Studio</Button>
          ) : (
            <span className="rounded-md bg-secondary px-2 py-1 font-mono text-[11px]">{address.slice(0, 6)}…{address.slice(-4)}</span>
          )}
        </div>
      </div>
    </header>
  );
}