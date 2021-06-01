from core.document import OFDFile
import os

folder = "ofds"
for path in os.listdir(folder):
    if not path.endswith(".ofd"):
        continue
    print("read file", path)
    file_path = os.path.join(folder, path)
    doc = OFDFile(file_path)
    doc.draw_document()
