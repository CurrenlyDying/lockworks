"""
4-Qubit SIGMA Experiments
=========================

Testing the Gambit protocol with 4 logical qubits (8 physical qubits).

Experiments:
1. 4-Qubit GHZ: |0000⟩ + |1111⟩
2. Linear Chain: a→b→c→d CNOT cascade 
3. Pair Entanglement: (a,b) and (c,d) independent pairs
"""

import sys
import os
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compiler import GambitCompiler, CircuitCompiler
from src.runtime import GambitExecutionManager, GambitResult
from src.isa import Instruction, OpCode
from src.slang import SLangProgram


# =============================================================================
# EXPERIMENT DEFINITIONS
# =============================================================================

@dataclass
class Hypothesis:
    name: str
    expected_states: List[str]
    min_prob: float
    null_threshold: float
    claim: str
    null_interp: str


EXPERIMENTS = {
    "ghz4": Hypothesis(
        name="4-Qubit GHZ State",
        expected_states=["0000", "1111"],
        min_prob=0.60,
        null_threshold=0.40,
        claim="Topological entanglement extends to 4-qubit systems",
        null_interp="Decoherence overwhelms 4-qubit chains"
    ),
    
    "chain4": Hypothesis(
        name="4-Qubit CNOT Chain",
        expected_states=["0000", "1111"],
        min_prob=0.65,
        null_threshold=0.45,
        claim="Sequential topological CNOTs maintain coherence",
        null_interp="Error accumulation in long CNOT chains"
    ),
    
    "pairs": Hypothesis(
        name="Independent Entangled Pairs",
        expected_states=["0000", "0011", "1100", "1111"],
        min_prob=0.70,
        null_threshold=0.50,
        claim="Parallel 2-qubit entanglement is robust",
        null_interp="Cross-talk between independent pairs"
    ),
    
    "w_state": Hypothesis(
        name="4-Qubit W-like State",
        expected_states=["0001", "0010", "0100", "1000"],
        min_prob=0.60,
        null_threshold=0.40,
        claim="Single-excitation superposition across 4 qubits",
        null_interp="W-state preparation fails in topology"
    ),
}


# =============================================================================
# BUILD EXPERIMENTS
# =============================================================================

def build_ghz4():
    """4-Qubit GHZ: |0000⟩ + |1111⟩"""
    prog = SLangProgram("GHZ4")
    a = prog.soliton("a", "H")
    b = prog.soliton("b", 0)
    c = prog.soliton("c", 0)
    d = prog.soliton("d", 0)
    
    prog.entangle(a, b)
    prog.entangle(b, c)
    prog.entangle(c, d)
    
    prog.measure(a)
    prog.measure(b)
    prog.measure(c)
    prog.measure(d)
    
    return "ghz4", prog.compile()


def build_chain4():
    """Linear CNOT chain: a→b→c→d"""
    prog = SLangProgram("Chain4")
    a = prog.soliton("a", 1)  # Start with Fisher state
    b = prog.soliton("b", 0)
    c = prog.soliton("c", 0)
    d = prog.soliton("d", 0)
    
    prog.entangle(a, b)
    prog.entangle(b, c)
    prog.entangle(c, d)
    
    prog.measure(a)
    prog.measure(b)
    prog.measure(c)
    prog.measure(d)
    
    return "chain4", prog.compile()


def build_pairs():
    """Two independent Bell pairs: (a,b) and (c,d)"""
    prog = SLangProgram("Pairs")
    a = prog.soliton("a", "H")
    b = prog.soliton("b", 0)
    c = prog.soliton("c", "H")
    d = prog.soliton("d", 0)
    
    prog.entangle(a, b)
    prog.entangle(c, d)
    
    prog.measure(a)
    prog.measure(b)
    prog.measure(c)
    prog.measure(d)
    
    return "pairs", prog.compile()


def build_w_state():
    """W-like state: |0001⟩ + |0010⟩ + |0100⟩ + |1000⟩"""
    # Build using edge states and targeted CNOTs
    prog = SLangProgram("WState")
    a = prog.soliton("a", "H")
    b = prog.soliton("b", "H")
    c = prog.soliton("c", 0)
    d = prog.soliton("d", 0)
    
    # Cross entanglement for W-like spread
    prog.entangle(a, c)
    prog.entangle(b, d)
    
    prog.measure(a)
    prog.measure(b)
    prog.measure(c)
    prog.measure(d)
    
    return "w_state", prog.compile()


# =============================================================================
# ANALYSIS
# =============================================================================

def analyze(name: str, result: GambitResult, hyp: Hypothesis) -> Dict:
    counts = result.counts
    total = sum(counts.values())
    
    observed = sum(counts.get(s, 0) for s in hyp.expected_states) / total
    
    if observed >= hyp.min_prob:
        outcome = "SUCCESS"
        interp = hyp.claim
    elif observed >= hyp.null_threshold:
        outcome = "PARTIAL"
        interp = f"Partial: {observed:.1%} (need {hyp.min_prob:.1%})"
    else:
        outcome = "NULL"
        interp = hyp.null_interp
    
    return {
        "experiment": name,
        "outcome": outcome,
        "observed": observed,
        "threshold": hyp.min_prob,
        "interpretation": interp,
        "counts": counts,
        "dominance": result.dominance,
        "top_state": result.top_state,
    }


# =============================================================================
# MAIN
# =============================================================================

def run_4qubit_experiments():
    print("=" * 70)
    print("    4-QUBIT SIGMA EXPERIMENTS")
    print("    Testing Extended Topological Entanglement")
    print("=" * 70)
    
    experiments = {
        "ghz4": build_ghz4(),
        "chain4": build_chain4(),
        "pairs": build_pairs(),
        "w_state": build_w_state(),
    }
    
    print("\n📋 HYPOTHESES:")
    for key, hyp in EXPERIMENTS.items():
        print(f"\n  {hyp.name}:")
        print(f"    Expected: {hyp.expected_states}")
        print(f"    Success if: ≥{hyp.min_prob:.0%}")
    
    print("\n" + "=" * 70)
    print("🚀 SUBMITTING TO IBM QUANTUM...")
    print("=" * 70)
    
    manager = GambitExecutionManager()
    manager.connect()
    
    circuits = []
    names = []
    for name, (_, circuit) in experiments.items():
        circuits.append(circuit)
        names.append(name)
        print(f"   📦 {circuit.name}: {circuit.num_qubits} qubits")
    
    results = manager.run_batch(circuits)
    
    # Analyze
    print("\n" + "=" * 70)
    print("    RESULTS")
    print("=" * 70)
    
    analyses = []
    for name, result in zip(names, results):
        hyp = EXPERIMENTS[name]
        analysis = analyze(name, result, hyp)
        analyses.append(analysis)
        
        emoji = {"SUCCESS": "✅", "PARTIAL": "⚠️", "NULL": "❌"}[analysis["outcome"]]
        
        print(f"\n{emoji} {hyp.name}")
        print(f"   Outcome: {analysis['outcome']}")
        print(f"   Observed: {analysis['observed']:.1%} (need {analysis['threshold']:.1%})")
        print(f"   Top: |{analysis['top_state']}⟩ @ {analysis['dominance']:.1%}")
        print(f"   Counts: {analysis['counts']}")
        print(f"   → {analysis['interpretation']}")
    
    # Summary
    success = sum(1 for a in analyses if a["outcome"] == "SUCCESS")
    partial = sum(1 for a in analyses if a["outcome"] == "PARTIAL")
    null = sum(1 for a in analyses if a["outcome"] == "NULL")
    
    print("\n" + "=" * 70)
    print(f"SUMMARY: ✅ {success} | ⚠️ {partial} | ❌ {null}")
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"4qubit_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "backend": manager.backend.name,
            "experiments": analyses,
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return analyses


if __name__ == "__main__":
    run_4qubit_experiments()
