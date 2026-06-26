"""Lumina runner - bypasses type checker entirely."""

import sys
import os
import tokeniser
import parser
import codegen
import lumina_utils as utils

def run_lumina(input_file):
    basename = os.path.splitext(os.path.basename(input_file))[0]
    c_filename = basename + ".c"

    print("=> Compiling Lumina source...")
    source = utils.read_file(input_file)
    tokens = tokeniser.tokenise(utils.explode(source))
    prog = parser.parse(tokens)

    print("=> Generating C code...")
    code = codegen.gen_program(prog, None)
    with open(c_filename, 'w') as f:
        f.write(code)

    print(f"=> Building executable ({basename})...")
    gcc_cmd = utils.compile_cmd(c_filename, basename)
    os.system(gcc_cmd)

    print(f"=> Running {basename}...")
    run_cmd = f"{basename}.exe" if os.name == 'nt' else f"./{basename}"
    os.system(run_cmd)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_now.py <file.lm>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)
    
    run_lumina(input_file)