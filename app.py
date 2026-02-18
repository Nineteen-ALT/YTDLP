from flask import Flask, request, render_template_string, jsonify, send_from_directory
import yt_dlp
import os
import threading
import re

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

progress_data = {
    "percent": 0,
    "status": "idle",
    "filename": None,
    "error": None
}

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def download_audio(url, quality):
    global progress_data

    progress_data["status"] = "downloading"
    progress_data["percent"] = 0
    progress_data["filename"] = None
    progress_data["error"] = None

    try:
        def hook(d):
            if d['status'] == 'downloading':
                percent_str = d.get('_percent_str', '').replace('%', '').strip()
                try:
                    progress_data["percent"] = float(percent_str)
                except:
                    pass

            if d['status'] == 'finished':
                progress_data["percent"] = 100

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'progress_hooks': [hook],
            'noplaylist': True,
            'quiet': True,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'remote_components': ['ejs:github'],
            'js_runtimes': {
                'node': {}
            },
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }]
        }


        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_path = ydl.prepare_filename(info)
            final_path = os.path.splitext(final_path)[0] + ".mp3"

            filename = sanitize_filename(os.path.basename(final_path))
            progress_data["filename"] = filename
            progress_data["status"] = "done"

    except Exception as e:
        progress_data["status"] = "error"
        progress_data["error"] = str(e)


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Downloader MP3</title>
</head>
<body style="background:#111;color:white;text-align:center;margin-top:60px;font-family:Arial;">

<div style="background:#1e1e1e;padding:30px;display:inline-block;border-radius:12px;width:500px;">
<h2>Downloader MP3</h2>

<input id="url" type="text" placeholder="Cole o link aqui"
style="width:100%;padding:10px;border-radius:6px;border:none;"><br><br>

<select id="quality" style="padding:8px;border-radius:6px;">
    <option value="128">128 kbps</option>
    <option value="192" selected>192 kbps</option>
    <option value="320">320 kbps</option>
</select><br><br>

<button onclick="startDownload()" style="padding:10px 20px;border-radius:6px;border:none;cursor:pointer;">
Baixar
</button>

<br><br>

<div style="width:100%;background:#333;border-radius:6px;">
    <div id="bar" style="width:0%;height:20px;background:lime;border-radius:6px;"></div>
</div>

<div id="status" style="margin-top:15px;"></div>

</div>

<script>
let interval = null;

function startDownload() {
    const url = document.getElementById("url").value;
    const quality = document.getElementById("quality").value;

    document.getElementById("bar").style.width = "0%";
    document.getElementById("status").innerHTML = "Iniciando...";

    fetch("/start", {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url: url, quality: quality})
    });

    if (interval) clearInterval(interval);

    interval = setInterval(() => {
        fetch("/progress")
        .then(res => res.json())
        .then(data => {

            document.getElementById("bar").style.width = data.percent + "%";
            document.getElementById("status").innerHTML = data.percent + "%";

            if (data.status === "done") {
                clearInterval(interval);
                document.getElementById("status").innerHTML =
                "Download concluído<br><a href='/download/" + data.filename + "' style='color:lime;'>Clique para baixar</a>";
            }

            if (data.status === "error") {
                clearInterval(interval);
                document.getElementById("status").innerHTML =
                "<span style='color:red'>" + data.error + "</span>";
            }

        });
    }, 1000);
}
</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/start", methods=["POST"])
def start():
    data = request.get_json()
    url = data["url"]
    quality = data["quality"]

    thread = threading.Thread(target=download_audio, args=(url, quality))
    thread.start()

    return jsonify({"status": "started"})

@app.route("/progress")
def progress():
    return jsonify(progress_data)

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run()

