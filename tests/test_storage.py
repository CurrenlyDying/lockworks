"""
CTM Test Cartridge
==================

Test suite for the Cylindrical Topological Memory system.

Tests:
    1. Basic read/write
    2. Multi-disk operations
    3. Link (gearing) behavior
    4. Sequencer validation
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cylinder import Cylinder, UnitCell, create_memory, GeometryError, AddressError
from src.sequencer import Sequencer, quick_sequence


class TestUnitCell(unittest.TestCase):
    """Test the UnitCell (Disk) class."""
    
    def test_initial_state(self):
        """Disk starts at position 0."""
        disk = UnitCell(address=0)
        self.assertEqual(disk.position, 0)
        self.assertEqual(disk.theta, 0.0)
    
    def test_rotate_to_1(self):
        """Rotate disk to position 1."""
        disk = UnitCell(address=0)
        disk.rotate_to(1)
        self.assertEqual(disk.position, 1)
        self.assertAlmostEqual(disk.theta, 0.196, places=3)
    
    def test_flip(self):
        """Flip toggles between 0 and 1."""
        disk = UnitCell(address=0)
        disk.flip()
        self.assertEqual(disk.position, 1)
        disk.flip()
        self.assertEqual(disk.position, 0)
    
    def test_physical_qubits(self):
        """Check qubit index mapping."""
        disk = UnitCell(address=2, phys_indices=(4, 5))
        self.assertEqual(disk.phase_qubit, 4)
        self.assertEqual(disk.data_qubit, 5)


class TestCylinder(unittest.TestCase):
    """Test the Cylinder (Memory Bank) class."""
    
    def test_create_memory(self):
        """Create a memory bank."""
        mem = create_memory(4)
        self.assertEqual(mem.n_disks, 4)
        self.assertEqual(mem.n_physical_qubits, 8)
    
    def test_alloc_resets(self):
        """ALLOC resets all disks to 0."""
        mem = Cylinder(4)
        mem.rotate(0, 1)
        mem.rotate(1, 1)
        mem.alloc()
        for disk in mem.disks:
            self.assertEqual(disk.position, 0)
    
    def test_rotate(self):
        """ROTATE sets disk position."""
        mem = create_memory(4)
        mem.rotate(2, 1)
        self.assertEqual(mem.disks[2].position, 1)
        self.assertEqual(mem.disks[0].position, 0)  # Others unchanged
    
    def test_push_alias(self):
        """PUSH is alias for ROTATE."""
        mem = create_memory(4)
        mem.push(1, 1)
        self.assertEqual(mem.disks[1].position, 1)
    
    def test_read_needle(self):
        """READ_NEEDLE returns disk position."""
        mem = create_memory(4)
        mem.rotate(0, 1)
        self.assertEqual(mem.read_needle(0), 1)
        self.assertEqual(mem.read_needle(1), 0)
    
    def test_address_bounds(self):
        """Invalid address raises error."""
        mem = create_memory(4)
        with self.assertRaises(AddressError):
            mem.rotate(10, 1)  # Out of bounds
    
    def test_link(self):
        """LINK records operation for CX generation."""
        mem = create_memory(4)
        mem.link(0, 1)
        ops = [op for op in mem._op_log if op["op"] == "LINK"]
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0]["control"], 0)
        self.assertEqual(ops[0]["target"], 1)
    
    def test_circuit_generation(self):
        """Generate circuit from cylinder state."""
        mem = create_memory(2)
        mem.rotate(0, 1)
        mem.link(0, 1)
        circuit = mem.to_circuit()
        
        self.assertEqual(circuit.num_qubits, 4)
        self.assertEqual(circuit.num_clbits, 2)


class TestSequencer(unittest.TestCase):
    """Test the Sequencer (Phase Lock Loop)."""
    
    def test_basic_sequence(self):
        """Build a basic sequence."""
        seq = Sequencer()
        seq.rotate(0, 1)
        seq.barrier()
        seq.link(0, 1)
        seq.read(0)
        
        self.assertEqual(len(seq.operations), 4)
    
    def test_validation_passes(self):
        """Valid sequence passes validation."""
        seq = Sequencer()
        seq.rotate(0, 1)
        seq.barrier()
        seq.link(0, 1)
        
        self.assertTrue(seq.validate())
    
    def test_quick_sequence(self):
        """Quick sequence builder."""
        seq = quick_sequence(
            writes={0: 1, 1: 0},
            links=[(0, 1)]
        )
        
        ops = seq.dump()
        op_types = [op["op"] for op in ops]
        
        self.assertIn("ROTATE", op_types)
        self.assertIn("LINK", op_types)
        self.assertIn("READ", op_types)
    
    def test_compile_to_cylinder(self):
        """Compile sequence to cylinder."""
        seq = Sequencer()
        seq.alloc(4)
        seq.rotate(0, 1)
        seq.rotate(1, 1)
        seq.barrier()
        seq.validate()
        
        mem = Cylinder(4)
        seq.compile(mem)
        
        self.assertEqual(mem.disks[0].position, 1)
        self.assertEqual(mem.disks[1].position, 1)


class TestIntegration(unittest.TestCase):
    """Integration tests for CTM system."""
    
    def test_write_link_read_scenario(self):
        """
        The spec scenario:
            1. Write 0 to Disk A
            2. Write 1 to Disk B
            3. Link A and B
            4. Read B (should be 1)
        """
        mem = create_memory(2)
        
        # Write operations
        mem.rotate(0, 0)  # Disk A = 0
        mem.rotate(1, 1)  # Disk B = 1
        
        # Link
        mem.link(0, 1)
        
        # Check states
        self.assertEqual(mem.read_needle(0), 0)
        self.assertEqual(mem.read_needle(1), 1)
        
        # Circuit should have CX gate
        circuit = mem.to_circuit()
        self.assertGreater(circuit.depth(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
