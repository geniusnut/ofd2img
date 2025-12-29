import sys

import zipfile

from flask import Flask, request, send_file

sys.path.append("/root/ofd2img")
from core.document import OFDFile

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route("/convert", methods=['POST'])
def convert():
    print("Posted file: {}".format(request.files['file']))
    storage = request.files['file']

    doc = OFDFile(storage)
    paths = doc.draw_document()
    print(paths)
    d = {'data': ''}
    zip_path = storage.filename.strip('.ofd') + '.zip'
    print(zip_path)
    zipf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
    for path in paths:
        zipf.write(path)
    zipf.close()
    return send_file(zip_path,
                     mimetype='zip',
                     download_name=zip_path,
                     as_attachment=True)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=45678, debug=True)