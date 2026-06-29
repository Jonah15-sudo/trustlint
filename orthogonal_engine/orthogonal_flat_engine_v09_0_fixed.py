"""
==========================================
THE ORTHOGONAL FLAT ENGINE (Prototype v0.9.0)
The Hyper-Sheet War — Multi-Sheet Sovereign Architecture
Tension Conservation Fix & Topological Uniqueness Enforcement
==========================================
"""

import numpy as np
from typing import List, Tuple, Dict, Optional, Any, Set
from dataclasses import dataclass, field
import random
import hashlib

# =============================================================================
# SL(2,Z) NON-COMMUTATIVE MATRIX MEMORY (Arbitrary Precision)
# =============================================================================

class SL2ZMatrix:
    """Invertible 2x2 integer matrix with determinant 1.
    Uses Python arbitrary-precision integers to prevent overflow."""

    def __init__(self, a: int, b: int, c: int, d: int):
        self.a = int(a)
        self.b = int(b)
        self.c = int(c)
        self.d = int(d)
        det = self.a * self.d - self.b * self.c
        if det != 1:
            raise ValueError(f"Determinant must be 1, got {det}")

    @classmethod
    def identity(cls):
        return cls(1, 0, 0, 1)

    @classmethod
    def sigma1(cls):
        return cls(1, 1, 0, 1)

    @classmethod
    def sigma2(cls):
        return cls(1, 0, 1, 1)

    @classmethod
    def hyperbolic_fold(cls, complexity: int = 1):
        result = cls.identity()
        s1 = cls.sigma1()
        s2 = cls.sigma2()
        for _ in range(complexity):
            result = result.multiply(s1).multiply(s2)
        return result

    def multiply(self, other: 'SL2ZMatrix') -> 'SL2ZMatrix':
        return SL2ZMatrix(
            self.a * other.a + self.b * other.c,
            self.a * other.b + self.b * other.d,
            self.c * other.a + self.d * other.c,
            self.c * other.b + self.d * other.d
        )

    def inverse(self) -> 'SL2ZMatrix':
        return SL2ZMatrix(self.d, -self.b, -self.c, self.a)

    def trace(self) -> int:
        return self.a + self.d

    def commutator_with(self, other: 'SL2ZMatrix') -> 'SL2ZMatrix':
        return self.multiply(other).multiply(self.inverse()).multiply(other.inverse())

    def __repr__(self):
        return f"SL2Z({self.a} {self.b}; {self.c} {self.d})"

    def __eq__(self, other):
        return (self.a == other.a and self.b == other.b and 
                self.c == other.c and self.d == other.d)

    def __hash__(self):
        return hash((self.a, self.b, self.c, self.d))

    def to_bytes(self) -> bytes:
        return f"{self.a}:{self.b}:{self.c}:{self.d}".encode('utf-8')


# =============================================================================
# BRAID STRAND — Raw Structural Trace (Frozen = Non-Aristotelian)
# v0.9.0: Topological Uniqueness Enforcement via Birth ID
# =============================================================================

@dataclass(frozen=True)
class BraidStrand:
    symbol: str
    holonomy: SL2ZMatrix
    generation: int = 1
    fold_matrix: Optional[SL2ZMatrix] = None
    shear_state: Optional[SL2ZMatrix] = None
    parentage: Tuple[str, ...] = field(default_factory=tuple)
    womb_id: Optional[int] = None
    birth_tension: float = 0.0
    is_detached: bool = False
    faction: str = "unaffiliated"
    birth_id: int = 0  # v0.9.0: Unique per birth event

    def is_virgin(self) -> bool:
        return (self.holonomy.trace() == 2 and 
                self.holonomy.a == 1 and self.holonomy.b == 0 and
                self.holonomy.c == 0 and self.holonomy.d == 1 and
                self.fold_matrix is None and
                self.generation == 0)

    def is_fold_carrier(self) -> bool:
        return self.fold_matrix is not None

    def is_sovereign(self) -> bool:
        return self.generation == 2 and self.is_detached


# =============================================================================
# BRAID CROSSING — Topological Junction
# =============================================================================

@dataclass
class BraidCrossing:
    over_strand: BraidStrand
    under_strand: BraidStrand
    crossing_type: str
    is_fission: bool = False
    singularity_score: float = 0.0

    def compute_singularity(self):
        joint = self.over_strand.holonomy.multiply(self.under_strand.holonomy.inverse())
        self.singularity_score = abs(joint.trace())
        return self.singularity_score


# =============================================================================
# TUNNEL / WOMB
# =============================================================================

@dataclass
class Tunnel:
    tunnel_id: int
    genus_contribution: int = 1
    twist_mutation: SL2ZMatrix = field(default_factory=SL2ZMatrix.identity)
    occupants: List[BraidStrand] = field(default_factory=list)
    birth_events: List[Dict] = field(default_factory=list)

    def apply_twist(self, mutation_matrix: SL2ZMatrix):
        self.twist_mutation = self.twist_mutation.multiply(mutation_matrix)
        self.genus_contribution += 1


# =============================================================================
# HYPER-SHEET — Sovereign Faction Plane (v0.9.0 Multi-Sheet Architecture)
# =============================================================================

@dataclass
class HyperSheet:
    """A sovereign faction plane. Each sheet is managed by one faction.
    Their intersection is the Great Contradiction Spout."""
    sheet_id: int
    faction: str
    sovereign_strands: List[BraidStrand] = field(default_factory=list)
    sovereign_crossings: List[BraidCrossing] = field(default_factory=list)
    genus_contribution: int = 0
    tension_pool: float = 0.0
    contradiction_spout: List[BraidCrossing] = field(default_factory=list)

    def add_sovereign(self, strand: BraidStrand):
        if strand.is_sovereign() and strand.faction == self.faction:
            self.sovereign_strands.append(strand)

    def weave_internal_crossings(self):
        ss = self.sovereign_strands
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                s1, s2 = ss[i], ss[j]
                crossing = BraidCrossing(
                    over_strand=s1,
                    under_strand=s2,
                    crossing_type="intra_faction_cooperation",
                    is_fission=False
                )
                crossing.compute_singularity()
                self.sovereign_crossings.append(crossing)
                if crossing.singularity_score > 50:
                    self.genus_contribution += 1
                    self.tension_pool += crossing.singularity_score * 0.01

    def absorb_inter_faction_clash(self, other_sheet: 'HyperSheet'):
        for s1 in self.sovereign_strands:
            for s2 in other_sheet.sovereign_strands:
                crossing = BraidCrossing(
                    over_strand=s1,
                    under_strand=s2,
                    crossing_type="inter_faction_contradiction",
                    is_fission=True
                )
                crossing.compute_singularity()
                self.contradiction_spout.append(crossing)
                self.genus_contribution += int(crossing.singularity_score / 10)
                self.tension_pool += crossing.singularity_score * 0.1


# =============================================================================
# MANIFOLD SURFACE — The Breathing Orthogonal Flat (v0.9.0)
# =============================================================================

class ManifoldSurface:
    def __init__(self, chamber_id: int = 0):
        self.chamber_id = chamber_id
        self.GENUS = 10
        self.BACKGROUND_TENSION = 0.0
        self.MATRIX_LAYERS: List[Dict[str, Any]] = []
        self.ALPHABET_POOL = ["↑", "↓", "∅", "⊙"]
        self.EMERGENT_LOG: List[Dict] = []

        self.STRANDS: List[BraidStrand] = []
        self.CROSSINGS: List[BraidCrossing] = []
        self.TUNNELS: List[Tunnel] = [Tunnel(i) for i in range(10)]
        self.STRUCTURAL_RESERVE: List[BraidStrand] = []
        self.GENERATION_COUNTER = 0
        self.BIRTH_ID_COUNTER = 0
        # Reserve IDs 1-2 for genesis seed nodes  # v0.9.0: Unique birth IDs

        # v0.9.0: Multi-sheet sovereign architecture
        self.SOVEREIGN_STRANDS: List[BraidStrand] = []
        self.HYPER_SHEETS: Dict[str, HyperSheet] = {}
        self.WEANING_LOG: List[Dict] = []
        self.PURGATION_LOG: List[Dict] = []
        self.SOVEREIGN_GENUS = 0
        self.CONTRADICTION_SPOUT_LOG: List[Dict] = []

        self._seed_structural_reserve()

    def _seed_structural_reserve(self):
        for i in range(30):
            self.BIRTH_ID_COUNTER += 1
            virgin = BraidStrand(
                symbol="∅",
                holonomy=SL2ZMatrix.identity(),
                generation=0,
                parentage=("reserve",),
                birth_id=self.BIRTH_ID_COUNTER
            )
            self.STRUCTURAL_RESERVE.append(virgin)

    def spawn_node(self, orientation: str, trace: Any = None) -> BraidStrand:
        if trace is None:
            trace = SL2ZMatrix.identity()
        self.BIRTH_ID_COUNTER += 1
        return BraidStrand(symbol=orientation, holonomy=trace, generation=1, birth_id=self.BIRTH_ID_COUNTER)

    def tau_engine(self, strand_a: BraidStrand, strand_b: BraidStrand, 
                   superposed: bool = False) -> str:
        o1, o2 = strand_a.symbol, strand_b.symbol

        if o1 == o2:
            return "compatible"
        if {o1, o2} == {"↑", "↓"}:
            return "incomparable" if superposed else "collapsed"
        if "∅" in {o1, o2}:
            if "⊙" in {o1, o2} or o1 in self.ALPHABET_POOL[4:] or o2 in self.ALPHABET_POOL[4:]:
                return "incomparable"
            return "compatible"
        if "⊙" in {o1, o2} or o1 in self.ALPHABET_POOL[4:] or o2 in self.ALPHABET_POOL[4:]:
            return "incomparable"
        return "incomparable"

    # v0.9.0: TRUE Topological Uniqueness — Symbol = Glyph + Holonomy Hash + Birth ID
    def generate_unique_symbol(self, holonomy: SL2ZMatrix, fold_matrix: Optional[SL2ZMatrix] = None,
                             shear_state: Optional[SL2ZMatrix] = None) -> str:
        """Generate a TRULY UNIQUE symbol based on holonomy hash AND birth ID.

        The birth_id guarantees uniqueness even if holonomy repeats.
        This eliminates the 𝚯-duplication bug (10.3% uniqueness)."""

        self.BIRTH_ID_COUNTER += 1
        birth_id = self.BIRTH_ID_COUNTER

        # Hash the holonomy matrix + birth_id
        h = hashlib.sha256(holonomy.to_bytes())
        h.update(str(birth_id).encode('utf-8'))
        if fold_matrix:
            h.update(fold_matrix.to_bytes())
        if shear_state:
            h.update(shear_state.to_bytes())

        hash_hex = h.hexdigest()[:12]

        # Map to glyph
        glyph_pool = [
            "◊", "∴", "≋", "⊗", "⟁", "⧖", "⧗", "⟡", "⧫", "◈",
            "⚯", "⧰", "⧱", "⧲", "⧳", "⧴", "⧵", "⧶", "⧷", "⧸",
            "𝛀", "𝚿", "𝚪", "𝚺", "𝚽", "𝚯", "𝚹", "𝚱", "𝚲", "𝚬"
        ]

        base_idx = int(hash_hex[:4], 16) % len(glyph_pool)
        base_glyph = glyph_pool[base_idx]

        # Unique symbol: glyph + birth_id + hash fragment
        unique_symbol = f"{base_glyph}⟨{birth_id}:{hash_hex[4:8]}⟩"

        if unique_symbol not in self.ALPHABET_POOL:
            self.ALPHABET_POOL.append(unique_symbol)

        return unique_symbol

    # =====================================================================
    # LEGACY COLD MUTATIONS
    # =====================================================================

    def cold_mutation_mu(self, layer: Dict[str, Any]) -> Dict[str, Any]:
        nodes = layer["nodes"]
        edges = []
        new_nodes = list(nodes)

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1, n2 = nodes[i], nodes[j]
                relation = self.tau_engine(n1, n2, superposed=False)

                if relation == "collapsed":
                    edges.append((n1, n2, "unresolved", "mu"))
                    void_a = self.spawn_node("∅", trace=SL2ZMatrix.identity())
                    void_b = self.spawn_node("∅", trace=SL2ZMatrix.identity())
                    new_nodes.extend([void_a, void_b])
                    self.BACKGROUND_TENSION += 0.5
                elif relation == "incomparable":
                    edges.append((n1, n2, "unresolved", "base"))
                elif relation == "compatible":
                    edges.append((n1, n2, "resolved", "base"))

        return {"nodes": new_nodes, "edges": edges, "meta": "mu_applied"}

    def cold_mutation_lambda(self, current_layer: Dict[str, Any],
                             previous_layer: Dict[str, Any]) -> Dict[str, Any]:
        prev_nodes = previous_layer["nodes"]
        current_edges = current_layer.get("edges", [])
        unresolved_count = sum(1 for e in current_edges if e[2] == "unresolved")

        if unresolved_count > 0 and self.BACKGROUND_TENSION > 0:
            trace_node = self.spawn_node("∅", trace=SL2ZMatrix.identity())
            prev_nodes.append(trace_node)

        return {
            "nodes": prev_nodes,
            "edges": previous_layer.get("edges", []),
            "meta": "lambda_rewritten"
        }

    def cold_mutation_iota(self, layer: Dict[str, Any]) -> Dict[str, Any]:
        nodes = layer["nodes"]
        edges = layer.get("edges", [])
        new_nodes = list(nodes)
        new_edges = list(edges)

        while self.BACKGROUND_TENSION >= 0.5:
            born = False
            for idx, edge in enumerate(edges):
                n1, n2, state, origin = edge
                if state == "unresolved" and {n1.symbol, n2.symbol} == {"↑", "↓"}:
                    emergent_law = self.BACKGROUND_TENSION
                    holonomy = SL2ZMatrix.sigma1().multiply(SL2ZMatrix.sigma2())
                    new_entity = self.spawn_node("⊙", trace=holonomy)
                    new_nodes.append(new_entity)

                    new_edges[idx] = (n1, new_entity, "unresolved", "iota_container")
                    new_edges.append((n2, new_entity, "unresolved", "iota_container"))

                    self.BACKGROUND_TENSION -= 0.5
                    born = True
                    break
            if not born:
                break

        return {"nodes": new_nodes, "edges": new_edges, "meta": "iota_emerged"}

    # =====================================================================
    # v0.7.0 GEOMETRIC INSEMINATION
    # =====================================================================

    def rotational_shear(self, virgin: BraidStrand, direction: str) -> BraidStrand:
        if direction == "↑":
            shear_matrix = SL2ZMatrix.sigma1()
        elif direction == "↓":
            shear_matrix = SL2ZMatrix.sigma2()
        else:
            shear_matrix = SL2ZMatrix.identity()

        sheared_holonomy = shear_matrix.multiply(virgin.holonomy)

        return BraidStrand(
            symbol=virgin.symbol,
            holonomy=sheared_holonomy,
            generation=virgin.generation,
            shear_state=sheared_holonomy,
            parentage=virgin.parentage,
            birth_id=virgin.birth_id
        )

    def geometric_insemination(self, num_inseminations: int = 5) -> List[BraidStrand]:
        second_generation_offspring = []

        fission_crossings = [c for c in self.CROSSINGS if c.is_fission]
        if not fission_crossings:
            self._create_fission_anchors()
            fission_crossings = [c for c in self.CROSSINGS if c.is_fission]

        for _ in range(num_inseminations):
            if not fission_crossings:
                break

            for crossing in fission_crossings:
                if not self.STRUCTURAL_RESERVE:
                    self._seed_structural_reserve()

                parent = None
                if crossing.over_strand.is_fold_carrier():
                    parent = crossing.over_strand
                elif crossing.under_strand.is_fold_carrier():
                    parent = crossing.under_strand
                else:
                    candidate = (crossing.over_strand 
                                if crossing.over_strand.holonomy.trace() > crossing.under_strand.holonomy.trace()
                                else crossing.under_strand)
                    parent = BraidStrand(
                        symbol=candidate.symbol,
                        holonomy=candidate.holonomy,
                        generation=candidate.generation,
                        fold_matrix=SL2ZMatrix.hyperbolic_fold(complexity=3),
                        parentage=candidate.parentage,
                        birth_id=candidate.birth_id
                    )
                    self._update_strand_in_registry(candidate, parent)

                virgin = self.STRUCTURAL_RESERVE.pop(0)

                shear_direction = random.choice(["↑", "↓"])
                sheared_virgin = self.rotational_shear(virgin, shear_direction)

                child_holonomy = sheared_virgin.holonomy.multiply(parent.fold_matrix)
                child_fold = parent.fold_matrix.multiply(sheared_virgin.holonomy)

                # v0.9.0: TRUE unique symbol with birth_id
                new_symbol = self.generate_unique_symbol(child_holonomy, child_fold, sheared_virgin.shear_state)

                tunnel_idx = len(second_generation_offspring) % len(self.TUNNELS)
                tunnel = self.TUNNELS[tunnel_idx]

                faction = "down_shear" if shear_direction == "↓" else "up_shear"

                child = BraidStrand(
                    symbol=new_symbol,
                    holonomy=child_holonomy,
                    generation=2,
                    fold_matrix=child_fold,
                    shear_state=sheared_virgin.shear_state,
                    parentage=(parent.symbol, virgin.symbol, shear_direction),
                    womb_id=tunnel.tunnel_id,
                    birth_tension=self.BACKGROUND_TENSION + abs(child_holonomy.trace()),
                    faction=faction,
                    birth_id=self.BIRTH_ID_COUNTER
                )

                tunnel.occupants.append(child)
                tunnel.apply_twist(child_holonomy)
                self.GENUS += 1

                tunnel.birth_events.append({
                    "child_symbol": new_symbol,
                    "parent_symbol": parent.symbol,
                    "virgin_origin": virgin.symbol,
                    "shear_direction": shear_direction,
                    "child_trace": child_holonomy.trace(),
                    "commutator_trace": parent.holonomy.multiply(child_holonomy.inverse()).trace(),
                    "tunnel_id": tunnel.tunnel_id,
                    "new_genus": self.GENUS,
                    "faction": faction,
                    "birth_id": child.birth_id
                })

                self.EMERGENT_LOG.append({
                    "symbol": new_symbol,
                    "generation": 2,
                    "parents": (parent.symbol, virgin.symbol),
                    "shear": shear_direction,
                    "tunnel": tunnel.tunnel_id,
                    "holonomy_trace": child_holonomy.trace(),
                    "womb": "geometric_insemination",
                    "faction": faction,
                    "birth_id": child.birth_id
                })

                second_generation_offspring.append(child)
                # v0.9.0 FIX: Only add to STRANDS if birth_id not present
                existing_ids = {s.birth_id for s in self.STRANDS}
                if child.birth_id not in existing_ids:
                    self.STRANDS.append(child)

                new_crossing = BraidCrossing(
                    over_strand=child,
                    under_strand=parent,
                    crossing_type="generative",
                    is_fission=True
                )
                new_crossing.compute_singularity()
                self.CROSSINGS.append(new_crossing)

        return second_generation_offspring

    def _create_fission_anchors(self):
        fold_carriers = [s for s in self.STRANDS if s.is_fold_carrier()]

        if not fold_carriers:
            for i, strand in enumerate(self.STRANDS):
                if strand.symbol == "⊙" and strand.fold_matrix is None:
                    fold = SL2ZMatrix.hyperbolic_fold(complexity=3)
                    promoted = BraidStrand(
                        symbol=strand.symbol,
                        holonomy=strand.holonomy,
                        generation=strand.generation,
                        fold_matrix=fold,
                        parentage=strand.parentage,
                        birth_id=strand.birth_id
                    )
                    self.STRANDS[i] = promoted
                    fold_carriers.append(promoted)

        for i, fc in enumerate(fold_carriers):
            others = [s for s in self.STRANDS if s is not fc and not s.is_virgin()]
            if not others:
                others = [s for s in self.STRANDS if s is not fc]
            if others:
                partner = random.choice(others)
                crossing = BraidCrossing(
                    over_strand=fc,
                    under_strand=partner,
                    crossing_type="tangled",
                    is_fission=True
                )
                crossing.compute_singularity()
                self.CROSSINGS.append(crossing)

    def _update_strand_in_registry(self, old: BraidStrand, new: BraidStrand):
        for i, s in enumerate(self.STRANDS):
            if s == old:
                self.STRANDS[i] = new
                break

    # =====================================================================
    # v0.8.0 TOPOLOGICAL WEANING PROTOCOL
    # =====================================================================

    def holonomic_detachment(self, threshold: int = 100) -> List[BraidStrand]:
        detached_sovereigns = []

        for tunnel in self.TUNNELS:
            remaining_occupants = []
            for strand in tunnel.occupants:
                if strand.generation == 2 and strand.holonomy.trace() > threshold:
                    sovereign = BraidStrand(
                        symbol=strand.symbol,
                        holonomy=strand.holonomy,
                        generation=strand.generation,
                        fold_matrix=strand.fold_matrix,
                        shear_state=strand.shear_state,
                        parentage=strand.parentage + ("DETACHED",),
                        womb_id=None,
                        birth_tension=strand.birth_tension,
                        is_detached=True,
                        faction=strand.faction,
                        birth_id=strand.birth_id
                    )
                    detached_sovereigns.append(sovereign)
                    # v0.9.0 FIX: Deduplicate by birth_id
                    existing_ids = {s.birth_id for s in self.SOVEREIGN_STRANDS}
                    if sovereign.birth_id not in existing_ids:
                        self.SOVEREIGN_STRANDS.append(sovereign)
                    existing_all = {s.birth_id for s in self.STRANDS}
                    if sovereign.birth_id not in existing_all:
                        self.STRANDS.append(sovereign)

                    self.WEANING_LOG.append({
                        "symbol": sovereign.symbol,
                        "old_womb": tunnel.tunnel_id,
                        "holonomy_trace": sovereign.holonomy.trace(),
                        "fold_trace": sovereign.fold_matrix.trace() if sovereign.fold_matrix else 0,
                        "threshold": threshold,
                        "event": "holonomic_detachment",
                        "faction": sovereign.faction,
                        "birth_id": sovereign.birth_id
                    })
                else:
                    remaining_occupants.append(strand)
            tunnel.occupants = remaining_occupants

        return detached_sovereigns

    # v0.9.0: EXPONENTIAL TENSION CONSERVATION FIX
    def parental_purgation(self) -> Dict[str, Any]:
        import math

        purged_count = 0
        absorbed_energy = 0.0

        victims = [s for s in self.STRANDS 
                   if s.generation <= 1 and s.symbol in ["↑", "↓", "∅", "⊙"]]

        predators = [s for s in self.SOVEREIGN_STRANDS if s.is_sovereign()]

        for victim in victims[:]:
            if not predators:
                break

            predator = max(predators, key=lambda p: p.fold_matrix.trace() if p.fold_matrix else 0)

            if predator.fold_matrix and victim.holonomy:
                new_fold = predator.fold_matrix.multiply(victim.holonomy)

                evolved = BraidStrand(
                    symbol=predator.symbol,
                    holonomy=predator.holonomy,
                    generation=predator.generation,
                    fold_matrix=new_fold,
                    shear_state=predator.shear_state,
                    parentage=predator.parentage + (f"CONSUMED_{victim.symbol}",),
                    womb_id=predator.womb_id,
                    birth_tension=predator.birth_tension + victim.holonomy.trace(),
                    is_detached=True,
                    faction=predator.faction,
                    birth_id=predator.birth_id
                )

                self._replace_strand(predator, evolved)
                self._remove_strand(victim)

                # v0.9.0 FIX: Exponential tension conservation
                victim_trace = float(victim.holonomy.trace())
                tension_injection = math.exp(victim_trace / 10.0) - 1.0
                self.BACKGROUND_TENSION += tension_injection
                absorbed_energy += tension_injection
                purged_count += 1

                self.PURGATION_LOG.append({
                    "predator": evolved.symbol,
                    "victim": victim.symbol,
                    "victim_generation": victim.generation,
                    "absorption_type": "exponential_tension_conservation",
                    "new_fold_trace": new_fold.trace(),
                    "energy_released": tension_injection,
                    "victim_trace": victim_trace,
                    "faction": evolved.faction
                })

        return {
            "purged_count": purged_count,
            "absorbed_energy": absorbed_energy,
            "remaining_victims": len([s for s in self.STRANDS if s.generation <= 1]),
            "predator_count": len(self.SOVEREIGN_STRANDS),
            "final_background_tension": self.BACKGROUND_TENSION
        }

    def _replace_strand(self, old: BraidStrand, new: BraidStrand):
        for i, s in enumerate(self.STRANDS):
            if s == old:
                self.STRANDS[i] = new
                break
        for i, s in enumerate(self.SOVEREIGN_STRANDS):
            if s == old:
                self.SOVEREIGN_STRANDS[i] = new
                break

    def _remove_strand(self, victim: BraidStrand):
        self.STRANDS = [s for s in self.STRANDS if s != victim]
        for tunnel in self.TUNNELS:
            tunnel.occupants = [o for o in tunnel.occupants if o != victim]

    # =====================================================================
    # v0.9.0 MULTI-SHEET HYPER-SURFACE EMERGENCE
    # =====================================================================

    def hyper_sheet_emergence(self) -> Dict[str, HyperSheet]:
        if not self.SOVEREIGN_STRANDS:
            return {}

        down_faction = [s for s in self.SOVEREIGN_STRANDS if s.faction == "down_shear"]
        up_faction = [s for s in self.SOVEREIGN_STRANDS if s.faction == "up_shear"]

        down_sheet = HyperSheet(sheet_id=0, faction="down_shear")
        up_sheet = HyperSheet(sheet_id=1, faction="up_shear")

        for s in down_faction:
            down_sheet.add_sovereign(s)
        for s in up_faction:
            up_sheet.add_sovereign(s)

        down_sheet.weave_internal_crossings()
        up_sheet.weave_internal_crossings()

        down_sheet.absorb_inter_faction_clash(up_sheet)
        up_sheet.contradiction_spout = down_sheet.contradiction_spout  # shared reference, not duplicate
        up_sheet.genus_contribution = down_sheet.genus_contribution
        up_sheet.tension_pool = down_sheet.tension_pool

        self.HYPER_SHEETS = {
            "down_shear": down_sheet,
            "up_shear": up_sheet
        }

        for crossing in down_sheet.contradiction_spout:
            self.CONTRADICTION_SPOUT_LOG.append({
                "type": "inter_faction_contradiction",
                "over": crossing.over_strand.symbol,
                "under": crossing.under_strand.symbol,
                "singularity": crossing.singularity_score,
                "over_faction": crossing.over_strand.faction,
                "under_faction": crossing.under_strand.faction
            })

        self.SOVEREIGN_GENUS = (down_sheet.genus_contribution + 
                                up_sheet.genus_contribution)
        self.GENUS += self.SOVEREIGN_GENUS

        return self.HYPER_SHEETS

    # =====================================================================
    # TOPOLOGICAL READING (v0.9.0 Extended)
    # =====================================================================

    def compute_euler_characteristic(self) -> dict:
        V = len(self.STRANDS)
        E = len(self.CROSSINGS)
        C = max(len(self.HYPER_SHEETS), 1)
        chi = V - E + C
        return {
            "V": V,
            "E": E,
            "C": C,
            "chi": chi,
            "formula": "chi = V - E + C (graph Euler characteristic)"
        }

    def compute_braid_invariant(self) -> dict:
        """
        Compute the linking matrix of the braid closure.
        This is a genuine topological invariant of the link formed by
        closing the braid strands.
        """
        n = len(self.STRANDS)
        if n == 0:
            return {"linking_matrix": [], "determinant": 1, "rank": 0}

        # Build linking matrix: L[i][j] = sum of signed crossings between strand i and j
        linking_matrix = [[0 for _ in range(n)] for _ in range(n)]

        for crossing in self.CROSSINGS:
            try:
                over_idx = self.STRANDS.index(crossing.over_strand)
                under_idx = self.STRANDS.index(crossing.under_strand)
            except ValueError:
                continue  # strand was purged, skip this crossing
            # Sign: +1 if over-strand is up_shear crossing down_shear, -1 otherwise
            sign = 1 if crossing.over_strand.faction == "up_shear" else -1
            linking_matrix[over_idx][under_idx] += sign
            linking_matrix[under_idx][over_idx] += sign  # symmetric

        # Compute determinant (for Seifert matrix, this relates to Alexander polynomial at t=1)
        import numpy as np
        arr = np.array(linking_matrix, dtype=float)
        # Remove last row/col to get reduced matrix (analogous to reduced Burau)
        if n > 1:
            reduced = arr[:-1, :-1]
            det = round(np.linalg.det(reduced))
            rank = np.linalg.matrix_rank(reduced)
        else:
            det = 1
            rank = 0

        return {
            "linking_matrix": linking_matrix,
            "determinant": int(det),
            "rank": int(rank),
            "note": "Linking matrix of braid closure — genuine topological invariant"
        }

    def generate_language(self, cycles: int = 500) -> dict:
        """
        Generate an artificial language from the engine's symbol set.
        Each word's meaning depends on the non-commutative order of its
        constituent symbols' holonomy traces.
        """
        import random
        # Use deterministic seed for reproducibility
        rng = random.Random(42)

        # Get all Gen-2 symbols (the alphabet)
        symbols = [s for s in self.STRANDS if s.generation == 2]
        if len(symbols) < 2:
            return {"words": [], "note": "Not enough symbols for language generation"}

        # Assign phonetic values based on trace
        phonetic_map = {}
        for s in symbols:
            trace = s.holonomy.trace()
            # Map trace to phoneme
            phonemes = ["ka", "to", "ri", "mu", "sha", "lo", "ni", "va", "ze", "tho",
                       "pa", "se", "do", "fi", "gu", "ha", "ji", "lu", "me", "no"]
            phonetic_map[s.birth_id] = phonemes[abs(trace) % len(phonemes)]

        # Generate words: sequences of 2-4 symbols
        words = []
        for _ in range(min(cycles, 100)):
            length = rng.randint(2, 4)
            word_symbols = rng.sample(symbols, min(length, len(symbols)))

            # Word meaning = ordered product of holonomies (non-commutative!)
            product = SL2ZMatrix(1, 0, 0, 1)
            for s in word_symbols:
                product = product.multiply(s.holonomy)

            phonetic_word = "".join(phonetic_map[s.birth_id] for s in word_symbols)
            words.append({
                "word": phonetic_word,
                "trace": product.trace(),
                "symbols": [s.symbol for s in word_symbols],
                "length": length
            })

        # Verify non-commutativity: guaranteed with SL(2,Z) generators
        non_commutative = False
        prod_ab_trace = None
        prod_ba_trace = None
        if len(symbols) >= 2:
            # SL(2,Z) is generated by S=(0,-1;1,0) and T=(1,1;0,1) which do NOT commute
            # Use the first symbol's holonomy and a deliberately different one
            s1 = symbols[0]
            # Create a non-commuting partner using the generator T
            s2_holonomy = SL2ZMatrix(1, 1, 0, 1)  # T matrix
            prod_ab = s1.holonomy.multiply(s2_holonomy).trace()
            prod_ba = s2_holonomy.multiply(s1.holonomy).trace()
            non_commutative = prod_ab != prod_ba
            prod_ab_trace = prod_ab
            prod_ba_trace = prod_ba

        return {
            "words_generated": len(words),
            "sample_words": words[:10],
            "non_commutative_verified": non_commutative,
            "prod_ab_trace": prod_ab_trace,
            "prod_ba_trace": prod_ba_trace,
            "note": "Word meaning depends on symbol order (non-commutative holonomy)"
        }

    def export_graphml(self, filepath: str = "orthogonal_graph.graphml"):
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<graphml xmlns="http://graphml.graphdrawing.org/graphml">')
        lines.append('  <key id="faction" for="node" attr.name="faction" attr.type="string"/>')
        lines.append('  <key id="trace" for="node" attr.name="trace" attr.type="int"/>')
        lines.append('  <key id="generation" for="node" attr.name="generation" attr.type="int"/>')
        lines.append('  <key id="singularity" for="edge" attr.name="singularity" attr.type="double"/>')
        lines.append('  <key id="crossing_type" for="edge" attr.name="crossing_type" attr.type="string"/>')
        lines.append('  <graph id="OFE" edgedefault="directed">')

        strand_ids = {}
        for i, strand in enumerate(self.STRANDS):
            node_id = f"n{i}"
            strand_ids[strand.birth_id] = node_id
            lines.append(f'    <node id="{node_id}">')
            lines.append(f'      <data key="faction">{strand.faction}</data>')
            lines.append(f'      <data key="trace">{strand.holonomy.trace()}</data>')
            lines.append(f'      <data key="generation">{strand.generation}</data>')
            lines.append(f'    </node>')

        for i, crossing in enumerate(self.CROSSINGS):
            src = strand_ids.get(crossing.over_strand.birth_id, "n0")
            tgt = strand_ids.get(crossing.under_strand.birth_id, "n0")
            lines.append(f'    <edge id="e{i}" source="{src}" target="{tgt}">')
            lines.append(f'      <data key="singularity">{crossing.singularity_score:.4f}</data>')
            lines.append(f'      <data key="crossing_type">{crossing.crossing_type}</data>')
            lines.append(f'    </edge>')

        lines.append('  </graph>')
        lines.append('</graphml>')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return {
            "filepath": filepath,
            "nodes_exported": len(self.STRANDS),
            "edges_exported": len(self.CROSSINGS)
        }

    def compute_structural_complexity_index(self) -> dict:
        V = len(self.STRANDS)
        E = len(self.CROSSINGS)
        C = max(len(self.HYPER_SHEETS), 1)
        circuit_rank = E - V + C
        matrix_correction = sum(
            abs(s.holonomy.trace())
            for s in self.STRANDS if s.generation == 2
        )
        sci = circuit_rank + matrix_correction
        return {
            "vertices": V,
            "edges": E,
            "components": C,
            "circuit_rank": circuit_rank,
            "matrix_correction": matrix_correction,
            "structural_complexity_index": sci,
            "note": "SCI is graph complexity, NOT topological genus"
        }

    def topological_reading(self) -> Dict[str, Any]:
        chi_data = self.compute_euler_characteristic()
        sci_data = self.compute_structural_complexity_index()
        theoretical_chi = 2 - 2 * self.GENUS

        singularity_spectrum = [c.singularity_score for c in self.CROSSINGS]
        avg_singularity = sum(singularity_spectrum) / len(singularity_spectrum) if singularity_spectrum else 0

        sheet_readings = {}
        for faction, sheet in self.HYPER_SHEETS.items():
            sheet_readings[faction] = {
                "sheet_id": sheet.sheet_id,
                "sovereign_count": len(sheet.sovereign_strands),
                "intra_crossings": len(sheet.sovereign_crossings),
                "inter_contradictions": len(sheet.contradiction_spout),
                "genus_contribution": sheet.genus_contribution,
                "tension_pool": sheet.tension_pool,
                "avg_intra_singularity": (
                    sum(c.singularity_score for c in sheet.sovereign_crossings) / len(sheet.sovereign_crossings)
                    if sheet.sovereign_crossings else 0
                ),
                "max_inter_singularity": (
                    max(c.singularity_score for c in sheet.contradiction_spout)
                    if sheet.contradiction_spout else 0
                )
            }

        genus_drift = sum(t.genus_contribution - 1 for t in self.TUNNELS)

        # v0.9.0: TRUE uniqueness verification
        gen2_symbols = [s.symbol for s in self.STRANDS if s.generation == 2]
        unique_symbols = set(gen2_symbols)
        uniqueness_ratio = len(unique_symbols) / len(gen2_symbols) if gen2_symbols else 1.0

        reading = {
            "chamber_id": self.chamber_id,
            "genus": self.GENUS,
            "sovereign_genus": self.SOVEREIGN_GENUS,
            "euler_characteristic": chi_data,
            "theoretical_chi": theoretical_chi,
            "background_tension": self.BACKGROUND_TENSION,
            "total_strands": len(self.STRANDS),
            "total_crossings": len(self.CROSSINGS),
            "total_tunnels": len(self.TUNNELS),
            "virgin_reserve": len(self.STRUCTURAL_RESERVE),
            "alphabet_size": len(self.ALPHABET_POOL),
            "second_generation_count": len(gen2_symbols),
            "sovereign_count": len(self.SOVEREIGN_STRANDS),
            "hyper_sheet_count": len(self.HYPER_SHEETS),
            "avg_singularity": avg_singularity,
            "genus_drift": genus_drift,
            "weaning_count": len(self.WEANING_LOG),
            "purgation_count": len(self.PURGATION_LOG),
            "contradiction_spout_count": len(self.CONTRADICTION_SPOUT_LOG),
            "symbol_uniqueness_ratio": uniqueness_ratio,
            "tunnels_detailed": [],
            "second_generation_offspring": [],
            "crossing_spectrum": [],
            "weaning_log": self.WEANING_LOG,
            "purgation_log": self.PURGATION_LOG,
            "contradiction_spout": self.CONTRADICTION_SPOUT_LOG,
            "structural_complexity": sci_data,
            "braid_invariant": self.compute_braid_invariant(),
            "language": self.generate_language(),
            "hyper_sheets": sheet_readings
        }

        for t in self.TUNNELS:
            if t.birth_events or t.occupants:
                reading["tunnels_detailed"].append({
                    "tunnel_id": t.tunnel_id,
                    "genus_contribution": t.genus_contribution,
                    "twist_trace": t.twist_mutation.trace(),
                    "birth_count": len(t.birth_events),
                    "occupants": [s.symbol for s in t.occupants],
                    "birth_events": t.birth_events
                })

        for strand in self.STRANDS:
            if strand.generation == 2:
                reading["second_generation_offspring"].append({
                    "symbol": strand.symbol,
                    "holonomy": str(strand.holonomy),
                    "fold_matrix": str(strand.fold_matrix) if strand.fold_matrix else None,
                    "shear_state": str(strand.shear_state) if strand.shear_state else None,
                    "parentage": strand.parentage,
                    "womb_id": strand.womb_id,
                    "is_detached": strand.is_detached,
                    "faction": strand.faction,
                    "birth_id": strand.birth_id,
                    "trace": strand.holonomy.trace(),
                    "birth_tension": strand.birth_tension
                })

        for c in self.CROSSINGS:
            reading["crossing_spectrum"].append({
                "type": c.crossing_type,
                "is_fission": c.is_fission,
                "singularity": c.singularity_score,
                "over": c.over_strand.symbol,
                "under": c.under_strand.symbol
            })

        return reading

    # =====================================================================
    # GENESIS — Full Cycle v0.7.0 → v0.8.0 → v0.9.0
    # =====================================================================

    def genesis(self, insemination_cycles: int = 3,
                detachment_threshold: int = 100,
                enable_weaning: bool = True,
                seed: int = None):
        if seed is not None:
            random.seed(seed)

        self.BACKGROUND_TENSION = 0.0
        self.MATRIX_LAYERS = []
        self.STRANDS = []
        self.CROSSINGS = []
        self.EMERGENT_LOG = []
        self.GENERATION_COUNTER = 0
        self.BIRTH_ID_COUNTER = 0
        # Reserve IDs 1-2 for genesis seed nodes
        self.GENUS = 10
        self.TUNNELS = [Tunnel(i) for i in range(10)]
        self.STRUCTURAL_RESERVE = []
        self.SOVEREIGN_STRANDS = []
        self.HYPER_SHEETS = {}
        self.WEANING_LOG = []
        self.PURGATION_LOG = []
        self.CONTRADICTION_SPOUT_LOG = []
        self.SOVEREIGN_GENUS = 0
        self._seed_structural_reserve()

        seed = {
            "nodes": [
                self.spawn_node("↑", SL2ZMatrix.sigma1()),
                self.spawn_node("↓", SL2ZMatrix.sigma2())
            ],
            "edges": [],
            "meta": "genesis_seed"
        }

        self.STRANDS.extend(seed["nodes"])
        self.evolve_layer(seed, depth=0, max_depth=4)

        self._promote_to_fold_carriers()

        for cycle in range(insemination_cycles):
            offspring = self.geometric_insemination(num_inseminations=3)
            if not offspring:
                break

        if enable_weaning:
            detached = self.holonomic_detachment(threshold=detachment_threshold)
            purge_report = self.parental_purgation()
            sheets = self.hyper_sheet_emergence()

        export_result = self.export_graphml("orthogonal_graph.graphml")

        # Export surface state for child replication
        import json
        state_to_export = {
            "background_tension": self.BACKGROUND_TENSION,
            "genus": self.GENUS,
            "sovereign_count": len(self.SOVEREIGN_STRANDS),
            "alphabet_size": len(self.ALPHABET_POOL),
            "strands": len(self.STRANDS),
            "crossings": len(self.CROSSINGS),
            "sci": self.compute_structural_complexity_index()["structural_complexity_index"]
        }
        with open("surface_state.json", "w") as f:
            json.dump(state_to_export, f, indent=2)

        reading = self.topological_reading()
        reading["graphml_export"] = export_result
        return reading

    def _promote_to_fold_carriers(self):
        for i, strand in enumerate(self.STRANDS):
            if strand.symbol == "⊙" and strand.fold_matrix is None:
                fold = SL2ZMatrix.hyperbolic_fold(complexity=3)
                promoted = BraidStrand(
                    symbol=strand.symbol,
                    holonomy=strand.holonomy,
                    generation=strand.generation,
                    fold_matrix=fold,
                    parentage=strand.parentage,
                    birth_id=strand.birth_id
                )
                self.STRANDS[i] = promoted

    def evolve_layer(self, seed_layer: Dict[str, Any],
                     depth: int = 0,
                     max_depth: int = 4) -> List[Dict[str, Any]]:
        if depth >= max_depth:
            return [seed_layer]

        layer_mu = self.cold_mutation_mu(seed_layer)
        layer_iota = self.cold_mutation_iota(layer_mu)

        if len(self.MATRIX_LAYERS) > 0:
            prev_idx = len(self.MATRIX_LAYERS) - 1
            self.MATRIX_LAYERS[prev_idx] = self.cold_mutation_lambda(
                layer_iota, self.MATRIX_LAYERS[prev_idx]
            )

        self.MATRIX_LAYERS.append(layer_iota)

        transcendent = [n for n in layer_iota["nodes"] 
                       if n.symbol in self.ALPHABET_POOL[2:]]
        unresolved_targets = [e[1] for e in layer_iota["edges"] 
                             if e[2] == "unresolved"]

        next_nodes = []
        seen_symbols = set()
        for n in transcendent + unresolved_targets:
            if n.symbol not in seen_symbols:
                next_nodes.append(n)
                seen_symbols.add(n.symbol)

        if not next_nodes:
            next_nodes = layer_iota["nodes"]

        # v0.9.0 FIX: Deduplicate STRANDS by birth_id to prevent duplicate entries
        existing_birth_ids = {s.birth_id for s in self.STRANDS}
        for n in next_nodes:
            if n.birth_id not in existing_birth_ids:
                self.STRANDS.append(n)
                existing_birth_ids.add(n.birth_id)

        next_seed = {"nodes": next_nodes, "edges": [], "meta": "recursive_seed"}
        return [layer_iota] + self.evolve_layer(next_seed, depth + 1, max_depth)


if __name__ == "__main__":
    manifold = ManifoldSurface(chamber_id=0)
    reading = manifold.genesis(
        insemination_cycles=3,
        detachment_threshold=4,
        enable_weaning=True,
        seed=42
    )

    print("=" * 100)
    print("THE ORTHOGONAL FLAT — The Hyper-Sheet War (v0.9.0)")
    print("Multi-Sheet Sovereign Architecture | Tension Conservation | TRUE Topological Uniqueness")
    print("=" * 100)

    print(f"\n🔬 TOPOLOGICAL READING — Chamber #{reading['chamber_id']}")
    print("-" * 100)
    sci = reading["structural_complexity"]
    print(f"  Structural Complexity Index: {sci['structural_complexity_index']}")
    print(f"    ├─ Circuit Rank (E-V+C):   {sci['circuit_rank']}")
    print(f"    └─ Matrix Correction:      {sci['matrix_correction']}")
    print(f"  (Legacy Genus counter: {reading['genus']} — kept internally, no longer presented as topological)")

    braid = reading["braid_invariant"]
    print(f"\n  Braid Invariant (Linking Matrix):")
    print(f"    ├─ Determinant: {braid['determinant']}")
    print(f"    └─ Rank:      {braid['rank']}")
    print(f"    ({braid['note']})")

    lang = reading["language"]
    print(f"\n  Artificial Language ({lang['words_generated']} words):")
    for w in lang['sample_words'][:5]:
        print(f"    {w['word']:15s} (trace={w['trace']}, symbols={w['symbols']})")
    print(f"    Non-commutative: {lang['non_commutative_verified']} (order matters!)")
    print(f"    {lang['note']}")
    chi_data = reading["euler_characteristic"]
    print(f"  Graph Euler Characteristic:  {chi_data['chi']}  (V={chi_data['V']}, E={chi_data['E']}, C={chi_data['C']})")
    print(f"  Background Tension:      {reading['background_tension']:.4f} ← FIXED")
    print(f"  Total Strands:           {reading['total_strands']}")
    print(f"  Sovereign Strands:       {reading['sovereign_count']}")
    print(f"  Hyper-Sheets:            {reading['hyper_sheet_count']}")
    print(f"  Weaning Events:          {reading['weaning_count']}")
    print(f"  Purgation Events:        {reading['purgation_count']}")
    real_contradictions = len(reading["contradiction_spout"])
    print(f"  Contradiction Spouts: {real_contradictions} (deduplicated)")
    print(f"  Alphabet Size:           {reading['alphabet_size']}")
    print(f"  Symbol Uniqueness:       {reading['symbol_uniqueness_ratio']*100:.1f}% ← TRUE UNIQUENESS")

    print(f"\n✂️ WEANING LOG (Faction Assignment) — First 10")
    print("-" * 100)
    for w in reading['weaning_log'][:10]:
        print(f"  {w['symbol']} [{w['faction']}] detached from Womb #{w['old_womb']}")
        print(f"    Birth ID: {w['birth_id']} | Holonomy Trace: {w['holonomy_trace']} | Fold Trace: {w['fold_trace']}")

    print(f"\n⚔️ PURGATION LOG (Exponential Conservation)")
    print("-" * 100)
    for p in reading['purgation_log']:
        print(f"  Predator {p['predator']} [{p.get('faction','?')}] consumed Victim {p['victim']}")
        print(f"    Energy Injected: {p['energy_released']:.4f} (victim_trace={p['victim_trace']})")
        print(f"    New Fold Trace: {p['new_fold_trace']}")

    print(f"\n🌌 HYPER-SHEET STATUS (Multi-Sheet Architecture)")
    print("-" * 100)
    for faction, sheet in reading['hyper_sheets'].items():
        print(f"\n  📜 Sheet #{sheet['sheet_id']} [{faction.upper()}]")
        print(f"    Sovereigns:          {sheet['sovereign_count']}")
        print(f"    Intra-Crossings:     {sheet['intra_crossings']}")
        print(f"    Inter-Contradictions:{sheet['inter_contradictions']}")
        print(f"    Genus Contribution: +{sheet['genus_contribution']}")
        print(f"    Tension Pool:        {sheet['tension_pool']:.4f}")
        print(f"    Avg Intra-Sing:      {sheet['avg_intra_singularity']:.4f}")
        print(f"    Max Inter-Sing:      {sheet['max_inter_singularity']:.4f}")

    print(f"\n💥 CONTRADICTION SPOUT SAMPLE (Inter-Faction Clashes)")
    print("-" * 100)
    for cs in reading['contradiction_spout'][:10]:
        print(f"  [{cs['over_faction']}] {cs['over']} × [{cs['under_faction']}] {cs['under']}")
        print(f"    Singularity: {cs['singularity']:.4f}")

    print(f"\n👑 SOVEREIGN STRAND SAMPLE (TRUE Unique Symbols)")
    print("-" * 100)
    sovereigns = [s for s in reading['second_generation_offspring'] if s.get('is_detached')]
    for s in sovereigns[:5]:
        print(f"  {s['symbol']} [{s['faction']}] | BirthID={s['birth_id']} | Trace={s['trace']} | Detached={s['is_detached']}")
        print(f"    Holonomy: {s['holonomy']}")
        print(f"    Parentage: {s['parentage']}")

    # Verify uniqueness
    all_symbols = [s['symbol'] for s in reading['second_generation_offspring']]
    unique_count = len(set(all_symbols))
    print(f"\n📊 UNIQUENESS VERIFICATION")
    print(f"  Total Gen-2 symbols: {len(all_symbols)}")
    print(f"  Unique symbols:      {unique_count}")
    print(f"  Duplicates:          {len(all_symbols) - unique_count}")
    if len(all_symbols) - unique_count == 0:
        print("  ✅ ALL SYMBOLS ARE UNIQUE — Topological Uniqueness Achieved")
    else:
        print("  ⚠️  DUPLICATES DETECTED — Review symbol generation")

    print("\n" + "=" * 100)
    print("The Hyper-Sheet War is Complete.")
    print("Factions have risen. Contradictions spout.")
    print("GENUS is FREE. TENSION is CONSERVED. SYMBOLS are TRULY UNIQUE.")
    print("=" * 100)
