import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GRPC_VERSION = '1.44.0'
PROTOC_DOCKER_IMAGE_VERSION = '0'

SCRIPT_DIR = Path(os.path.dirname(os.path.realpath(sys.argv[0]))).resolve()


def validate_run_result(run_result):
    if run_result.returncode != 0:
        if run_result.stdout:
            print(run_result.stdout)

        print(f"Failed to execute external command: \"{' '.join(run_result.args)}\"", file=sys.stderr)
        print(run_result.stderr, file=sys.stderr)
        sys.exit(run_result.returncode)


def compose_docker_image_name():
    splitted_version = GRPC_VERSION.split('.')
    image_version = '.'.join(splitted_version[0:2]) + '_' + PROTOC_DOCKER_IMAGE_VERSION

    return f"namely/protoc-all:{image_version}"


def checkout_commit(commit_hash):
    validate_run_result(subprocess.run(['git', 'fetch', '--all'], capture_output=True, cwd=SCRIPT_DIR, text=True))
    validate_run_result(
        subprocess.run(['git', 'checkout', commit_hash], capture_output=True, cwd=SCRIPT_DIR, text=True))


def build(commit, output, language, is_legacy):
    tmp_dir_path = Path(os.path.join(tempfile.gettempdir(), f"tolar_proto_{commit}"))
    tmp_dir_path.mkdir(parents=True, exist_ok=True)

    output_dir_path = Path(output).resolve()
    shutil.rmtree(output_dir_path, ignore_errors=True)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    in_dir = '/defs/in'
    out_dir = '/defs/out'

    command = ['docker', 'run', '-v']

    if is_legacy:
        command.append(f"{SCRIPT_DIR.parent.parent}:{in_dir}")
    else:
        command.append(f"{SCRIPT_DIR}:{in_dir}")

    command.extend(['-v', f"{tmp_dir_path}:{out_dir}",
                    compose_docker_image_name(), '-d', in_dir, '-o', out_dir, '-l', language])

    if is_legacy:
        command.extend(['-i', str(in_dir)])

    validate_run_result(subprocess.run(command, capture_output=True, text=True))

    shutil.copytree(tmp_dir_path / 'tolar' / 'proto', output_dir_path, dirs_exist_ok=True)


def main(argv, arc):
    arg_parse = argparse.ArgumentParser()
    arg_parse.add_argument('--output', type=str, required=True)
    arg_parse.add_argument('--language', type=str, required=True)
    arg_parse.add_argument('--commit', type=str)
    arg_parse.add_argument('--legacy', action='store_true', default=True)

    args = arg_parse.parse_args()

    if args.commit is not None:
        checkout_commit(args.commit)

    build(args.commit, args.output, args.language, args.legacy)

    return 0


if __name__ == '__main__':
    main(sys.argv, len(sys.argv))
