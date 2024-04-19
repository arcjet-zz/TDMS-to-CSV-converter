from flask import Flask, request, send_from_directory, render_template_string, jsonify
from nptdms import TdmsFile
from werkzeug.utils import secure_filename
from zipfile import ZipFile
import pandas as pd
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Limit the maximum file upload size to 500MB

@app.route('/')
def index():
    return render_template_string('''<!doctype html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Convert TDMS to CSV</title>
      <link rel="icon" href="https://example.com/favicon.ico" type="image/x-icon">
      <link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/font-awesome/6.4.0/css/all.min.css">
      <script src="https://cdn.bootcdn.net/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
      <style>
        body, html { 
            height: 100%; 
            margin: 0; 
            font-family: Arial, sans-serif; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            flex-direction: column; 
            text-align: center; 
        }
        .button {
            background-color: #0052d4; 
            border: none;
            color: white;
            padding: 20px 54px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 5px;
        }
        .button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        #progress-bar { 
            width: 0%; 
            height: 30px; 
            background-color: #cccccc; 
            text-align: center; 
            color: white; 
            line-height: 30px; 
            border-radius: 5px; 
        }
        #progress-wrap { 
            width: 100%; 
            background-color: #ddd; 
            border-radius: 5px; 
            margin: 10px 0; 
            position: relative;
        }
      </style>
    </head>
    <body>
    <div>
      <h1>Convert Your TDMS Files To CSV</h1>
      <form id="upload-form" enctype="multipart/form-data">
        <input type="file" name="files" multiple required onchange="checkFiles()" id="file-input" class="file-input" style="display: none;" accept=".tdms">
        <label for="file-input" class="button"><i class="fa fa-file-upload"></i> Choose files</label>
        <button type="button" class="button" onclick="uploadFiles()" id="upload-btn" disabled><i class="fa fa-upload"></i><span> Upload and Convert</span></button>
      </form>
      <div id="progress-wrap">
        <div id="progress-bar">0%</div>
      </div>
      <button id="download-btn" class="button" disabled><i class="fa fa-download"></i><span> Download Converted Files</span></button>
    </div>

    <script>
    function checkFiles() {
      var files = document.getElementById('file-input').files;
      var allTDMS = Array.from(files).every(file => file.name.endsWith('.tdms'));
      document.getElementById('upload-btn').disabled = !allTDMS || files.length === 0;
    }

    function uploadFiles() {
      var formData = new FormData($('#upload-form')[0]);
      $.ajax({
        xhr: function() {
          var xhr = new window.XMLHttpRequest();
          xhr.upload.addEventListener("progress", function(evt) {
            if (evt.lengthComputable) {
              var percentComplete = evt.loaded / evt.total;
              var progressBar = $('#progress-bar');
              progressBar.width(percentComplete * 100 + '%');
              progressBar.text(Math.round(percentComplete * 100) + '%');
              if (percentComplete < 1) {
                progressBar.css('background-color', '#ffc107');
              } else {
                progressBar.text('Processing...');
              }
            }
          }, false);
          return xhr;
        },
        url: '/convert',
        type: 'POST',
        data: formData,
        contentType: false,
        processData: false,
        success: function(data) {
          var progressBar = $('#progress-bar');
          progressBar.text('Done!');
          progressBar.css('background-color', '#4CAF50');
          $('#download-btn').prop('disabled', false);
          $('#download-btn').click(function() {
            window.location.href = data.url;
          });
        },
        error: function(xhr) {
          var progressBar = $('#progress-bar');
          progressBar.width('100%');
          progressBar.text('Error: Please double-check your tdms file!');
          progressBar.css('background-color', 'red');
          $('#upload-btn').prop('disabled', false);
          $('#download-btn').prop('disabled', true);
        }
      });
    }
    </script>
    </body>
    </html>
    ''')

@app.route('/convert', methods=['POST'])
def convert():
    files = request.files.getlist('files')
    if not all(f.filename.endswith('.tdms') for f in files):
        return jsonify({'error': 'All files must be in .TDMS format'}), 400

    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], "converted_files.zip")
    try:
        with ZipFile(zip_path, 'w') as zipf:
            for file in files:
                original_filename = file.filename
                base_filename = os.path.splitext(original_filename)[0]  # Removes the extension from filename
                csv_filename = base_filename + '.csv'  # Append .csv to the filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
                file.save(file_path)
                tdms_file = TdmsFile.read(file_path)
                df = tdms_file.as_dataframe()
                csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                zipf.write(csv_path, arcname=csv_filename)  # Use the modified filename in the ZIP
                os.remove(csv_path)
                os.remove(file_path)
        return jsonify({'url': '/download/converted_files.zip'})
    except Exception as e:
        return jsonify({'error': 'Failed to process files: ' + str(e)}), 500


@app.route('/download/<path:filename>', methods=['GET'])
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, port=8088)
