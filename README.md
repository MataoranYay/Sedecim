# Sedecim

> *Sedecim* is a **16-bit microcoded CPU** designed and built
> from the gate level up in **Logisim-Evolution**, together with a small Python
> toolchain that defines its instruction set and compiles programs to machine code.

The CPU follows an **x86-inspired** design: a 16-bit data path, a register file with
`AX/BX/CX/DX`, a four-segment memory model (`CS/DS/SS/ES`) and a stack pointer
(`SP/BP`), driven by a microcode ROM. Every instruction is implemented as a
sequence of 32-bit **microinstructions** that orchestrate the bus, the ALU, the
register file and the memory — making the whole design transparent, educational and
easy to extend.

---

## Features

- **16-bit data path** with a shared internal bus and a 16-bit main memory
  (64 Ki × 16-bit address space).
- **Microcoded control unit**: instructions are decoded through a
  2<sup>20</sup> × 32-bit microcode ROM, so the ISA is defined entirely in software
  (`ISA.py`) rather than hard-wired.
- **x86-inspired architecture**: 12 architectural registers (`AX`, `BX`, `CX`, `DX`,
  `CS`, `DS`, `SS`, `ES`, `SP`, `BP`, `DI`, `SI`) and a segmented memory model.
- **33 instructions** across data transfer, arithmetic, logic, shifts, stack,
  subroutine and conditional control flow.
- **6 addressing modes**: immediate, register, direct, indirect, register+offset and
  base+index.
- **16-operation ALU** with a 4-bit program-status word (`Z`/`S`/`C`/`O` flags).
- **Pure-gate implementation**: no built-in CPU — everything (registers, ALU,
  multiplexers, decoders, flip-flops) is assembled from primitive gates and
  Logisim memory components.
- **Python toolchain** (standard library only): an ISA/microcode definition and a
  compiler that both *generates the microcode image* and *assembles programs*.

---

## Architecture overview

```
                            +---------------------------+
                            |       Microcode ROM       |
                            |   (2^20 words x 32-bit)   |
                            +-------------+-------------+
                                          |
                            +-------------v-------------+
 [ DipSwitch ] --- input --> |        CONTROL UNIT       | ---> [ LedBar ]
                            +-------------+-------------+
                                          |
         +-------------------+------------+------------+-------------------+
         |                   |            |            |                   |
   +-----v------+     +------v-----+  +---v----+  +----v------+    +-------v-------+
   | Reg. File  | <-> |     ALU    |  |  PSW   |  |  Program  |    |   Main RAM    |
   | (26 words) |     | (16 ops)   |  | (4-bit)|  |  Counter  |    | 64 Ki x 16-bit|
   +------------+     +------------+  +--------+  +-----------+    +---------------+
         |                   |            |            |
         +-------------------+------------+------------+
                        16-bit internal bus
```

- **Control unit** (`CONTROL_UNIT`, `PULSE_CONTROLLER`, `REG_CONTROLLER`,
  `REG_RW_CONTROLLER`, `MEM_ADDR_REG`, `SEG_SELECTOR`) reads the current
  microinstruction from the ROM and drives the datapath.
- **Pulse controller** steps the machine through the micro-cycle counter; the
  circuit is clocked manually via the `CP` button (with `RS` for reset).
- **Memory address register / segment selector** compute the effective address as
  `segment base + offset`, selecting one of the four 16-bit segment registers.
- **Program counter** (`PROGRAM_COUNTER`) supports load, increment and output on
  the bus.
- **ALU** (`WORD_ALU`) provides 16 operations: `ADD`, `SUB`, `INC`, `DEC`, `AND`,
  `OR`, `XOR`, `NAND`, `NOR`, `XNOR`, `NOT`, `SHL`, `SHR`, `SAR`, `PA` and `PB`.

---

## Register file

The register file is a 26-word, 16-bit structure indexed by a *pin address*
(see `PIN` in `ISA.py`). The registers visible to the programmer are:

| Group          | Registers                        | Role                       |
|----------------|----------------------------------|----------------------------|
| General        | `AX`, `BX`, `CX`, `DX`           | Accumulator / general data |
| Segment        | `CS`, `DS`, `SS`, `ES`           | Code / data / stack / extra|
| Pointer        | `SP`, `BP`                       | Stack pointer / base pointer|
| Index          | `SI`, `DI`                       | Source / destination index |

The remaining entries are internal (microarchitectural) registers such as `MAR`,
`MDR`, `IR`, `DST`, `SRC`, `DISP`, `A1`, `A2` and temporaries `T1`–`T5`.

---

## Instruction set

33 mnemonics are defined. `dst`/`src` may be a register, an immediate, or a memory
operand in any of the six addressing modes below.

| Category        | Mnemonics                                                                 |
|-----------------|---------------------------------------------------------------------------|
| Data transfer   | `MOV dst, src`                                                            |
| Arithmetic      | `ADD`, `SUB`, `CMP`, `INC`, `DEC`                                         |
| Logic           | `AND`, `OR`, `XOR`, `NAND`, `NOR`, `XNOR`, `NOT`                          |
| Shift           | `SHL`, `SHR`, `SAR`                                                       |
| ALU pass-through| `PA`, `PB`                                                                |
| Unconditional   | `JMP target`                                                              |
| Conditional     | `JZ`, `JNZ`, `JS`, `JNS`, `JC`, `JNC`, `JO`, `JNO`                        |
| Subroutine      | `CALL target`, `RET`                                                      |
| Stack           | `PUSH src`, `POP dst`                                                     |
| Misc            | `NOP`, `HLT`                                                              |

Conditional jumps are evaluated against the 4-bit **program-status word**:

| Flag | Bit | Meaning                | Taken when |
|------|-----|------------------------|------------|
| `Z`  | 0   | Zero                   | `JZ`       |
| `S`  | 1   | Sign / negative        | `JS`       |
| `C`  | 2   | Carry / borrow         | `JC`       |
| `O`  | 3   | Overflow               | `JO`       |

---

## Addressing modes

| Mode | Syntax            | Meaning                                      |
|------|-------------------|----------------------------------------------|
| IMM  | `10`, `0x10`      | Immediate value                              |
| REG  | `AX`              | Register (value in register)                 |
| DIR  | `[5]`, `[0x10]`   | Direct — absolute address                    |
| IND  | `[BP]`            | Indirect — address held in register          |
| ROF  | `[BP+1]`          | Register + offset                            |
| BIX  | `[BP+SI]`         | Base + index                                 |

Examples:

```asm
MOV  AX 0x10        ; AX = 0x10
ADD  AX BX          ; AX = AX + BX
MOV  [5] AX         ; store AX at address 5
MOV  AX [BP+SI]     ; load AX from (BP + SI)
INC  [0x8000]       ; increment the word at 0x8000
```

---

## Microcode

Control is **microprogrammed**: every machine instruction is expanded into a list of
32-bit microinstructions (`MICROINSTRUCTION` in `ISA.py`), where each control field
is a bit in the word (register read/write addresses, bus enables, segment selection,
PC control, ALU opcode, PSW write, cycle reset and halt).

- **Fetch sequences** `FETCH0`–`FETCH3` read the opcode word and 0–3 operand words.
- Each instruction is **padded to 16 cycles** with the `CYC` (cycle-reset) control.
- The microcode ROM is addressed by the concatenation of:

  ```
  [ 12-bit instruction word ][ 4-bit PSW ][ 4-bit cycle counter ]
  ```

  yielding a 20-bit address (1,048,576 words) × 32-bit data.
- The assembled image is written in Logisim's run-length-encoded
  [“v2.0 raw”](https://github.com/logisim-evolution/logisim-evolution) format as
  `microcode.raw`.

The conditional jumps use a clever trick: when the PSW does **not** satisfy the
branch condition, the microcode slot is filled with a `FETCH1` sequence padded with
`CYC` (the “PSW cavity”), so the CPU simply skips the target operand and falls
through to the next instruction.

---

## Toolchain

All tooling is pure **Python 3** (standard library only — `ISA.py` and `COMPILER.py`
import only `itertools` and each other).

| File             | Purpose                                                                  |
|------------------|--------------------------------------------------------------------------|
| `ISA.py`         | ISA definition: register map, control signals, opcodes, addressing modes, microinstruction sequences |
| `COMPILER.py`    | Microcode compiler (`compile_microcode`) and assembler (`compile_code`)  |
| `microcode.raw`  | Generated microcode image (Logisim “v2.0 raw”)                           |
| `Demo.ipynb`     | Worked examples: compiling microcode and assembling sample programs      |
| `16-bit CPU.circ`| The Logisim-Evolution circuit (the CPU itself)                           |

### Assembling a program

The assembler supports **labels** (`name:`), **comments** (`;`), decimal and hex
(`0x…`) literals, and all six addressing modes. The output is a space-separated
list of hex words ready to load into main memory.

---

## Getting started

### Prerequisites

- [Logisim-Evolution](https://github.com/logisim-evolution/logisim-evolution) ≥ 5.0
- Python 3.10+

### 1. Generate the microcode

```bash
python -c "from COMPILER import compile_microcode; compile_microcode()"
```

This writes `microcode.raw`.

### 2. Load the microcode into the ROM

Open `16-bit CPU.circ` in Logisim-Evolution. In the `MAIN` circuit, right-click the
**microcode ROM** → **Load Image…** → select `microcode.raw`.

### 3. Assemble and load a program
```python
from COMPILER import compile_code

code = """
seg:
    MOV DS 0x4000      ; data segment
    MOV SS 0x8000      ; stack segment
    MOV SP 0x4000      ; stack pointer
    JMP start

start:
    MOV AX [0]         ; a = [0]
    MOV BX [1]         ; b = [1]
    ADD AX BX          ; AX = a + b
    MOV [2] AX         ; [2] = a + b
    JMP end
    
end:
    HLT
"""

print(compile_code(code))
```

Assemble your program with `compile_code(...)`, then load the resulting hex words
into the **main RAM** (right-click the RAM → **Load Image…**, or edit its contents
directly).

### 4. Run

Use the `RS` button to reset, then press `CP` (clock pulse) repeatedly to step the
machine cycle by cycle. Results appear on the `LedBar`; the `DipSwitch` provides
input, and probes throughout the `MAIN` circuit expose the bus, registers and
microinstruction word.

> A full worked example (a subroutine that computes `a + b − 1`) is available in
> [`Demo.ipynb`](Demo.ipynb).

---

## Project layout

```
16-bit CPU/
├── 16-bit CPU.circ     # Logisim-Evolution circuit (CPU)
├── ISA.py              # instruction set & microcode definition
├── COMPILER.py         # microcode compiler + assembler
├── microcode.raw       # generated microcode image
├── Demo.ipynb          # usage examples
└── README.md
```

The circuit is organized as a hierarchy of sub-circuits, including `WORD_ALU`,
`PROGRAM_COUNTER`, `CONTROL_UNIT`, `PULSE_CONTROLLER`, `REG_CONTROLLER`,
`REG_RW_CONTROLLER`, `MEM_ADDR_REG` and `SEG_SELECTOR`, built on gate-level
building blocks (adders, multiplexers, decoders, latches and flip-flops).

---

## License

No license has been chosen yet. If you plan to publish this project, add an
open-source license (e.g. [MIT](https://choosealicense.com/licenses/mit/)) and
reference it here.

---

## Acknowledgements

Built with [Logisim-Evolution](https://github.com/logisim-evolution/logisim-evolution).
