import { readClient, getWriteClient } from "./genlayer-client";
import type { Address } from "viem";
import { TransactionStatus } from "genlayer-js/types";

// Hard-coded, immutable deployed contract address (not user-editable).
const CONTRACT_ADDRESS = "0x997887E63E389bB3C0ccB9Ea5fb8bfeCE4876Ad9" as Address;
export const getContractAddress = (): Address => CONTRACT_ADDRESS;

export type GameState = {
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

const EMPTY_STATE: GameState = {
  city: "",
  players: [],
  factions: [],
  propaganda: [],
  laws: [],
  accusations: [],
  bribes: [],
  sabotages: [],
  elections: [],
};

// get_state returns a JSON-encoded string (primitive ABI type) so viem can
// decode it reliably. Parse it here.
export async function readState(addr: Address): Promise<GameState> {
  const raw = await readClient.readContract({
    address: addr,
    functionName: "get_state",
    args: [],
  });
  if (typeof raw === "string") {
    if (!raw) return EMPTY_STATE;
    try {
      return { ...EMPTY_STATE, ...(JSON.parse(raw) as GameState) };
    } catch {
      return EMPTY_STATE;
    }
  }
  return { ...EMPTY_STATE, ...((raw ?? {}) as GameState) };
}


export async function callWrite(
  user: Address,
  contract: Address,
  fn: string,
  args: any[],
) {
  const client = getWriteClient(user);
  const hash = await client.writeContract({
    address: contract,
    functionName: fn,
    args,
    value: BigInt(0),
  });
  const receipt = await readClient.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.ACCEPTED,
  });
  return { hash, receipt };
}