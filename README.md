Télé-Éducation Platform
Une plateforme de streaming éducatif permettant aux professeurs de diffuser des cours en direct via WebRTC et aux spectateurs de les visionner en HLS, avec des fonctionnalités interactives comme des quiz et des commentaires.
Prérequis

Système : Linux (testé sur Ubuntu)
Logiciels :
Python 3.12
Node.js (pour Tailwind CSS, optionnel)
Redis
MySQL
SRS (Simple Realtime Server) pour WebRTC et HLS


Navigateurs : Chrome, Firefox, ou Safari (pour HLS)

- Installation

    Cloner le dépôt :
    git clone <url-du-dépôt>
    cd tele_education


- Configurer l'environnement virtuel :
    cd backend
    python -m venv .venv
    source .venv/bin/activate


- Installer les dépendances Python :
    pip install -r requirements.txt


- Configurer MySQL :

    Créez la base de données education :mysql -u nospi -p
    CREATE DATABASE education;
    exit




- Configurer Redis :

    Installez Redis :sudo apt install redis-server
    Lancez Redis :sudo systemctl start redis




- Configurer les variables d'environnement :

    Créez un fichier .env dans backend/ :touch backend/.env

    FLASK_ENV=development
    SECRET_KEY=your-secret-key-here
    DATABASE_URL=mysql+pymysql://nospi:passer@localhost/education
    REDIS_URL=redis://localhost:6379/0
    JWT_SECRET_KEY=your-jwt-secret-key-here




- Migrations de la base de données

    cd backend
    source .venv/bin/activate
    flask db init


    Créer les migrations :
    flask db migrate -m "Initial migration"


    Appliquer les migrations :
    flask db upgrade




**Lancement de l'application**

**Lancer SRS :**
sudo /usr/local/srs/objs/srs -c /usr/local/srs/conf/srs.conf


Vérifiez les ports :lsof -i :1935,1985,8080,8000




**Lancer Flask :**
source .venv/bin/activate
cd backend
python run.py


Accéder à l'application :


- Création de comptes  et connexion 
    Acceder a : http://localhost:5001/apidocs
    et dans l'option register creer deux utilisateurs, un avec le rle professor et l'autre avec le role viewer

    Ensuite aller sur l'interface web : http://localhost:5001/auth/login 
    Connectez-vous avec :
    Professeur : prof@visiotech.me / motdepasse
    Spectateur : viewer@visiotech.me / motdepasse





- Utilisation

    - Professeur :

        Créez une session sur /sessions/create.
        Accédez à /sessions/professor?session_id=<id> pour diffuser via WebRTC.
        Lancez le streaming, créez des quiz.


    - Spectateur :

        Sélectionnez une session sur /sessions/active.
        Visionnez le flux HLS sur /sessions/viewer?session_id=<id>.
        Participez aux quiz.



Dépannage

Erreur Socket.IO (ConnectionRefusedError: Missing token) :
Vérifiez que jwt_token est dans localStorage (console du navigateur).
Assurez-vous que .env contient JWT_SECRET_KEY.


Flux vidéo absent :
Testez l'URL HLS dans VLC : http://localhost:8080/hls/live/session_<id>.m3u8.
Consultez /usr/local/srs/logs/srs.log.


Base de données :
Vérifiez DATABASE_URL dans .env.
Réexécutez flask db upgrade si nécessaire.


Redis :
Vérifiez que Redis est en cours d'exécution :redis-cli ping





