import json
import sys
import os
from argparse import ArgumentParser
import pty
import shlex
import re
import subprocess
from tempfile import NamedTemporaryFile


class PtyDotRenderer:
    GRAPH_LABEL_RE = re.compile(rb'^digraph\b[^=}]*\blabel=(?:"|<(?:<[^>]*>)*)([^"<>]*?Graph)')
    WHITESPACE_RE = re.compile(r'\s')

    def __init__(self, out_dir: str):
        self._read_buffer = b''
        self._out_dir = out_dir
        self._ctr = {}

    def read(self, fd):
        try:
            chunk = os.read(fd, 10000)
        except OSError:
            if self._read_buffer:
                self.try_parse(self._read_buffer)
                self._read_buffer = b''
            return b''

        self._read_buffer += chunk
        offset = 0
        while (line_feed := self._read_buffer.find(b'\r', offset)) != -1:
            self.try_parse(self._read_buffer[offset:line_feed])
            offset = line_feed + 2
        self._read_buffer = self._read_buffer[offset:]
        return chunk

    def try_parse(self, line: bytes):
        try:
            info = json.loads(line)
            name = info['name']
            data = info['data']
            if 'Graph' in name:
                return self.render(name, data.encode('utf-8'))
        except (json.JSONDecodeError, KeyError):
            pass

        match = PtyDotRenderer.GRAPH_LABEL_RE.match(line)
        if match:
            return self.render(match.group(1).decode('utf-8'), line)

    def render(self, name: str, dot_source: bytes):
        seq_no = self._ctr.get(name, 0) + 1
        self._ctr[name] = seq_no

        compact_name = PtyDotRenderer.WHITESPACE_RE.sub('', name)
        out_path = os.path.join(self._out_dir, f'{compact_name}-{seq_no}.png' if seq_no > 1 else f'{compact_name}.png')

        try:
            with NamedTemporaryFile() as source_file:
                source_file.write(dot_source)
                source_file.flush()
                subprocess.run(f'dot -Tpng > {shlex.quote(out_path)} < {shlex.quote(source_file.name)}', shell=True)
        except OSError as e:
            raise RuntimeError(e)

    def counts(self):
        return {**self._ctr}


def main():
    parser = ArgumentParser(description='Launch a Celerity application and render its CDAG/TDAGs.')
    parser.add_argument('--out-dir', '-o', default=os.getcwd(),  help='output directory')
    parser.add_argument('command', nargs='+', help='command line, passed to sh')
    args = parser.parse_args()

    cmdline = ' '.join(shlex.quote(c) for c in args.command)

    renderer = PtyDotRenderer(args.out_dir)
    try:
        status = os.waitstatus_to_exitcode(pty.spawn(['/bin/sh', '-c', cmdline], renderer.read))
    except Exception as e:
        print(e, file=sys.stderr)
        return 1

    counts = renderer.counts()
    if counts:
        print('Rendered', ', '.join(f'{n} {g}s' for g, n in counts.items()), 'to', args.out_dir)
    else:
        print('Rendered nothing')

    return status


if __name__ == '__main__':
    sys.exit(main())
