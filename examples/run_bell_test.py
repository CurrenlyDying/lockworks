"""
Run Bell Test on IBM Hardware
=============================

This script compiles and runs the Bell state S-Lang program
on IBM Quantum hardware using the Gambit stack.

Usage:
    python examples/run_bell_test.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compiler import GambitCompiler
from src.runtime import GambitExecutionManager, verify_topology


def main():
    print("=" * 60)
    print("    PROJECT SIGMA: Bell State Verification")
    print("=" * 60)
    
    # Load the S-Lang program
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bell_path = os.path.join(script_dir, "bell_test.sl")
    
    # Compile
    print("\n📝 COMPILING S-LANG SOURCE...")
    compiler = GambitCompiler(complexity=6)
    
    with open(bell_path, 'r') as f:
        source = f.read()
    
    program_name, circuit = compiler.compile_source(source)
    
    print(f"   Program: {program_name}")
    print(f"   Qubits: {circuit.num_qubits} physical")
    print(f"   Circuit depth: {circuit.depth()}")
    
    # Execute
    print("\n🚀 EXECUTING ON IBM QUANTUM...")
    manager = GambitExecutionManager()
    result = manager.run(circuit)
    
    # Display results
    print("\n" + "=" * 60)
    print("    RESULTS")
    print("=" * 60)
    print(f"\nRaw Counts: {result.counts}")
    print(f"\nDominance: {result.dominance:.2%}")
    print(f"Top State: |{result.top_state}⟩")
    print(f"Z-Score: {result.z_score:.2f}σ")
    print(f"Purity: {result.purity:.4f}")
    
    # Verify entanglement
    total = sum(result.counts.values())
    p_00 = result.counts.get('00', 0) / total
    p_11 = result.counts.get('11', 0) / total
    p_error = 1 - (p_00 + p_11)
    
    print(f"\n📊 BELL STATE ANALYSIS:")
    print(f"   |00⟩: {p_00:.2%}")
    print(f"   |11⟩: {p_11:.2%}")
    print(f"   Correlations: {p_00 + p_11:.2%}")
    print(f"   Errors: {p_error:.2%}")
    
    # Verdict
    print("\n" + "-" * 60)
    passed, msg = verify_topology(result)
    
    if p_00 + p_11 > 0.80:
        print("✅ SUCCESS: TOPOLOGICAL ENTANGLEMENT CONFIRMED!")
        print(f"   {msg}")
    else:
        print("⚠️ WARNING: ENTANGLEMENT NOT CONFIRMED")
        print(f"   Correlation {p_00 + p_11:.2%} < 80%")
    
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
