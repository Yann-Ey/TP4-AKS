import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# os.environ.get va lire les variables que nous avons définies dans le ConfigMap et le Secret
APP_MESSAGE = os.environ.get('APP_MESSAGE', 'Message par défaut')
ALLOWED_EXT = os.environ.get('UPLOAD_ALLOWED_EXT', '.txt')
PASSWORD = os.environ.get('UPLOAD_PASSWORD', 'admin') # Vient du Secret
UPLOAD_FOLDER = '/data' # Le volume partagé

# On s'assure que le dossier de stockage existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    # Affiche le message de bienvenue et la liste des fichiers
    try:
        files = os.listdir(UPLOAD_FOLDER)
    except Exception as e:
        files = [str(e)]
    return jsonify({
        "message": APP_MESSAGE,
        "files": files,
        "info": f"Only {ALLOWED_EXT} allowed"
    })

@app.route('/upload', methods=['POST'])
def upload_file():
   
    if request.form.get('password') != PASSWORD:
        return jsonify({"error": "Mauvais mot de passe !"}), 403
    
    if 'file' not in request.files:
        return jsonify({"error": "Pas de fichier envoyé"}), 400
        
    file = request.files['file']
    
   
    if not file.filename.endswith(ALLOWED_EXT):
        return jsonify({"error": f"Extension interdite. Seulement {ALLOWED_EXT}"}), 400
        
    
    file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    return jsonify({"status": "Fichier sauvegardé avec succès !"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

    