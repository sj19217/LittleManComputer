"""
This program will run an implementation of the LMC. At present the LMC code will simply be stored as an explicit string.

The process will take 2 parts:
 1. Compilation/assembly; this will take a string of LMC assembly code and place the machine code instructions
     into memory as necessary.
 2. Execution; the machine code will run, mimicking the process/registers of a CPU.
"""

from collections import namedtuple
import math

ASSEMBLY_CODE = """
	INP
	STA	a
	INP
	STA	b
loop	LDA	res
	ADD	b
	STA	res
	LDA	a
	SUB	dec
	STA	a
	BRP	loop
	LDA	res
	OUT
	HLT

a	DAT
b	DAT
res	DAT
dec	DAT 1
"""

OPCODES = {
    "ADD": 1,
    "SUB": 2,
    "STA": 3,
    "LDA": 4,
    "BRA": 5,
    "BRZ": 6,
    "BRP": 7,
    "INP": 8,
    "OUT": 9,
    "HLT": 0,
    "DAT": None
}

RAM_SIZE = 100
RAM_SIZE_DECLENGTH = math.ceil(math.log(RAM_SIZE, 10))

PRINT_DEBUG = True

# Used in the process of compiling
LabelledCommandTuple = namedtuple("LabelledCommandTuple", ["label", "opcode", "operand"])
CommandTuple = namedtuple("CommandTuple", ["opcode", "operand"])

# For a synatx error in the code
class CompileError(Exception):
    pass

def compile_assembly(asm):
    """
    Compiles the assembly code into the RAM.
    The RAM works using a list.

    1. Split into individual lines
    2. For each line, remove all comments (then remove all empty lines)
    3. Split each into (up to) 3 parts by whitespace. Organise into tuples like:
        (label, opcode, operand)
    4. Everywhere an operand uses a label, replace the label with a numeric value (the memory address of the line with
        that label)
    5. Assemble the commands in their numeric form into the memory.
    @param asm:
    @return:
    """

    memory = [0] * RAM_SIZE

    # STEP 1 - Split code into individual lines
    asm_lines = asm.split("\n")


    # STEP 2a - Remove comments
    for i, line in enumerate(asm_lines):
        code, *comments = line.split("#")   # Part before any hash symbols stays
        asm_lines[i] = code.strip()

    #       b - Remove empty lines
    asm_lines = [line for line in asm_lines if line]


    # STEP 3 - Split into command tuples
    labelled_command_tuples = []
    for linenum, line in enumerate(asm_lines, start=1):
        parts = line.split()

        # If it has 3 parts, they are (label, opcode, operand)
        # If it has 2 parts, they are (label, opcode) or (opcode, operand), depending on which is a valid opcode
        #  (if neither is valid, a CompileError is raised)
        # If it has 1 part, it is an opcode
        # If it has more, raise a CompileError

        if len(parts) == 1:
            # Confirm it is a valid opcode
            if parts[0] not in OPCODES.keys():
                raise CompileError("No valid opcode found on line {} ({})".format(linenum, parts))
            labelled_command_tuples.append(LabelledCommandTuple("", parts[0], 0))

        elif len(parts) == 2:
            first, second = parts

            if first in OPCODES.keys():
                # If it is a valid int, turn it into that
                # This is because string values in the operand section will be treated as labels
                try:
                    second = int(second)
                except ValueError:
                    pass
                labelled_command_tuples.append(LabelledCommandTuple("", first, second))
            elif second in OPCODES.keys():
                labelled_command_tuples.append(LabelledCommandTuple(first, second, 0))
            else:
                raise CompileError("No valid opcode found on line {}".format(linenum))

        elif len(parts) == 3:
            # Confirm the second is a valid opcode
            if parts[1] not in OPCODES.keys():
                raise CompileError("No valid opcode found on line {}".format(linenum))

            # If the operand is a valid int, turn it into that
            try:
                parts[2] = int(parts[2])
            except ValueError:
                pass

            labelled_command_tuples.append(LabelledCommandTuple(parts[0], parts[1], parts[2]))

        elif len(parts) > 3:
            raise CompileError("Too many parts in line {}".format(linenum))


    # STEP 4 - Replace labels with numeric IDs
    # Firstly, make a label index
    labels_index = {}
    for i, command in enumerate(labelled_command_tuples):
        if command.label:
            # Is there already one there?
            if command.label in labels_index.keys():
                raise CompileError("Already a line with label {}".format(command.label))

            # There isn't, so add it now
            labels_index[command.label] = i

    # Finally, Perform replacements
    command_tuples = []
    for command in labelled_command_tuples:
        if isinstance(command.operand, str):
            if command.operand in labels_index.keys():
                label_numeric = labels_index[command.operand]
            else:
                raise CompileError("Unknown label: {}".format(command.operand))

            new_command = CommandTuple(command.opcode, label_numeric)
            command_tuples.append(new_command)
        else:
            command_tuples.append(CommandTuple(command.opcode, command.operand))

    # STEP 5 - Assemble numerically
    opcode_mult = 10 ** RAM_SIZE_DECLENGTH

    for i, command in enumerate(command_tuples):
        if command.opcode == "DAT":
            # DAT just places the command in the box
            memory[i] = command.operand
            continue

        numeric_opcode = OPCODES[command.opcode]

        memory[i] = (numeric_opcode * opcode_mult) + command.operand

    return memory

def write_memory(address, content, registers, memory):
    registers["mar"] = address
    registers["mdr"] = content
    memory[registers["mar"]] = registers["mdr"]
    if PRINT_DEBUG: print("Wrote {data} to address {addr}".format(data=content, addr=address))

def read_memory(address, registers, memory):
    registers["mar"] = address
    registers["mdr"] = memory[registers["mdr"]]
    if PRINT_DEBUG: print("Read {data} from address {addr} into MDR".format(data=registers["mdr"], addr=address))

def exec_ADD(operand, registers, memory):
    registers["mar"] = operand                  # 1. Store operand in MAR
    registers["mdr"] = memory[registers["mar"]] # 2. Get data from memory and store in in MDR
    registers["acc"] += registers["mdr"]        # 3. Add the MDR to the accumulator

def exec_SUB(operand, registers, memory):
    registers["mar"] = operand
    registers["mdr"] = memory[registers["mar"]]
    registers["acc"] -= registers["mdr"]

def exec_STA(operand, registers, memory):
    registers["mar"] = operand                  # Store operand in MAR
    registers["mdr"] = registers["acc"]         # Store accumulator value in MDR
    memory[registers["mar"]] = registers["mdr"] # Write MDR to memory

def exec_LDA(operand, registers, memory):
    registers["mar"] = operand                  # Store operand in MAR
    registers["mdr"] = memory[registers["mar"]] # Load memory data into MDR
    registers["acc"] = registers["mdr"]         # Store MDR in accumulator

def exec_BRA(operand, registers, memory):
    registers["pc"] = operand                   # Save operand to PC (branch)

def exec_BRZ(operand, registers, memory):
    if registers["acc"] == 0:
        registers["pc"] = operand

def exec_BRP(operand, registers, memory):
    if registers["acc"] > 0:
        registers["pc"] = operand

def exec_INP(operand, registers, memory):
    registers["acc"] = int(input("< "))

def exec_OUT(operand, registers, memory):
    print(">", registers["acc"])

EXEC_DICT = {
    1: exec_ADD,
    2: exec_SUB,
    3: exec_STA,
    4: exec_LDA,
    5: exec_BRA,
    6: exec_BRZ,
    7: exec_BRP,
    8: exec_INP,
    9: exec_OUT
}


def execute(memory, pc=0):
    """
    Executes the data in the memory given.
    @param memory:
    @param pc: Program counter
    @return:
    """

    # Registers
    registers = {
        "acc": 0,   # Accumulator
        "cir": 0,   # Current instruction register
        "mdr": 0,   # Memory data register
        "mar": 0,   # Memory address register
        "pc": pc    # Program counter
    }

    while True:
        # Fetch, decode, execute
        # 1. Fetch

        # Move current program counter to MAR
        registers["mar"] = registers["pc"]

        # Increment PC
        registers["pc"] += 1

        # Get memory from address in MAR and store in MDR
        registers["mdr"] = memory[registers["mar"]]

        # Store the instruction in the CIR
        registers["cir"] = registers["mdr"]

        # 2. Decode
        # Find basic opcode number
        opcode = int(math.floor(registers["cir"] / (10**RAM_SIZE_DECLENGTH)))
        operand = registers["cir"] - (opcode * 10**RAM_SIZE_DECLENGTH)

        # 3. Execute
        # Pass of to a dict of functions
        if opcode == 0:
            # HLT operation
            return
        EXEC_DICT[opcode](operand, registers, memory)





def print_tabular(data, columns):
    """
    Prints the list given to it as tabular data. Mostly for printing the memory contents.
    @param data:
    @param columns:
    @return:
    """

    string_list = [str(x) for x in data]
    max_size = len(max(string_list, key=lambda x: len(x)))

    for i, item in enumerate(string_list, 1):
        print(format(item, ">" + str(max_size)) + " ", end="")
        if i % columns == 0:
            print()


def main(asm):
    """
    Compile then execute
    @return:
    """

    # Compile the program
    memory = compile_assembly(asm)
    print("Initial memory state:")
    print_tabular(memory, 10)

    # Run the program
    execute(memory)

    print("Final memory state:")
    print_tabular(memory, 10)


if __name__ == "__main__":
    main(ASSEMBLY_CODE)
