import argparse
import os
import sys

# Add paths for module resolution
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.document import OFDFile


def main():
    parser = argparse.ArgumentParser(description="Convert OFD file to image")
    parser.add_argument("file_path", help="Path to the OFD file to process")
    parser.add_argument(
        "-o", "--output", default=None, help="Output file path (optional)"
    )

    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        print(f"Error: File '{args.file_path}' not found", file=sys.stderr)
        sys.exit(1)

    try:
        doc = OFDFile(args.file_path)
        result = doc.draw_document()
        print(result)
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
