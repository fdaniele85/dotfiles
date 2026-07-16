#! /usr/bin/env python3

import sys

def remove_command(text, command):
    """Rimuove \command{...} tenendo il contenuto, gestendo graffe annidate."""
    needle = command + '{'
    result = []
    i = 0
    while i < len(text):
        idx = text.find(needle, i)
        if idx == -1:
            result.append(text[i:])
            break
        result.append(text[i:idx])
        j = idx + len(needle)
        depth = 1
        while j < len(text) and depth > 0:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
            j += 1
        result.append(text[idx + len(needle):j - 1])
        i = j
    return ''.join(result)

def main():
    if len(sys.argv) < 3:
        print("Uso: python3 strip_cmd.py <file.tex> <\\comando> [<\\comando2> ...]")
        sys.exit(1)

    filename = sys.argv[1]
    commands = sys.argv[2:]

    with open(filename, 'r') as f:
        text = f.read()

    for cmd in commands:
        text = remove_command(text, cmd)

    print(text)

if __name__ == '__main__':
    main()