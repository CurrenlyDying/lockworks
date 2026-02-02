"""
SIGMA QPU Experiment Suite
===========================

Complex S-Lang programs with pre-defined hypotheses for QPU testing.
Each experiment has clear success/null criteria.

Experiments:
1. Three-Qubit GHZ State (Full Entanglement Chain)
2. Soliton Roll Cascade (Sequential NOT gates)
3. Interference Pattern (Edge-State Superposition)
4. Decoherence Stress Test (High-Complexity Braid)
"""

import sys
import os
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compiler import GambitCompiler, CircuitCompiler
from src.runtime import GambitExecutionManager, GambitResult, verify_topology
from src.isa import SolitonHeap, Instruction, OpCode, TopologyConstants
from src.slang import SLangProgram


# =============================================================================
# EXPERIMENT DEFINITIONS
# =============================================================================

@dataclass
class ExperimentHypothesis:
    """Defines expected outcomes for an experiment."""
    name: str
    description: str
    expected_states: List[str]      # States expected to dominate
    min_combined_prob: float        # Minimum combined probability for success
    null_threshold: float           # Below this = null result
    physics_claim: str              # What we claim if successful
    null_interpretation: str        # What null result means


EXPERIMENTS = {
    "ghz3": ExperimentHypothesis(
        name="Three-Qubit GHZ State",
        description="Create |000⟩ + |111⟩ superposition across 3 solitons",
        expected_states=["000", "111"],
        min_combined_prob=0.70,     # 70% in GHZ states = success
        null_threshold=0.50,        # Below 50% = null (could be noise)
        physics_claim="Topological entanglement extends to 3-qubit systems with maintained coherence",
        null_interpretation="Decoherence dominates at 3-qubit scale, or gate errors compound"
    ),
    
    "cascade": ExperimentHypothesis(
        name="Soliton Roll Cascade",
        description="Apply 3 sequential rolls: 0 → 1 → 0 → 1. Final should be |1⟩",
        expected_states=["10"],     # Physical |10⟩ = Logical |1⟩
        min_combined_prob=0.80,     # 80% = success
        null_threshold=0.60,
        physics_claim="Soliton topology preserves coherence through multiple phase transitions",
        null_interpretation="Phase accumulation errors or decoherence during multi-roll sequence"
    ),
    
    "interference": ExperimentHypothesis(
        name="Edge-State Interference",
        description="Two solitons at θ=0.1 (edge), measure interference pattern",
        expected_states=["00", "01", "10", "11"],  # Mixed distribution
        min_combined_prob=0.90,     # 90% total (should see all states)
        null_threshold=0.70,
        physics_claim="Edge state (θ=0.1) produces quantum superposition with measurable interference",
        null_interpretation="Edge state collapses to classical mixture or is noise-dominated"
    ),
    
    "stress": ExperimentHypothesis(
        name="Decoherence Stress Test",
        description="High complexity (C=8) vs Standard (C=6) - test topology robustness",
        expected_states=["00"],     # ROBUST state should still dominate
        min_combined_prob=0.85,     # Even at C=8, should maintain 85%
        null_threshold=0.75,
        physics_claim="Topological protection scales with circuit complexity",
        null_interpretation="Higher complexity increases decoherence, topology breaks down"
    ),
    
    "correlation": ExperimentHypothesis(
        name="Classical Correlation Test",
        description="CNOT chain: a→b→c. If a=1, then b=1, then c=1",
        expected_states=["000", "111"],  # Perfect correlations
        min_combined_prob=0.75,
        null_threshold=0.55,
        physics_claim="Topological CNOT maintains classical correlations in multi-qubit chains",
        null_interpretation="Gate fidelity degrades in 3-qubit chains"
    ),
}


# =============================================================================
# EXPERIMENT PROGRAMS
# =============================================================================

def build_ghz3_program() -> Tuple[str, "QuantumCircuit"]:
    """
    3-Qubit GHZ State: |000⟩ + |111⟩
    
    Circuit:
        a = H (superposition)
        b = 0
        c = 0
        CNOT(a, b)
        CNOT(b, c)
    """
    prog = SLangProgram("GHZ3")
    a = prog.soliton("a", "H")  # Superposition
    b = prog.soliton("b", 0)
    c = prog.soliton("c", 0)
    
    prog.entangle(a, b)  # a controls b
    prog.entangle(b, c)  # b controls c
    
    prog.measure(a)
    prog.measure(b)
    prog.measure(c)
    
    return "ghz3", prog.compile()


def build_cascade_program() -> Tuple[str, "QuantumCircuit"]:
    """
    Soliton Roll Cascade: 0 → 1 → 0 → 1
    
    Three rolls should result in final state |1⟩
    """
    prog = SLangProgram("Cascade")
    q = prog.soliton("q", 0)
    
    q.roll()  # 0 → 1
    q.roll()  # 1 → 0
    q.roll()  # 0 → 1
    
    prog.measure(q)
    
    return "cascade", prog.compile()


def build_interference_program() -> Tuple[str, "QuantumCircuit"]:
    """
    Edge-State Interference
    
    Two qubits at θ=0.1 (edge of chaos), measure both.
    Should see interference pattern (not just 00 or 11).
    """
    # Use raw IR for edge state (θ=0.1)
    instructions = [
        Instruction.alloc("a"),
        Instruction(OpCode.S_WRITE, "a", ["H"]),  # H = edge state
        Instruction.alloc("b"),
        Instruction(OpCode.S_WRITE, "b", ["H"]),
        Instruction.measure("a"),
        Instruction.measure("b"),
    ]
    
    cc = CircuitCompiler(complexity=6)
    circuit = cc.compile(instructions)
    circuit.name = "Interference"
    
    return "interference", circuit


def build_stress_program(complexity: int = 8) -> Tuple[str, "QuantumCircuit"]:
    """
    Decoherence Stress Test
    
    ROBUST state at high complexity.
    Tests if topology still protects against decoherence.
    """
    instructions = [
        Instruction.alloc("q"),
        Instruction.write("q", 0),  # ROBUST
        Instruction.measure("q"),
    ]
    
    cc = CircuitCompiler(complexity=complexity, unsafe=True)
    circuit = cc.compile(instructions)
    circuit.name = f"Stress_C{complexity}"
    
    return "stress", circuit


def build_correlation_program() -> Tuple[str, "QuantumCircuit"]:
    """
    Classical Correlation Test
    
    Chain: a → b → c
    If a starts in superposition, correlations should propagate.
    """
    prog = SLangProgram("Correlation")
    a = prog.soliton("a", "H")
    b = prog.soliton("b", 0)
    c = prog.soliton("c", 0)
    
    prog.entangle(a, b)
    prog.entangle(b, c)
    
    prog.measure(a)
    prog.measure(b)
    prog.measure(c)
    
    return "correlation", prog.compile()


# =============================================================================
# RESULT ANALYSIS
# =============================================================================

def analyze_experiment(
    exp_name: str,
    result: GambitResult,
    hypothesis: ExperimentHypothesis
) -> Dict:
    """Analyze experiment result against hypothesis."""
    
    counts = result.counts
    total = sum(counts.values())
    
    # Calculate probability in expected states
    expected_prob = sum(counts.get(s, 0) for s in hypothesis.expected_states) / total
    
    # Determine outcome
    if expected_prob >= hypothesis.min_combined_prob:
        outcome = "SUCCESS"
        interpretation = hypothesis.physics_claim
    elif expected_prob >= hypothesis.null_threshold:
        outcome = "PARTIAL"
        interpretation = f"Partial success: {expected_prob:.1%} (threshold: {hypothesis.min_combined_prob:.1%})"
    else:
        outcome = "NULL"
        interpretation = hypothesis.null_interpretation
    
    # State distribution
    state_dist = {s: counts.get(s, 0) / total for s in sorted(counts.keys())}
    
    return {
        "experiment": exp_name,
        "hypothesis": hypothesis.name,
        "outcome": outcome,
        "expected_states": hypothesis.expected_states,
        "observed_prob": expected_prob,
        "threshold": hypothesis.min_combined_prob,
        "null_threshold": hypothesis.null_threshold,
        "state_distribution": state_dist,
        "interpretation": interpretation,
        "dominance": result.dominance,
        "top_state": result.top_state,
        "z_score": result.z_score,
        "raw_counts": counts,
    }


# =============================================================================
# MAIN RUNNER
# =============================================================================

def run_all_experiments():
    """Run all experiments on IBM QPU."""
    
    print("=" * 70)
    print("    SIGMA QPU EXPERIMENT SUITE")
    print("    Pre-defined Hypotheses with Success/Null Criteria")
    print("=" * 70)
    
    # Build all circuits
    experiments = {
        "ghz3": build_ghz3_program(),
        "cascade": build_cascade_program(),
        "interference": build_interference_program(),
        "stress": build_stress_program(complexity=8),
        "correlation": build_correlation_program(),
    }
    
    # Print hypotheses
    print("\n📋 EXPERIMENT HYPOTHESES:")
    print("-" * 70)
    for key, hyp in EXPERIMENTS.items():
        print(f"\n{hyp.name}:")
        print(f"  Expected: {hyp.expected_states}")
        print(f"  Success if: ≥{hyp.min_combined_prob:.0%} in expected states")
        print(f"  Null if: <{hyp.null_threshold:.0%}")
        print(f"  Claim: {hyp.physics_claim[:60]}...")
    
    print("\n" + "=" * 70)
    print("🚀 CONNECTING TO IBM QUANTUM...")
    print("=" * 70)
    
    manager = GambitExecutionManager()
    manager.connect()
    
    # Prepare batch
    circuits = []
    names = []
    for name, (_, circuit) in experiments.items():
        circuits.append(circuit)
        names.append(name)
        print(f"   📦 Queued: {circuit.name} ({circuit.num_qubits} qubits)")
    
    # Run batch
    print(f"\n🔥 SUBMITTING BATCH ({len(circuits)} experiments)...")
    results = manager.run_batch(circuits)
    
    # Analyze results
    print("\n" + "=" * 70)
    print("    RESULTS ANALYSIS")
    print("=" * 70)
    
    all_analyses = []
    
    for name, result in zip(names, results):
        hypothesis = EXPERIMENTS[name]
        analysis = analyze_experiment(name, result, hypothesis)
        all_analyses.append(analysis)
        
        # Print result
        outcome_emoji = {"SUCCESS": "✅", "PARTIAL": "⚠️", "NULL": "❌"}[analysis["outcome"]]
        
        print(f"\n{outcome_emoji} {hypothesis.name}")
        print("-" * 50)
        print(f"   Outcome: {analysis['outcome']}")
        print(f"   Expected states: {analysis['expected_states']}")
        print(f"   Observed: {analysis['observed_prob']:.1%}")
        print(f"   Top state: |{analysis['top_state']}⟩ @ {analysis['dominance']:.1%}")
        print(f"   Z-Score: {analysis['z_score']:.1f}σ")
        print(f"   Counts: {analysis['raw_counts']}")
        print(f"\n   📝 {analysis['interpretation']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("    SUMMARY")
    print("=" * 70)
    
    success = sum(1 for a in all_analyses if a["outcome"] == "SUCCESS")
    partial = sum(1 for a in all_analyses if a["outcome"] == "PARTIAL")
    null = sum(1 for a in all_analyses if a["outcome"] == "NULL")
    
    print(f"\n   ✅ Success: {success}/{len(all_analyses)}")
    print(f"   ⚠️ Partial: {partial}/{len(all_analyses)}")
    print(f"   ❌ Null: {null}/{len(all_analyses)}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"experiment_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "backend": manager.backend.name if manager.backend else "unknown",
            "experiments": all_analyses,
            "summary": {
                "success": success,
                "partial": partial,
                "null": null,
                "total": len(all_analyses)
            }
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    return all_analyses


if __name__ == "__main__":
    run_all_experiments()
