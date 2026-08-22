# Regnum.AI — AI Political Warfare on GenLayer

A persistent on-chain political simulation where AI judges, AI media, AI police, and AI citizens decide the fate of your faction. Built on **GenLayer** — a blockchain whose validators run LLMs and reach *subjective consensus* on outcomes no traditional smart contract could decide.

**Deployed contract:** `0x997887E63E389bB3C0ccB9Ea5fb8bfeCE4876Ad9`
**Chain:** GenLayer Studio (chainId `61999`, RPC `https://studio.genlayer.com/api`)

---

## 1. The game

You join a fictional city, create or join a faction, and fight for political dominance. Every meaningful action is judged **subjectively by an AI jury of validators**:

| Action | Who judges it | What can happen |
| --- | --- | --- |
| Spread Propaganda | AI Media | Goes viral, flops, or is publicly debunked |
| Propose a Law | AI Constitutional Court | Law is enacted or struck down as unfair/illegitimate |
| Accuse a Citizen | AI Judges | Guilt or acquittal; jail time and reputation loss |
| Bribe an Official | AI officials with individual moral codes | Bribe accepted, refused, or leaked to the press |
| Sabotage a Rival | AI Police | Sabotage succeeds or fails; you may get caught |
| Hold an Election | AI Citizenry | Weighs faction influence + recent media coverage, picks a winner |

Reputation, money, jail status and faction influence all shift based on the AI verdict. No two playthroughs are the same, and every verdict is auditable on the GenLayer explorer — you can read the model's reasoning and how validators voted.

---

## 2. Architecture

```text
 Browser (React 19 / TanStack Start)
    │  genlayer-js + viem
    ▼
 GenLayer Studio RPC  ──►  GenVM validators (LLM execution + consensus)
    │
    ▼
 political_warfare.py  (intelligent contract storage: TreeMap / DynArray)
```

### Smart contract — `contract/political_warfare.py`

- Written in Python for the **GenLayer** intelligent-contract runtime (GenVM).
- Uses `gl.nondet.exec_prompt(...)` for LLM verdicts, wrapped in
  `gl.eq_principle.prompt_comparative(...)` so multiple validators must agree on
  the same main decision before it is accepted by consensus.
- Persists players, factions, propaganda, laws, accusations, bribes, sabotages
  and election logs in on-chain `TreeMap` / `DynArray` storage.
- Pinned to the production runner:
  `# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }`

### Frontend — `src/`

- **TanStack Start** (React 19 + Vite 7), file-based routing under `src/routes`.
- **Tailwind v4** + shadcn/ui, themed with semantic tokens in `src/styles.css`.
- **genlayer-js** + **viem** for reads and transactions (`src/lib/genlayer-client.ts`).
- **MetaMask** integration with automatic add/switch to GenLayer Studio
  (`src/hooks/use-wallet.ts`).

---

## 3. Contract-side fixes applied in this build

These address the two execution failures raised during review:

**a) Illegal state iteration (the viem crash)**
`TreeMap` is a direct storage wrapper and does **not** support `.items()`,
`.keys()` or `.values()` full-state loops — calling them makes GenVM throw at
view time, so the RPC reverts and genlayer-js reports "execution failed".

Fix: the contract now keeps explicit index arrays

```python
player_index: DynArray[Address]
faction_index: DynArray[str]
```

maintained on every `create_player` / `create_faction`, and all reads
(`get_state`, `_all_players`, `_all_factions`, `hold_election`) iterate the
index array and look up each key individually. There is no `.items()` call
anywhere in the contract.

**b) ABI schema violation (complex return types)**
The ABI compiler cannot statically map `typing.Any` / nested `dict` returns, so
viem could not decode the response.

Fix: every `@gl.public.view` now returns a **primitive**. `get_state` returns a
JSON-encoded `str`, alongside typed helpers `get_player`, `get_faction`,
`get_players`, `get_factions` and the count views. Internal helpers carry no
ambiguous annotations, and storage slices are built with `range` + `append`
instead of `list(self.<storage>)`.

Frontend counterpart: `readState()` in `src/lib/contract.ts` parses the JSON
string and merges it into a typed `GameState`, falling back to a safe empty
state if parsing fails.

**c) Runner pin** — the local-only `py-genlayer:test` alias was replaced with
the supported production runner hash, which resolves the
"could not load contract schema" error in Studio.

---

## 4. Contract address is immutable

The address is a module-level constant in `src/lib/contract.ts`:

```ts
// Hard-coded, immutable deployed contract address (not user-editable).
const CONTRACT_ADDRESS = "0x9228026D3Da51Cd42f94Ca5646411d1B457D8aDC" as Address;
export const getContractAddress = (): Address => CONTRACT_ADDRESS;
```

There is **no UI input, env var, query param or localStorage override** for it.
The header renders it read-only (truncated), and every read/write call resolves
it through `getContractAddress()`. Changing the target contract requires a code
change and redeploy.

---

## 5. How to play

1. Install **MetaMask**.
2. Open the app and click **Connect Wallet** — it prompts you to add/switch to
   the GenLayer Studio network automatically.
3. Get test GEN from the GenLayer Studio faucet to pay for transactions.
4. **Create a faction** (name + ideology) or **register as a player** in an
   existing one.
5. Pick an action: Propaganda, Law, Accusation, Bribe, Sabotage, Election.
6. Confirm in MetaMask and wait ~10–30s for validators to reach consensus.
7. Watch reputation, money and faction influence update live as the verdict is
   written on-chain. The board auto-refreshes every 8 seconds.

---

## 6. Local development

```bash
bun install
bun dev          # http://localhost:8080
```

Build for production:

```bash
bun run build
```

### Redeploying the contract

1. Open [GenLayer Studio](https://studio.genlayer.com) and paste
   `contract/political_warfare.py`.
2. Deploy with constructor arg `city` (the city name).
3. Copy the new address into `CONTRACT_ADDRESS` in `src/lib/contract.ts`.

---

## 7. Project layout

```text
contract/political_warfare.py   Intelligent contract (GenVM Python)
src/routes/index.tsx            Single page route + SEO/OG metadata
src/routes/__root.tsx           Root document/layout
src/components/Header.tsx       Wallet connect + read-only contract address
src/components/GameBoard.tsx    All six actions, state panels, live refresh
src/hooks/use-wallet.ts         MetaMask account/chain tracking
src/lib/genlayer-client.ts      genlayer-js clients, chain add/switch
src/lib/contract.ts             Immutable address, readState, callWrite
src/styles.css                  Tailwind v4 theme tokens
```
