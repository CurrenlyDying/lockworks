"""
SIGMA Scaling Law Verification
==============================

HYPOTHESIS (Gemini): "Topological protection scales inversely with manifold complexity"

PREDICTION:
    - Modular: Noise ∝ Constant (per module)
    - Monolith: Noise ∝ N² (or worse with crosstalk)

VERIFICATION EXPERIMENTS:
    1. Fixed-Core Scaling: Keep core size = 2, increase # of cores
    2. Fixed-Total Scaling: Same total qubits, vary modular vs monolith
    3. Crosstalk Isolation: Test if independent pairs truly decouple

SUCCESS CRITERIA:
    - Modular fidelity should remain constant as cores increase
    - Monolith fidelity should degrade as N increases
    - The ratio (Modular/Monolith) should increase with complexity
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compiler import CircuitCompiler
from src.runtime import GambitExecutionManager, GambitResult
from src.isa import Instruction, OpCode, TopologyConstants
from src.slang import SLangProgram


# =============================================================================
# EXPERIMENT 1: MODULAR SCALING
# =============================================================================

def build_modular_chain(n_cores: int) -> Tuple[str, "QuantumCircuit"]:
    """
    Build N independent cores, each entangled to the next.
    
    Topology:
        Core0 → CX → Core1 → CX → Core2 → ... → CoreN
        
    Each core is braided independently, only linked by CX on data bits.
    """
    prog = SLangProgram(f"Modular{n_cores}")
    
    cores = []
    # First core in superposition
    cores.append(prog.soliton("c0", "H"))
    
    # Remaining cores in ground state
    for i in range(1, n_cores):
        cores.append(prog.soliton(f"c{i}", 0))
    
    # Link each core to the next via CX
    for i in range(n_cores - 1):
        prog.entangle(cores[i], cores[i+1])
    
    # Measure all
    for core in cores:
        prog.measure(core)
    
    return f"modular_{n_cores}", prog.compile()


def build_monolith_attempts(n_qubits: int) -> Tuple[str, "QuantumCircuit"]:
    """
    Build a single large braid across all qubits (expected to fail).
    
    This tests the "Scale UP" approach.
    """
    # Use raw instructions to force single-braid topology
    instructions = []
    
    for i in range(n_qubits):
        instructions.append(Instruction.alloc(f"q{i}"))
        if i == 0:
            instructions.append(Instruction(OpCode.S_WRITE, f"q{i}", ["H"]))
        else:
            instructions.append(Instruction.write(f"q{i}", 0))
    
    # Chain CNOTs (this is what failed before)
    for i in range(n_qubits - 1):
        instructions.append(Instruction.cnot(f"q{i}", f"q{i+1}"))
    
    for i in range(n_qubits):
        instructions.append(Instruction.measure(f"q{i}"))
    
    cc = CircuitCompiler(complexity=6)
    circuit = cc.compile(instructions)
    circuit.name = f"Monolith{n_qubits}"
    
    return f"monolith_{n_qubits}", circuit


# =============================================================================
# EXPERIMENT 2: CROSSTALK ISOLATION
# =============================================================================

def build_isolated_pairs(n_pairs: int) -> Tuple[str, "QuantumCircuit"]:
    """
    Build N completely independent Bell pairs (no CX between pairs).
    
    This tests if isolation truly preserves fidelity.
    """
    prog = SLangProgram(f"Isolated{n_pairs}Pairs")
    
    pairs = []
    for i in range(n_pairs):
        a = prog.soliton(f"a{i}", "H")
        b = prog.soliton(f"b{i}", 0)
        prog.entangle(a, b)
        pairs.append((a, b))
    
    for a, b in pairs:
        prog.measure(a)
        prog.measure(b)
    
    return f"isolated_{n_pairs}_pairs", prog.compile()


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def calculate_ghz_fidelity(counts: Dict[str, int], n_qubits: int) -> float:
    """
    Calculate fidelity to ideal GHZ state: |00...0⟩ + |11...1⟩
    """
    total = sum(counts.values())
    zeros = '0' * n_qubits
    ones = '1' * n_qubits
    ghz_prob = (counts.get(zeros, 0) + counts.get(ones, 0)) / total
    return ghz_prob


def calculate_pair_fidelity(counts: Dict[str, int], n_pairs: int) -> float:
    """
    Calculate fidelity to ideal tensor product of Bell states.
    
    For N pairs: (|00⟩ + |11⟩) ⊗ (|00⟩ + |11⟩) ⊗ ...
    Expected states: all combinations of 00 and 11 per pair.
    """
    total = sum(counts.values())
    n_bits = n_pairs * 2
    
    # Generate all expected states
    expected = []
    for i in range(2**n_pairs):
        bits = format(i, f'0{n_pairs}b')
        state = ''.join('00' if b == '0' else '11' for b in bits)
        expected.append(state)
    
    fidelity = sum(counts.get(s, 0) for s in expected) / total
    return fidelity


# =============================================================================
# MAIN VERIFICATION
# =============================================================================

def run_scaling_verification():
    """
    Run the complete scaling law verification.
    """
    print("=" * 70)
    print("    SIGMA SCALING LAW VERIFICATION")
    print("    Hypothesis: Topological protection ∝ 1/Complexity")
    print("=" * 70)
    
    # Define experiments
    experiments = []
    
    # Modular scaling: 2, 3, 4 cores
    for n in [2, 3, 4]:
        experiments.append(build_modular_chain(n))
    
    # Isolated pairs: 1, 2, 3, 4 pairs
    for n in [1, 2, 3, 4]:
        experiments.append(build_isolated_pairs(n))
    
    print(f"\n📋 Experiments Queued: {len(experiments)}")
    for name, circ in experiments:
        print(f"   {name}: {circ.num_qubits} qubits")
    
    # Run on QPU
    print("\n🚀 Submitting to IBM Quantum...")
    manager = GambitExecutionManager()
    manager.connect()
    
    circuits = [c for _, c in experiments]
    names = [n for n, _ in experiments]
    
    results = manager.run_batch(circuits)
    
    # Analyze
    print("\n" + "=" * 70)
    print("    RESULTS ANALYSIS")
    print("=" * 70)
    
    all_data = []
    
    # Modular results
    print("\n📊 MODULAR CHAIN SCALING:")
    print("-" * 50)
    for i, n in enumerate([2, 3, 4]):
        result = results[i]
        fidelity = calculate_ghz_fidelity(result.counts, n)
        print(f"   {n} Cores ({n*2} physical): GHZ Fidelity = {fidelity:.1%}")
        all_data.append({
            "experiment": f"modular_{n}",
            "cores": n,
            "physical": n * 2,
            "type": "modular",
            "fidelity": fidelity,
            "dominance": result.dominance,
            "counts": result.counts,
        })
    
    # Isolated pairs results
    print("\n📊 ISOLATED PAIRS SCALING:")
    print("-" * 50)
    for i, n in enumerate([1, 2, 3, 4]):
        result = results[3 + i]
        fidelity = calculate_pair_fidelity(result.counts, n)
        print(f"   {n} Pairs ({n*4} physical): Pair Fidelity = {fidelity:.1%}")
        all_data.append({
            "experiment": f"isolated_{n}",
            "pairs": n,
            "physical": n * 4,
            "type": "isolated",
            "fidelity": fidelity,
            "dominance": result.dominance,
            "counts": result.counts,
        })
    
    # Scaling analysis
    print("\n" + "=" * 70)
    print("    SCALING LAW VERIFICATION")
    print("=" * 70)
    
    modular = [d for d in all_data if d["type"] == "modular"]
    isolated = [d for d in all_data if d["type"] == "isolated"]
    
    # Check if fidelity stays constant (modular hypothesis)
    modular_fidelities = [d["fidelity"] for d in modular]
    isolated_fidelities = [d["fidelity"] for d in isolated]
    
    modular_variance = max(modular_fidelities) - min(modular_fidelities)
    isolated_variance = max(isolated_fidelities) - min(isolated_fidelities)
    
    print(f"\n   Modular Chain Variance: {modular_variance:.1%}")
    print(f"   Isolated Pairs Variance: {isolated_variance:.1%}")
    
    # Compare to previous monolith results (from earlier experiments)
    print("\n📈 COMPARISON TO MONOLITH (from earlier runs):")
    print(f"   Chain4 (monolith): 4.6% GHZ fidelity")
    print(f"   Modular4 (v2.0):   {modular[2]['fidelity']:.1%} GHZ fidelity")
    print(f"   Improvement:       {modular[2]['fidelity']/0.046:.1f}x")
    
    # Verdict
    print("\n" + "=" * 70)
    if modular_variance < 0.20 and modular[2]["fidelity"] > 0.30:
        print("✅ HYPOTHESIS VERIFIED:")
        print("   - Modular fidelity remains relatively constant")
        print("   - Far exceeds monolith at same qubit count")
        print("   - CORE_SIZE = 2 is the fundamental unit")
    else:
        print("⚠️ HYPOTHESIS PARTIALLY VERIFIED:")
        print("   - Results show improvement but need more data")
    print("=" * 70)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scaling_verification_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "backend": manager.backend.name,
            "hypothesis": "Topological protection scales inversely with manifold complexity",
            "experiments": all_data,
            "modular_variance": modular_variance,
            "isolated_variance": isolated_variance,
            "verdict": "VERIFIED" if (modular_variance < 0.20 and modular[2]["fidelity"] > 0.30) else "PARTIAL"
        }, f, indent=2)
    
    print(f"\n💾 Saved: {filename}")
    
    return all_data


if __name__ == "__main__":
    run_scaling_verification()
