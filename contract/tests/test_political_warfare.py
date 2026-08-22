"""Focused tests for the state-changing safeguards of PoliticalWarfare.

Run: python3 contract/tests/test_political_warfare.py
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)            # stub `genlayer`
sys.path.insert(0, os.path.dirname(HERE))  # contract package dir

from genlayer import Address, DynArray, TreeMap, gl  # noqa: E402
from political_warfare import PoliticalWarfare  # noqa: E402

ALICE = Address("0x" + "a" * 40)
BOB = Address("0x" + "b" * 40)


def new_game(city="Testopolis"):
    c = PoliticalWarfare(city)
    c.players = TreeMap()
    c.factions = TreeMap()
    c.action_seen = TreeMap()
    c.player_index = DynArray()
    c.faction_index = DynArray()
    for name in ("propaganda", "laws", "accusations", "bribes", "sabotages", "election_log"):
        setattr(c, name, DynArray())
    return c


def as_user(addr):
    gl.message.sender_address = addr


def respond(*payloads):
    gl.nondet.responses = [p if isinstance(p, str) else json.dumps(p) for p in payloads]


class Base(unittest.TestCase):
    def setUp(self):
        self.c = new_game()
        as_user(ALICE)
        self.c.create_faction("Reds", "collectivist")
        self.c.register_player("Alice", "Reds")
        as_user(BOB)
        self.c.register_player("Bob", "Reds")
        as_user(ALICE)
        respond()


class TestInputValidation(Base):
    def test_bribe_rejects_zero_and_negative(self):
        for bad in (0, -1, -500):
            with self.assertRaises(Exception):
                self.c.bribe_official("Judge", bad, "drop the case")
        self.assertEqual(len(self.c.bribes), 0)

    def test_bribe_rejects_overdraft(self):
        with self.assertRaises(Exception):
            self.c.bribe_official("Judge", 99999, "drop the case")

    def test_empty_text_rejected(self):
        with self.assertRaises(Exception):
            self.c.spread_propaganda("   ", "Reds")
        with self.assertRaises(Exception):
            self.c.propose_law("Title", "")

    def test_bribe_deducts_only_on_validated_outcome(self):
        respond({"accepted": True, "leak_risk": 10, "reason": "greedy"})
        self.c.bribe_official("Judge", 100, "drop the case")
        self.assertEqual(self.c._player(ALICE)["money"], 900)


class TestOutputValidation(Base):
    def test_garbage_output_produces_no_mutation(self):
        respond("not json at all")
        self.c.bribe_official("Judge", 100, "drop the case")
        p = self.c._player(ALICE)
        self.assertEqual(p["money"], 1000)
        self.assertEqual(p["reputation"], 50)
        self.assertFalse(json.loads(self.c.bribes[0])["outcome"]["validated"])

    def test_non_boolean_decision_is_unvalidated(self):
        respond({"accepted": "maybe", "leak_risk": 90})
        self.c.bribe_official("Judge", 100, "x")
        self.assertEqual(self.c._player(ALICE)["money"], 1000)

    def test_unknown_verdict_label_is_rejected(self):
        respond({"verdict": "legendary", "believability": 10})
        self.c.spread_propaganda("Reds eat babies", "Reds")
        self.assertEqual(self.c._faction("Reds")["influence"], 50)
        self.assertEqual(json.loads(self.c.propaganda[0])["verdict"]["verdict"], "unvalidated")

    def test_scores_are_clamped(self):
        respond({"verdict": "viral", "believability": 500, "misinformation": -20, "emotional_pull": "80"})
        self.c.spread_propaganda("Reds eat babies", "Reds")
        v = json.loads(self.c.propaganda[0])["verdict"]
        self.assertEqual(v["believability"], 100)
        self.assertEqual(v["misinformation"], 0)
        self.assertEqual(v["emotional_pull"], 80)
        self.assertEqual(self.c._faction("Reds")["influence"], 40)

    def test_sabotage_damage_bounded_and_fenced_json_parsed(self):
        respond('```json\n{"success": true, "caught": false, "damage": 9999}\n```')
        self.c.sabotage("Reds", "cut the power")
        self.assertEqual(self.c._faction("Reds")["influence"], 0)

    def test_election_winner_must_be_on_the_ballot(self):
        respond({"winner": "Ghost Party", "turnout": 60})
        self.c.hold_election()
        log = json.loads(self.c.election_log[0])
        self.assertIsNone(log["winner"])
        self.assertFalse(log["validated"])
        self.assertEqual(self.c._faction("Reds")["influence"], 50)

    def test_election_winner_matched_case_insensitively(self):
        respond({"winner": "reds", "turnout": 300})
        self.c.hold_election()
        log = json.loads(self.c.election_log[0])
        self.assertEqual(log["winner"], "Reds")
        self.assertEqual(log["turnout"], 100)
        self.assertEqual(self.c._faction("Reds")["influence"], 70)


class TestTurnAndReplay(Base):
    def test_duplicate_action_in_same_turn_rejected(self):
        respond({"legitimate": True, "fairness": 50}, {"legitimate": True, "fairness": 50})
        self.c.propose_law("Curfew", "Nobody out after 10pm")
        with self.assertRaises(Exception):
            self.c.propose_law("Curfew", "Nobody out after 10pm")
        self.assertEqual(len(self.c.laws), 1)

    def test_same_action_allowed_after_end_turn(self):
        respond(*[{"legitimate": True} for _ in range(2)])
        self.c.propose_law("Curfew", "Nobody out after 10pm")
        self.c.end_turn()
        self.c.propose_law("Curfew", "Nobody out after 10pm")
        self.assertEqual(len(self.c.laws), 2)
        self.assertEqual(self.c.get_turn(), 2)

    def test_action_budget_per_turn(self):
        respond(*[{"legitimate": True} for _ in range(5)])
        for i in range(3):
            self.c.propose_law(f"Law {i}", "body")
        with self.assertRaises(Exception):
            self.c.propose_law("Law 4", "body")
        self.c.end_turn()
        self.c.propose_law("Law 4", "body")
        self.assertEqual(len(self.c.laws), 4)

    def test_election_once_per_turn(self):
        respond({"winner": "Reds"}, {"winner": "Reds"})
        self.c.hold_election()
        with self.assertRaises(Exception):
            self.c.hold_election()
        self.c.end_turn()
        self.c.hold_election()
        self.assertEqual(len(self.c.election_log), 2)


class TestJailLifecycle(Base):
    def _jail_bob(self, years=1):
        as_user(ALICE)
        respond({"guilty": True, "sentence_years": years, "confidence": 90})
        self.c.accuse(BOB.as_hex, "treason", "documents")

    def test_guilty_verdict_jails_with_deadline(self):
        self._jail_bob(1)
        bob = self.c._player(BOB)
        self.assertTrue(bob["in_jail"])
        self.assertEqual(bob["jail_until"], self.c.turn + 2)
        self.assertEqual(bob["reputation"], 25)

    def test_jailed_player_cannot_act(self):
        self._jail_bob(1)
        as_user(BOB)
        respond({"legitimate": True})
        with self.assertRaises(Exception):
            self.c.propose_law("Free me", "amnesty")

    def test_sentence_auto_expires(self):
        self._jail_bob(1)
        self.c.end_turn()
        self.c.end_turn()
        as_user(BOB)
        respond({"legitimate": True})
        self.c.propose_law("Free me", "amnesty")
        self.assertFalse(self.c._player(BOB)["in_jail"])

    def test_release_prisoner_requires_served_sentence(self):
        self._jail_bob(2)
        with self.assertRaises(Exception):
            self.c.release_prisoner(BOB.as_hex)
        for _ in range(4):
            self.c.end_turn()
        self.c.release_prisoner(BOB.as_hex)
        self.assertFalse(self.c._player(BOB)["in_jail"])

    def test_unvalidated_guilt_does_not_jail(self):
        as_user(ALICE)
        respond({"guilty": "probably", "sentence_years": 5})
        self.c.accuse(BOB.as_hex, "treason", "rumours")
        self.assertFalse(self.c._player(BOB)["in_jail"])

    def test_caught_saboteur_is_jailed(self):
        respond({"success": False, "caught": True, "damage": 0})
        self.c.sabotage("Reds", "leak files")
        alice = self.c._player(ALICE)
        self.assertTrue(alice["in_jail"])
        self.assertEqual(alice["reputation"], 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
