"""
Unit Tests for Gambit Compiler Stack
=====================================

Tests the G-ISA, compiler, and S-Lang parser without requiring IBM hardware.
"""

import sys
import os
import unittest

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.isa import (
    OpCode, 
    Instruction, 
    SolitonRegister, 
    SolitonHeap,
    TopologyConstants,
    to_gray,
    from_gray,
    gray_code_transition,
    decode_physical_to_logical,
    calculate_dominance,
)
from src.compiler import (
    GambitCompiler,
    CircuitCompiler,
    SLangLexer,
    SLangParser,
    GISAAssembler,
)
from src.slang import (
    SLangProgram,
    parse_slang,
    quick_bell_state,
)


class TestOpCodes(unittest.TestCase):
    """Test G-ISA OpCode enum."""
    
    def test_all_opcodes_defined(self):
        """Verify all required opcodes exist."""
        required = ['S_ALLOC', 'S_WRITE', 'S_ROLL', 'S_CNOT', 'S_MEASURE']
        for op in required:
            self.assertTrue(hasattr(OpCode, op), f"Missing OpCode: {op}")
    
    def test_opcode_values_unique(self):
        """Each opcode has a unique value."""
        values = [op.value for op in OpCode]
        self.assertEqual(len(values), len(set(values)))


class TestInstruction(unittest.TestCase):
    """Test Instruction class."""
    
    def test_alloc_instruction(self):
        instr = Instruction.alloc("test")
        self.assertEqual(instr.opcode, OpCode.S_ALLOC)
        self.assertEqual(instr.target, "test")
    
    def test_write_instruction(self):
        instr = Instruction.write("q", 0)
        self.assertEqual(instr.opcode, OpCode.S_WRITE)
        self.assertEqual(instr.operands, [0])
    
    def test_write_invalid_value(self):
        with self.assertRaises(ValueError):
            Instruction.write("q", 2)  # Only 0 or 1 allowed
    
    def test_roll_instruction(self):
        instr = Instruction.roll("q")
        self.assertEqual(instr.opcode, OpCode.S_ROLL)
    
    def test_cnot_instruction(self):
        instr = Instruction.cnot("ctrl", "tgt")
        self.assertEqual(instr.opcode, OpCode.S_CNOT)
        self.assertEqual(instr.target, "tgt")
        self.assertEqual(instr.operands, ["ctrl"])


class TestSolitonRegister(unittest.TestCase):
    """Test SolitonRegister class."""
    
    def test_default_state(self):
        reg = SolitonRegister("test")
        self.assertEqual(reg.theta, 0.0)
        self.assertEqual(reg.logical_state, 0)
    
    def test_write_0(self):
        reg = SolitonRegister("test")
        reg.write(0)
        self.assertEqual(reg.theta, TopologyConstants.THETA_ROBUST)
    
    def test_write_1(self):
        reg = SolitonRegister("test")
        reg.write(1)
        self.assertEqual(reg.theta, TopologyConstants.THETA_FISHER)
    
    def test_roll(self):
        reg = SolitonRegister("test")
        reg.write(0)
        reg.roll()
        self.assertEqual(reg.theta, TopologyConstants.THETA_FISHER)
        reg.roll()
        self.assertEqual(reg.theta, TopologyConstants.THETA_ROBUST)


class TestSolitonHeap(unittest.TestCase):
    """Test SolitonHeap memory manager."""
    
    def test_allocation(self):
        heap = SolitonHeap()
        reg = heap.alloc("q1")
        
        self.assertEqual(reg.name, "q1")
        self.assertEqual(heap.num_solitons, 1)
        self.assertEqual(heap.num_physical_qubits, 2)
    
    def test_multiple_allocations(self):
        heap = SolitonHeap()
        heap.alloc("a")
        heap.alloc("b")
        
        self.assertEqual(heap.num_solitons, 2)
        self.assertEqual(heap.num_physical_qubits, 4)
    
    def test_duplicate_allocation_fails(self):
        heap = SolitonHeap()
        heap.alloc("q")
        with self.assertRaises(ValueError):
            heap.alloc("q")  # Duplicate name
    
    def test_get_soliton(self):
        heap = SolitonHeap()
        heap.alloc("test")
        reg = heap.get("test")
        self.assertEqual(reg.name, "test")
    
    def test_topology_validation(self):
        heap = SolitonHeap()
        warnings = heap.validate_topology(complexity=3)  # Too low
        self.assertTrue(len(warnings) > 0)
        self.assertTrue("Geometry" in warnings[0])


class TestGrayCode(unittest.TestCase):
    """Test Gray Code utilities."""
    
    def test_to_gray(self):
        self.assertEqual(to_gray(0), 0b00)
        self.assertEqual(to_gray(1), 0b01)
        self.assertEqual(to_gray(2), 0b11)
        self.assertEqual(to_gray(3), 0b10)
    
    def test_from_gray(self):
        self.assertEqual(from_gray(0b00), 0)
        self.assertEqual(from_gray(0b01), 1)
        self.assertEqual(from_gray(0b11), 2)
        self.assertEqual(from_gray(0b10), 3)
    
    def test_gray_transition(self):
        path = gray_code_transition(0, 3)
        # Should have single-bit changes
        self.assertEqual(path, [0, 1, 3])


class TestDecoding(unittest.TestCase):
    """Test result decoding."""
    
    def test_physical_to_logical(self):
        self.assertEqual(decode_physical_to_logical('00'), 0)
        self.assertEqual(decode_physical_to_logical('01'), 0)
        self.assertEqual(decode_physical_to_logical('10'), 1)
        self.assertEqual(decode_physical_to_logical('11'), 1)
    
    def test_dominance_calculation(self):
        counts = {'00': 900, '10': 50, '01': 30, '11': 20}
        dom, top, decoh = calculate_dominance(counts)
        
        self.assertEqual(top, '00')
        self.assertAlmostEqual(dom, 0.9, places=2)
        self.assertFalse(decoh)  # 90% > 85% threshold


class TestCompiler(unittest.TestCase):
    """Test GambitCompiler."""
    
    def test_compile_simple_program(self):
        source = """
        program Test:
            soliton q = 0;
            q.roll();
            measure(q);
        """
        compiler = GambitCompiler()
        name, circuit = compiler.compile_source(source)
        
        self.assertEqual(name, "Test")
        self.assertEqual(circuit.num_qubits, 2)  # 1 soliton = 2 physical
    
    def test_compile_bell_state(self):
        source = """
        program Bell:
            soliton a = H;
            soliton b = 0;
            entangle(a, b);
            measure(a);
            measure(b);
        """
        compiler = GambitCompiler()
        name, circuit = compiler.compile_source(source)
        
        self.assertEqual(name, "Bell")
        self.assertEqual(circuit.num_qubits, 4)  # 2 solitons = 4 physical


class TestSLangProgram(unittest.TestCase):
    """Test fluent SLangProgram API."""
    
    def test_program_building(self):
        prog = SLangProgram("Demo")
        q = prog.soliton("q", 0)
        q.roll()
        prog.measure(q)
        
        instrs = prog.get_instructions()
        self.assertEqual(len(instrs), 4)  # alloc, write, roll, measure
    
    def test_bell_state_helper(self):
        circuit = quick_bell_state()
        self.assertEqual(circuit.num_qubits, 4)


class TestGISAAssembler(unittest.TestCase):
    """Test G-ISA assembly format."""
    
    def test_assemble_basic(self):
        source = """
        S_ALLOC q
        S_WRITE q 0
        S_ROLL q
        S_MEASURE q
        """
        assembler = GISAAssembler()
        instrs = assembler.assemble(source)
        
        self.assertEqual(len(instrs), 4)
        self.assertEqual(instrs[0].opcode, OpCode.S_ALLOC)
        self.assertEqual(instrs[2].opcode, OpCode.S_ROLL)


class TestLexer(unittest.TestCase):
    """Test S-Lang lexer."""
    
    def test_tokenize_program(self):
        source = "program Test:"
        lexer = SLangLexer(source)
        tokens = lexer.tokenize()
        
        from src.compiler import TokenType
        self.assertEqual(tokens[0].type, TokenType.PROGRAM)
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
