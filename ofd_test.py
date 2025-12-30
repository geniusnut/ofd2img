import argparse
import os
import sys
from pathlib import Path

# Add paths for module resolution
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.document import OFDFile


def process_ofd_file(file_path, output_path=None):
    """Process a single OFD file"""
    try:
        doc = OFDFile(file_path)
        result = doc.draw_document()
        print(f"✓ Processed: {file_path}")
        if output_path:
            print(f"  Output: {result}")
        return True
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Convert OFD file(s) to image")
    parser.add_argument("path", help="Path to OFD file or folder containing OFD files")
    parser.add_argument(
        "-o", "--output", default=None, help="Output folder path (optional)"
    )

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path '{args.path}' not found", file=sys.stderr)
        sys.exit(1)

    # If output is specified, ensure output directory exists
    if args.output:
        os.makedirs(args.output, exist_ok=True)

    processed = 0
    failed = 0

    if os.path.isfile(args.path):
        # Single file
        if args.path.lower().endswith(".ofd"):
            if process_ofd_file(args.path, args.output):
                processed += 1
            else:
                failed += 1
        else:
            print(f"Error: '{args.path}' is not an OFD file", file=sys.stderr)
            sys.exit(1)
    elif os.path.isdir(args.path):
        # Process folder
        ofd_files = list(Path(args.path).glob("**/*.ofd"))
        if not ofd_files:
            print(f"Warning: No OFD files found in '{args.path}'")
            sys.exit(0)

        print(f"Found {len(ofd_files)} OFD file(s) to process...")
        for ofd_file in ofd_files:
            if process_ofd_file(str(ofd_file), args.output):
                processed += 1
            else:
                failed += 1
    else:
        print(
            f"Error: '{args.path}' is neither a file nor a directory", file=sys.stderr
        )
        sys.exit(1)

    print(f"\nCompleted: {processed} processed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
