from ISA import PIN, SHIFTS, MICROINSTRUCTION, OP_TYPE, ADDR_MODE, FETCH0, FETCH1, FETCH2, FETCH3, ASMINSTRUCTION
from itertools import groupby

def write_rle_raw(filename, data):
    def lines():
        yield "v2.0 raw\n"
        for val, g in groupby(data):
            n = sum(1 for _ in g)
            yield f"{n}*{val:x}\n" if n > 1 else f"{val:x}\n"

    with open(filename, 'w') as f:
        f.writelines(lines())

def compile_microcode(save_path="microcode.raw"):
    # For each opcode: take its micro-op list and pad it to 16 cycles with CYC
    ASM = {k:v+[MICROINSTRUCTION['CYC']]*(16 - len(v)) for k,v in ASMINSTRUCTION.items()}
    
    # Map conditional-jump opcodes to (PSW bit index, required value)
    CJMPS = {
        OP_TYPE["JZ"]:  (0, 1),
        OP_TYPE["JNZ"]: (0, 0),
        OP_TYPE["JS"]:  (1, 1),
        OP_TYPE["JNS"]: (1, 0),
        OP_TYPE["JC"]:  (2, 1),
        OP_TYPE["JNC"]: (2, 0),
        OP_TYPE["JO"]:  (3, 1),
        OP_TYPE["JNO"]: (3, 0),
    }

    # Fill the PSW cavity of CJMPS instructions with FETCH1 padded to 16 cycles with CYC
    CJMPS_cavity = FETCH1 + [MICROINSTRUCTION['CYC']] * (16 - len(FETCH1))

    # Allocate 1 Mi-entry microcode array, pre-filled with CYC
    micro_seq = [MICROINSTRUCTION['CYC']] * 0x100000

    # Iterate over the entire 12-bit opcode space
    for asm in range(0x1000):
        if asm not in ASM:
            continue
    
        op_type = asm & 0xff8
        cond = CJMPS.get(op_type) 

        # Iterate over the entire 4-bit PSW space
        for psw in range(0x10):
            # Iterate over the entire 4-bit cycle space
            for cyc in range(0x10):
                addr = (asm << 8) | (psw << 4) | cyc
                
                # Fill the PSW cavity of CJMPS instructions if the current opcode is in CJMPS and doesn't meet the corresponding condition, otherwise, normally fill in the instruction
                if cond is not None and ((psw >> cond[0]) & 1) != cond[1]:
                    micro_seq[addr] = CJMPS_cavity[cyc]
                else:
                    micro_seq[addr] = ASM[asm][cyc]

    # Save microcode
    write_rle_raw(save_path, micro_seq)
    print(f"Saved in {save_path}")

def compile_word(w: str):
    # MOV
    if w in OP_TYPE:
        return {"CODE": OP_TYPE[w]}
    # AX
    elif w in PIN:
        return {"CODE": PIN[w], "AM": ADDR_MODE["REG"]}
    # 10 or 0x10
    elif w.isascii() and w.isdigit() or w.startswith("0x"):
        return {"CODE": int(w, 16 if w.startswith("0x") else 10), "AM": ADDR_MODE["IMM"]}
    elif w.startswith("[") and w.endswith("]"):
        w = w[1:-1]
        ws = w.split("+")
        # [AX]
        if w in PIN:
            return {"CODE": PIN[w], "AM": ADDR_MODE["IND"]}
        # [10] or [0x10]
        elif w.isascii() and w.isdigit() or w.startswith("0x"):
            return {"CODE": int(w, 16 if w.startswith("0x") else 10), "AM": ADDR_MODE["DIR"]}
        elif len(ws) == 2:
            # [BP+SI]
            if ws[0] in PIN and ws[1] in PIN:
                return {"CODE": (PIN[ws[0]], PIN[ws[1]]), "AM": ADDR_MODE["BIX"]}
            # [BP+1]
            elif ws[0] in PIN and (ws[1].isascii() and ws[1].isdigit() or ws[1].startswith("0x")):
                return {"CODE": (PIN[ws[0]], int(ws[1], 16 if ws[1].startswith("0x") else 10)), "AM": ADDR_MODE["ROF"]}
            else: raise ValueError(f"Undefined code: {w}")      
        else: raise ValueError(f"Undefined code: {w}")
    else: raise ValueError(f"Undefined code: {w}")

def compile_line(l: str, MARKS: dict = {}):
    ls = l.split(" ")

    # 2-address instruction
    if len(ls) == 3:
        c1, c2, c3 = compile_word(ls[0]), compile_word(ls[1]), compile_word(ls[2])

        if isinstance(c2["CODE"], tuple):
            return [c1["CODE"] | c2["AM"] << 3 | c3["AM"], c2["CODE"][0], c3["CODE"], c2["CODE"][1]]
        elif isinstance(c3["CODE"], tuple):
            return [c1["CODE"] | c2["AM"] << 3 | c3["AM"], c2["CODE"], c3["CODE"][0], c3["CODE"][1]]
        else:
            return [c1["CODE"] | c2["AM"] << 3 | c3["AM"], c2["CODE"], c3["CODE"]]
    
    # 1-address instruction
    elif len(ls) == 2:
        if ls[1] in MARKS:
            c1, c2 = compile_word(ls[0]), compile_word(MARKS[ls[1]])
            return [c1["CODE"] | c2["AM"], c2["CODE"]]
        else: 
            c1, c2 = compile_word(ls[0]), compile_word(ls[1])
            return [c1["CODE"] | c2["AM"], c2["CODE"]]

    # 0-address instruction
    elif len(ls) == 1:
        c1 = compile_word(ls[0])
        return [c1["CODE"]]

def compile_code(c: str):
    # Split strings into an array while ignoring annotations, space characters aside a line and blank lines
    cs = [s for s in (i.split(";")[0].strip() for i in c.splitlines()) if s]

    # Find all marks while calculating the corresponding index
    MARKS = {}
    word_offset = 0
    for l in cs:
        if l.endswith(":"):
            MARKS[l[:-1]] = str(word_offset)
            continue
        word_offset += len([p for i in l.split(" ") for p in i.split("+")])

    # Delete all marks
    cs = [l for l in cs if not l.endswith(":")]

    # Compile all lines
    compiled = [compile_line(l, MARKS) for l in cs]

    # Flatten and convert into hex strings
    return " ".join([hex(j)[2:] for i in compiled for j in i])