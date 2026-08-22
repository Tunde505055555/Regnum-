import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import type { Address } from "viem";

export const CHAIN_ID = 61999;
export const CHAIN_HEX = "0xF22F";
export const RPC_URL = "https://studio.genlayer.com/api";

export const readClient = createClient({ chain: studionet });

export function getWriteClient(address: Address) {
  if (typeof window === "undefined" || !(window as any).ethereum) {
    throw new Error("MetaMask not found");
  }
  return createClient({
    chain: studionet,
    account: address,
    endpoint: RPC_URL,
    provider: (window as any).ethereum,
  } as any);
}

export async function ensureStudionet() {
  const eth = (window as any).ethereum;
  if (!eth) throw new Error("MetaMask not found");
  try {
    await eth.request({ method: "wallet_switchEthereumChain", params: [{ chainId: CHAIN_HEX }] });
  } catch (err: any) {
    if (err?.code === 4902) {
      await eth.request({
        method: "wallet_addEthereumChain",
        params: [{
          chainId: CHAIN_HEX,
          chainName: "GenLayer Studio",
          nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
          rpcUrls: [RPC_URL],
          blockExplorerUrls: ["https://explorer-studio.genlayer.com/"],
        }],
      });
    } else {
      throw err;
    }
  }
}

export async function connectWallet(): Promise<Address> {
  const eth = (window as any).ethereum;
  if (!eth) throw new Error("MetaMask not installed");
  const accounts: string[] = await eth.request({ method: "eth_requestAccounts" });
  await ensureStudionet();
  return accounts[0] as Address;
}