# v0.4.0
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json


# AI Political Warfare — a persistent online city governed by AI courts,
# AI media, AI police and AI citizens. GenLayer validators subjectively
# determine corruption, misinformation, guilt and legitimacy.
#
# Deploy on GenLayer Studio (chain 61999). Constructor takes the city name.
#
# Storage rules honoured here:
#   * TreeMap is never iterated (no .items()/.keys()/.values()) — index
#     DynArrays hold the known keys and the maps are read key-by-key.
#   * Every @gl.public.view returns a primitive (str/int) so the generated ABI
#     is statically typed and genlayer-js/viem can decode it. Structured
#     payloads are JSON-encoded strings.
#
# Safeguards (v0.4.0):
#   * Inputs are validated before any AI call (non-empty text, positive bribes,
#     sufficient funds, bounded lengths).
#   * Every consequential field returned by the validators is coerced and
#     range-checked; a malformed / non-consensual reply produces NO state
#     mutation and is logged as "unvalidated".
#   * Turn controls: a global turn counter with a per-player action budget.
#   * Replay controls: identical (sender, action, payload) submissions inside
#     the same turn are rejected.
#   * Jail lifecycle: sentences are served in turns and auto-expire.

MAX_TEXT = 1000
ACTIONS_PER_TURN = 3
TURNS_PER_JAIL_YEAR = 2
MAX_JAIL_TURNS = 20


class PoliticalWarfare(gl.Contract):
    city_name: str
    turn: bigint
    # players[address] = {"name", "faction", "reputation", "money",
    #                     "in_jail", "jail_until", "turn", "actions"}
    players: TreeMap[Address, str]
    # factions[name] = {"founder", "ideology", "members", "influence"}
    factions: TreeMap[str, str]
    # index arrays — the only supported way to enumerate map keys
    player_index: DynArray[Address]
    faction_index: DynArray[str]
    # replay guard: dedupe key -> turn it was first seen at
    action_seen: TreeMap[str, bigint]
    # propaganda log: list of json strings
    propaganda: DynArray[str]
    laws: DynArray[str]
    accusations: DynArray[str]
    bribes: DynArray[str]
    sabotages: DynArray[str]
    election_log: DynArray[str]

    def __init__(self, city_name: str):
        self.city_name = city_name
        self.turn = 1

    # ---------- validation helpers ----------
    def _vtext(self, value: str, field: str) -> str:
        text = str(value).strip()
        if not text:
            raise Exception(field + " is required")
        if len(text) > MAX_TEXT:
            raise Exception(field + " is too long")
        return text

    def _vbool(self, raw, field: str):
        # Only a real boolean counts. Anything else is unvalidated.
        if raw is True:
            return True
        if raw is False:
            return False
        return None

    def _vint(self, raw, low: int, high: int):
        if isinstance(raw, bool):
            return None
        if isinstance(raw, int):
            value = raw
        elif isinstance(raw, float):
            value = int(raw)
        elif isinstance(raw, str):
            try:
                value = int(float(raw.strip()))
            except Exception:
                return None
        else:
            return None
        if value < low:
            value = low
        if value > high:
            value = high
        return value

    def _vchoice(self, raw, allowed):
        if not isinstance(raw, str):
            return None
        value = raw.strip().lower()
        if value in allowed:
            return value
        return None

    def _vsummary(self, raw) -> str:
        if not isinstance(raw, str):
            return ""
        return raw.strip()[:280]

    def _parse(self, result: str):
        # Tolerates fenced JSON. Returns {} when the consensual output is not
        # a JSON object, which callers treat as "no consequences".
        if not isinstance(result, str):
            return {}
        text = result.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        if not isinstance(parsed, dict):
            return {}
        return parsed

    def _consensus(self, evaluate) -> str:
        return gl.eq_principle.prompt_comparative(
            evaluate,
            "Accept if both JSON outputs choose the same main decision value. Ignore differences in scores, wording, confidence, turnout, summaries, reasons, or other secondary fields.",
        )

    # ---------- storage helpers ----------
    def _read_player(self, addr: Address) -> str:
        if addr in self.players:
            return self.players[addr]
        return ""

    def _read_faction(self, name: str) -> str:
        if name in self.factions:
            return self.factions[name]
        return ""

    def _player(self, addr: Address):
        raw = self._read_player(addr)
        if not raw:
            return {}
        return json.loads(raw)

    def _save_player(self, addr: Address, p) -> None:
        self.players[addr] = json.dumps(p)

    def _faction(self, name: str):
        raw = self._read_faction(name)
        if not raw:
            return {}
        return json.loads(raw)

    def _save_faction(self, name: str, f) -> None:
        self.factions[name] = json.dumps(f)

    def _all_players(self):
        out = []
        for i in range(len(self.player_index)):
            addr = self.player_index[i]
            raw = self._read_player(addr)
            if not raw:
                continue
            p = json.loads(raw)
            p["address"] = addr.as_hex
            out.append(p)
        return out

    def _all_factions(self):
        out = []
        for i in range(len(self.faction_index)):
            name = self.faction_index[i]
            raw = self._read_faction(name)
            if not raw:
                continue
            f = json.loads(raw)
            f["name"] = name
            out.append(f)
        return out

    # ---------- turn / replay / jail lifecycle ----------
    def _release_if_served(self, p):
        if p.get("in_jail") and int(p.get("jail_until", 0)) <= int(self.turn):
            p["in_jail"] = False
            p["jail_until"] = 0
        return p

    def _jail(self, p, turns: int):
        turns = max(1, min(MAX_JAIL_TURNS, int(turns)))
        p["in_jail"] = True
        p["jail_until"] = int(self.turn) + turns
        return p

    def _spend_action(self, p):
        # Per-turn action budget. Resets automatically on a new turn.
        if int(p.get("turn", 0)) != int(self.turn):
            p["turn"] = int(self.turn)
            p["actions"] = 0
        if int(p.get("actions", 0)) >= ACTIONS_PER_TURN:
            raise Exception("Action budget exhausted for this turn")
        p["actions"] = int(p.get("actions", 0)) + 1
        return p

    def _guard(self, action: str, payload: str):
        """Validate the actor, apply jail + turn + replay rules.

        Returns (sender, player_dict) with the action already accounted for.
        The caller must persist the player via _save_player.
        """
        sender = gl.message.sender_address
        player = self._player(sender)
        if not player:
            raise Exception("Register first")
        player = self._release_if_served(player)
        if player.get("in_jail"):
            raise Exception("In jail until turn " + str(player.get("jail_until", 0)))
        key = sender.as_hex + "|" + action + "|" + str(self.turn) + "|" + payload[:200]
        if key in self.action_seen:
            raise Exception("Duplicate action already submitted this turn")
        player = self._spend_action(player)
        self.action_seen[key] = int(self.turn)
        return sender, player

    @gl.public.write
    def end_turn(self) -> None:
        self.turn = int(self.turn) + 1

    @gl.public.write
    def release_prisoner(self, address: str) -> None:
        addr = Address(address)
        p = self._player(addr)
        if not p:
            raise Exception("Unknown player")
        if not p.get("in_jail"):
            raise Exception("Not jailed")
        if int(p.get("jail_until", 0)) > int(self.turn):
            raise Exception("Sentence not served yet")
        p["in_jail"] = False
        p["jail_until"] = 0
        self._save_player(addr, p)

    # ---------- views (all return primitives) ----------
    @gl.public.view
    def get_state(self) -> str:
        return json.dumps({
            "city": self.city_name,
            "turn": int(self.turn),
            "players": self._all_players(),
            "factions": self._all_factions(),
            "propaganda": [json.loads(x) for x in self.propaganda],
            "laws": [json.loads(x) for x in self.laws],
            "accusations": [json.loads(x) for x in self.accusations],
            "bribes": [json.loads(x) for x in self.bribes],
            "sabotages": [json.loads(x) for x in self.sabotages],
            "elections": [json.loads(x) for x in self.election_log],
        })

    @gl.public.view
    def get_city_name(self) -> str:
        return self.city_name

    @gl.public.view
    def get_turn(self) -> int:
        return int(self.turn)

    @gl.public.view
    def get_player_count(self) -> int:
        return len(self.player_index)

    @gl.public.view
    def get_faction_count(self) -> int:
        return len(self.faction_index)

    @gl.public.view
    def get_player(self, address: str) -> str:
        p = self._player(Address(address))
        if not p:
            return ""
        p["address"] = address
        return json.dumps(p)

    @gl.public.view
    def get_faction(self, name: str) -> str:
        f = self._faction(name)
        if not f:
            return ""
        f["name"] = name
        return json.dumps(f)

    @gl.public.view
    def get_players(self) -> str:
        return json.dumps(self._all_players())

    @gl.public.view
    def get_factions(self) -> str:
        return json.dumps(self._all_factions())

    # ---------- player & faction setup ----------
    @gl.public.write
    def register_player(self, name: str, faction: str) -> None:
        sender = gl.message.sender_address
        if self._player(sender):
            raise Exception("Already registered")
        _name = self._vtext(name, "name")
        _faction = self._vtext(faction, "faction")
        self._save_player(sender, {
            "name": _name,
            "faction": _faction,
            "reputation": 50,
            "money": 1000,
            "in_jail": False,
            "jail_until": 0,
            "turn": int(self.turn),
            "actions": 0,
        })
        self.player_index.append(sender)
        f = self._faction(_faction)
        if f:
            f["members"] = int(f.get("members", 0)) + 1
            self._save_faction(_faction, f)

    @gl.public.write
    def create_faction(self, name: str, ideology: str) -> None:
        _name = self._vtext(name, "name")
        _ideology = self._vtext(ideology, "ideology")
        if self._faction(_name):
            raise Exception("Faction exists")
        sender = gl.message.sender_address
        self._save_faction(_name, {
            "founder": sender.as_hex,
            "ideology": _ideology,
            "members": 0,
            "influence": 50,
        })
        self.faction_index.append(_name)

    # ---------- propaganda — AI media judges effectiveness ----------
    @gl.public.write
    def spread_propaganda(self, headline: str, target_faction: str) -> None:
        _headline = self._vtext(headline, "headline")
        _target = self._vtext(target_faction, "target_faction")
        sender, player = self._guard("propaganda", _headline + "|" + _target)

        city = self.city_name

        def evaluate() -> str:
            task = f"""You are the AI Media of the city of {city}.
A propaganda headline has been published targeting faction "{_target}":

HEADLINE: {_headline}

Judge it on: believability, emotional pull, misinformation level.
Respond ONLY with a JSON object:
{{"believability": 0-100, "emotional_pull": 0-100, "misinformation": 0-100, "verdict": "viral"|"flop"|"debunked", "summary": "one sentence"}}"""
            return gl.nondet.exec_prompt(task)

        raw = self._parse(self._consensus(evaluate))
        verdict = self._vchoice(raw.get("verdict"), ["viral", "flop", "debunked"])
        validated = verdict is not None
        outcome = {
            "verdict": verdict if validated else "unvalidated",
            "believability": self._vint(raw.get("believability"), 0, 100),
            "emotional_pull": self._vint(raw.get("emotional_pull"), 0, 100),
            "misinformation": self._vint(raw.get("misinformation"), 0, 100),
            "summary": self._vsummary(raw.get("summary")),
            "validated": validated,
        }

        if validated:
            target = self._faction(_target)
            if target and verdict == "viral":
                target["influence"] = max(0, int(target["influence"]) - 10)
                self._save_faction(_target, target)
                player["reputation"] = min(100, int(player["reputation"]) + 5)
            elif verdict == "debunked":
                player["reputation"] = max(0, int(player["reputation"]) - 10)
        self._save_player(sender, player)

        self.propaganda.append(json.dumps({
            "by": sender.as_hex,
            "turn": int(self.turn),
            "headline": _headline,
            "target": _target,
            "verdict": outcome,
        }))

    # ---------- laws — propose & AI legitimacy check ----------
    @gl.public.write
    def propose_law(self, title: str, body: str) -> None:
        _title = self._vtext(title, "title")
        _body = self._vtext(body, "body")
        sender, player = self._guard("law", _title)
        self._save_player(sender, player)

        city = self.city_name

        def evaluate() -> str:
            task = f"""You are the AI Constitutional Court of {city}.
A new law has been proposed:

TITLE: {_title}
BODY: {_body}

Determine legitimacy. Respond ONLY with JSON:
{{"legitimate": true|false, "fairness": 0-100, "ruling": "one sentence reasoning"}}"""
            return gl.nondet.exec_prompt(task)

        raw = self._parse(self._consensus(evaluate))
        legitimate = self._vbool(raw.get("legitimate"), "legitimate")
        validated = legitimate is not None
        ruling = {
            "legitimate": bool(legitimate) if validated else False,
            "fairness": self._vint(raw.get("fairness"), 0, 100),
            "ruling": self._vsummary(raw.get("ruling")),
            "validated": validated,
        }

        self.laws.append(json.dumps({
            "by": sender.as_hex,
            "turn": int(self.turn),
            "title": _title,
            "body": _body,
            "ruling": ruling,
        }))

    # ---------- accusations — AI courts judge guilt ----------
    @gl.public.write
    def accuse(self, target: str, crime: str, evidence: str) -> None:
        _target = self._vtext(target, "target")
        _crime = self._vtext(crime, "crime")
        _evidence = self._vtext(evidence, "evidence")
        sender, player = self._guard("accuse", _target + "|" + _crime)
        self._save_player(sender, player)

        city = self.city_name

        def evaluate() -> str:
            task = f"""You are an AI Judge in {city}. A citizen has been accused.
ACCUSED ADDRESS: {_target}
ALLEGED CRIME: {_crime}
EVIDENCE PRESENTED: {_evidence}

Decide subjectively whether the accused is guilty. Respond ONLY with JSON:
{{"guilty": true|false, "confidence": 0-100, "sentence_years": 0-10, "opinion": "one sentence"}}"""
            return gl.nondet.exec_prompt(task)

        raw = self._parse(self._consensus(evaluate))
        guilty = self._vbool(raw.get("guilty"), "guilty")
        years = self._vint(raw.get("sentence_years"), 0, 10)
        validated = guilty is not None and (guilty is False or years is not None)
        verdict = {
            "guilty": bool(guilty) if validated else False,
            "confidence": self._vint(raw.get("confidence"), 0, 100),
            "sentence_years": years if years is not None else 0,
            "opinion": self._vsummary(raw.get("opinion")),
            "validated": validated,
        }

        if validated and guilty:
            target_addr = Address(_target)
            tp = self._player(target_addr)
            if tp:
                tp["reputation"] = max(0, int(tp["reputation"]) - 25)
                tp = self._jail(tp, max(1, int(verdict["sentence_years"]) * TURNS_PER_JAIL_YEAR))
                self._save_player(target_addr, tp)

        self.accusations.append(json.dumps({
            "by": sender.as_hex,
            "turn": int(self.turn),
            "target": _target,
            "crime": _crime,
            "verdict": verdict,
        }))

    # ---------- bribes — AI officials accept or reject ----------
    @gl.public.write
    def bribe_official(self, official_role: str, amount: int, purpose: str) -> None:
        _role = self._vtext(official_role, "official_role")
        _purpose = self._vtext(purpose, "purpose")
        _amount = self._vint(amount, -1, 1000000000)
        if _amount is None or _amount <= 0:
            raise Exception("Bribe amount must be positive")
        sender, player = self._guard("bribe", _role + "|" + str(_amount) + "|" + _purpose)
        if _amount > int(player["money"]):
            raise Exception("Not enough funds")

        city = self.city_name

        def evaluate() -> str:
            task = f"""You are an AI {_role} in {city}, with your own moral code.
A citizen offers you a bribe of {_amount} GEN to: {_purpose}.
Decide subjectively whether you accept. Some officials are corrupt, others are not.
Respond ONLY with JSON:
{{"accepted": true|false, "reason": "one sentence", "leak_risk": 0-100}}"""
            return gl.nondet.exec_prompt(task)

        raw = self._parse(self._consensus(evaluate))
        accepted = self._vbool(raw.get("accepted"), "accepted")
        leak = self._vint(raw.get("leak_risk"), 0, 100)
        validated = accepted is not None
        outcome = {
            "accepted": bool(accepted) if validated else False,
            "leak_risk": leak if leak is not None else 0,
            "reason": self._vsummary(raw.get("reason")),
            "validated": validated,
        }

        if validated:
            player["money"] = int(player["money"]) - _amount
            if accepted:
                player["reputation"] = max(0, int(player["reputation"]) - 5)
            if int(outcome["leak_risk"]) > 70:
                player["reputation"] = max(0, int(player["reputation"]) - 15)
        self._save_player(sender, player)

        self.bribes.append(json.dumps({
            "by": sender.as_hex,
            "turn": int(self.turn),
            "official": _role,
            "amount": _amount,
            "purpose": _purpose,
            "outcome": outcome,
        }))

    # ---------- sabotage rivals ----------
    @gl.public.write
    def sabotage(self, target_faction: str, plan: str) -> None:
        _target = self._vtext(target_faction, "target_faction")
        _plan = self._vtext(plan, "plan")
        sender, player = self._guard("sabotage", _target + "|" + _plan)

        city = self.city_name

        def evaluate() -> str:
            task = f"""You are the AI Police of {city} watching factions.
A player is attempting to SABOTAGE faction "{_target}" with this plan:

PLAN: {_plan}

Decide subjectively whether it succeeds and whether the saboteur is caught.
Respond ONLY with JSON:
{{"success": true|false, "caught": true|false, "damage": 0-100, "report": "one sentence"}}"""
            return gl.nondet.exec_prompt(task)

        raw = self._parse(self._consensus(evaluate))
        success = self._vbool(raw.get("success"), "success")
        caught = self._vbool(raw.get("caught"), "caught")
        damage = self._vint(raw.get("damage"), 0, 100)
        validated = success is not None and caught is not None and (success is False or damage is not None)
        outcome = {
            "success": bool(success) if validated else False,
            "caught": bool(caught) if validated else False,
            "damage": damage if damage is not None else 0,
            "report": self._vsummary(raw.get("report")),
            "validated": validated,
        }

        if validated:
            target = self._faction(_target)
            if target and success:
                target["influence"] = max(0, int(target["influence"]) - int(outcome["damage"]))
                self._save_faction(_target, target)
            if caught:
                player["reputation"] = max(0, int(player["reputation"]) - 20)
                player = self._jail(player, 2)
        self._save_player(sender, player)

        self.sabotages.append(json.dumps({
            "by": sender.as_hex,
            "turn": int(self.turn),
            "target": _target,
            "plan": _plan,
            "outcome": outcome,
        }))

    # ---------- AI citizens hold an election ----------
    @gl.public.write
    def hold_election(self) -> None:
        key = "election|" + str(self.turn)
        if key in self.action_seen:
            raise Exception("Election already held this turn")
        self.action_seen[key] = int(self.turn)

        snapshot = []
        names = []
        for f in self._all_factions():
            names.append(str(f.get("name")))
            snapshot.append({"name": f.get("name"), "ideology": f.get("ideology"), "influence": f.get("influence")})

        if not snapshot:
            self.election_log.append(json.dumps({
                "turn": int(self.turn),
                "winner": None,
                "turnout": 0,
                "validated": False,
                "summary": "No factions registered — election cancelled.",
            }))
            return

        prop_recent = []
        prop_start = max(0, len(self.propaganda) - 5)
        for i in range(prop_start, len(self.propaganda)):
            prop_recent.append(json.loads(self.propaganda[i]))

        city = self.city_name
        snapshot_json = json.dumps(snapshot)
        prop_json = json.dumps(prop_recent)

        def evaluate() -> str:
            task = f"""You are the AI Citizenry of {city}.
Factions on the ballot:
{snapshot_json}

Recent media coverage:
{prop_json}

Decide subjectively which faction wins the election based on influence and media.
Respond ONLY with JSON:
{{"winner": "<faction name>", "turnout": 0-100, "summary": "one sentence"}}"""
            return gl.nondet.exec_prompt(task)

        raw = self._parse(self._consensus(evaluate))
        winner_raw = raw.get("winner")
        winner = None
        if isinstance(winner_raw, str):
            for i in range(len(names)):
                if names[i].strip().lower() == winner_raw.strip().lower():
                    winner = names[i]
                    break
        validated = winner is not None
        turnout = self._vint(raw.get("turnout"), 0, 100)

        if validated:
            wf = self._faction(winner)
            if wf:
                wf["influence"] = min(100, int(wf["influence"]) + 20)
                self._save_faction(winner, wf)

        self.election_log.append(json.dumps({
            "turn": int(self.turn),
            "winner": winner,
            "turnout": turnout if turnout is not None else 0,
            "summary": self._vsummary(raw.get("summary")),
            "validated": validated,
        }))
