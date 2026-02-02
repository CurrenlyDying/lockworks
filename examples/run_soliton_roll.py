"""
Run Soliton Roll on IBM Hardware
================================

Demonstrates the Soliton Roll (logical NOT gate).

Usage:
    python examples/run_soliton_roll.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compiler import GambitCompiler
from src.runtime import GambitExecutionManager, verify_topology


def main():
    print("=" * 60)
    print("    PROJECT SIGMA: Soliton Roll (NOT Gate)")
    print("=" * 60)
    
    # Load S-Lang
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "soliton_roll.sl")
    
    # Compile
    print("\n📝 COMPILING...")
    compiler = GambitCompiler(complexity=6)
    
    with open(path, 'r') as f:
        source = f.read()
    
    program_name, circuit = compiler.compile_source(source)
    print(f"   Program: {program_name}")
    
    # Execute
    print("\n🚀 EXECUTING...")
    manager = GambitExecutionManager()
    result = manager.run(circuit)
    
    # Display
    print("\n" + "=" * 60)
    print("    RESULTS")
    print("=" * 60)
    print(f"\nRaw Counts: {result.counts}")
    print(f"\nDominance: {result.dominance:.2%}")
    print(f"Top State: |{result.top_state}⟩")
    
    # Verdict
    # After a roll from 0, we expect |10⟩
    expected = '10'
    
    print("\n" + "-" * 60)
    if result.top_state == expected:
        print("✅ SUCCESS: SOLITON ROLL VERIFIED!")
        print(f"   Input: |0⟩_L → Output: |1⟩_L")
        print(f"   Physical: |00⟩ → |10⟩ @ {result.dominance:.2%}")
    else:
        print(f"⚠️ UNEXPECTED: Got |{result.top_state}⟩, expected |{expected}⟩")
    
    return 0 if result.top_state == expected else 1


if __name__ == "__main__":
    sys.exit(main())
