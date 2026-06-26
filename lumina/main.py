"""Main entry point for the Lumina compiler."""

import sys
import os
import argparse

import tokeniser
import parser
import checker
import codegen
import lumina_utils as utils
from errors import LuminaError, from_failure


def compile_and_build(debug: bool, video_output: str, input_file: str):
    """Compile a Lumina file and build the executable."""
    basename = os.path.splitext(os.path.basename(input_file))[0]
    c_filename = basename + ".c"

    print("=> Compiling Lumina source...")
    try:
        source = utils.read_file(input_file)
        tokens = tokeniser.tokenise(utils.explode(source))
    except LuminaError as e:
        print(e.pp(), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    try:
        prog = parser.parse(tokens)
    except Exception as e:
        err = from_failure(str(e))
        print(err.pp(), file=sys.stderr)
        sys.exit(1)

    if debug:
        print("Tokens:")
        print('\n'.join(tokeniser.print_token(t) for t in tokens))
        print("AST:")
        print(parser.ast.pp_program(prog))

    diags = checker.check(prog)
    checker.print_diagnostics(diags)

    if any(d.severity == checker.Severity.ERROR for d in diags):
        sys.exit(1)

    try:
        code = codegen.gen_program(prog, video_output)
    except Exception as e:
        err = from_failure(str(e))
        print(err.pp(), file=sys.stderr)
        sys.exit(1)

    with open(c_filename, 'w') as f:
        f.write(code)

    print(f"=> Building executable ({basename})...")
    gcc_cmd = utils.compile_cmd(c_filename, basename)
    gcc_exit_code = os.system(gcc_cmd)

    if gcc_exit_code != 0:
        print(f"Error: GCC compilation failed with code {gcc_exit_code}", file=sys.stderr)
        sys.exit(gcc_exit_code)

    return basename, prog


def build_action(debug: bool, video_output: str, input_file: str) -> None:
    """Build action for the CLI."""
    compile_and_build(debug, video_output, input_file)
    print("=> Build successful.")


def run_action(debug: bool, video_output: str, input_file: str) -> None:
    """Run action for the CLI."""
    basename, prog = compile_and_build(debug, video_output, input_file)

    print(f"=> Running {basename}...")
    if os.name == 'nt':
        run_cmd = f"{basename}.exe"
    else:
        run_cmd = f"./{basename}"
        os.system(run_cmd)

    if codegen.is_render_mode(prog):
        output_path = video_output if video_output else "output.mp4"
        print(f"Output written to {output_path}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Lumina - Graphics scripting language")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("-o", "--output", help="Specify output path for rendered video")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Compile a Lumina file")
    build_parser.add_argument("file", help="The Lumina source file")

    run_parser = subparsers.add_parser("run", help="Compile and execute a Lumina file")
    run_parser.add_argument("file", help="The Lumina source file")

    args = parser.parse_args()
    debug = args.debug
    video_output = args.output

    if args.command == "build":
        build_action(debug, video_output, args.file)
    elif args.command == "run":
        run_action(debug, video_output, args.file)


if __name__ == "__main__":
    main()