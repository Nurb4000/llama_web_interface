from flask import Flask, render_template, request, redirect, url_for
import os

app = Flask(__name__)

MODEL_PATH = '/home/user/Models'
LLAMA_SERVER_SERVICE_FILE = '/etc/systemd/system/llama-server.service'

def get_current_model():
    with open(LLAMA_SERVER_SERVICE_FILE, 'r') as file:
        lines = file.readlines()
        for line in lines:
            if '-m' in line:
                return line.split('-m ')[1].strip()
    return "Unknown"

def get_all_models():
    return [f for f in os.listdir(MODEL_PATH) if os.path.isfile(os.path.join(MODEL_PATH, f))]

def update_service_file(model_name):
    with open(LLAMA_SERVER_SERVICE_FILE, 'r') as file:
        lines = file.readlines()
    with open(LLAMA_SERVER_SERVICE_FILE, 'w') as file:
        for line in lines:
            if '-m' in line:
                file.write(f'ExecStart=/home/user/src/llama.cpp/build/bin/llama-server -m /home/user/Models/{model_name} --n-gpu-layers 50 --host 0.0.0.0\n')
            else:
                file.write(line)

@app.route('/')
def index():
    current_model = get_current_model()
    models = get_all_models()
    return render_template('index.html', current_model=current_model, models=models)

@app.route('/update', methods=['POST'])
def update():
    model_name = request.form['model']
    update_service_file(model_name)
    os.system('systemctl daemon-reload')
    os.system('systemctl restart llama-server')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090)