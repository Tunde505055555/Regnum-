import { useEffect, useState, useCallback } from "react";
import type { Address } from "viem";
import { connectWallet, ensureStudionet, CHAIN_HEX } from "@/lib/genlayer-client";

export function useWallet() {
  const [address, setAddress] = useState<Address | null>(null);
  const [chainOk, setChainOk] = useState(false);

  useEffect(() => {
    const eth = (window as any).ethereum;
    if (!eth) return;
    eth.request({ method: "eth_accounts" }).then((accs: string[]) => {
      if (accs[0]) setAddress(accs[0] as Address);
    });
    eth.request({ method: "eth_chainId" }).then((id: string) => {
      setChainOk(id?.toLowerCase() === CHAIN_HEX.toLowerCase());
    });
    const onAcc = (accs: string[]) => setAddress((accs[0] as Address) ?? null);
    const onChain = (id: string) => setChainOk(id?.toLowerCase() === CHAIN_HEX.toLowerCase());
    eth.on?.("accountsChanged", onAcc);
    eth.on?.("chainChanged", onChain);
    return () => {
      eth.removeListener?.("accountsChanged", onAcc);
      eth.removeListener?.("chainChanged", onChain);
    };
  }, []);

  const connect = useCallback(async () => {
    const a = await connectWallet();
    setAddress(a);
    setChainOk(true);
  }, []);

  const switchChain = useCallback(async () => {
    await ensureStudionet();
    setChainOk(true);
  }, []);

  return { address, chainOk, connect, switchChain };
}