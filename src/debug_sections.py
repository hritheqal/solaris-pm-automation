from pathlib import Path
import re
import sys


def read_file(path):
    return Path(path).read_text(errors="ignore")


def extract_sections(text):
    sections = {}

    pattern = re.compile(
        r"Section\s*:\s*(.*?)\n"
        r"Command\s*:\s*(.*?)\n"
        r"Output\s*:\s*\n"
        r"(.*?)(?=\nSection\s*:|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(text):
        section_name = match.group(1).strip()
        command = match.group(2).strip()
        output = match.group(3).strip()

        sections[section_name] = {
            "command": command,
            "output": output,
        }

    return sections


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python debug_sections.py ..\\inputs\\your_file.txt")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    text = read_file(input_file)

    sections = extract_sections(text)

    print()
    print(f"File: {input_file}")
    print(f"Total sections found: {len(sections)}")
    print()

    for section_name, data in sections.items():
        print("=" * 70)
        print(f"Section : {section_name}")
        print(f"Command : {data['command']}")
        print("-" * 70)

        output_lines = data["output"].splitlines()
        output_preview = output_lines[:8]

        for line in output_preview:
            print(line)

        if len(output_lines) > 8:
            print("...")

        print()


if __name__ == "__main__":
    main()