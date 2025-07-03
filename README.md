
# Télé-Éducation Platform

Une plateforme de streaming éducatif permettant aux professeurs de diffuser des cours en direct via WebRTC et aux spectateurs de les visionner en HLS, avec des fonctionnalités interactives : quiz & commentaires.

---

## Prérequis

- **Système** : Linux (testé sur Ubuntu)
- **Logiciels** :
  - Python 3.12
  - Node.js (pour Tailwind CSS, optionnel)
  - Redis
  - MySQL
  - SRS (Simple Realtime Server) pour WebRTC et HLS
- **Navigateurs** : Chrome, Firefox ou Safari (pour HLS)

---

## 1. Installation

### a. Cloner le dépôt

```bash
git clone https://github.com/Uriel-Ondo/tnt_agricole.git
cd tnt_agricole
git checkout main
```

### b. Configurer l’environnement virtuel Python

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

### c. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### d. Configurer MySQL

1. Créez la base de données :

```bash
mysql -u admin -p
CREATE DATABASE agro;
exit
```

2. (Adaptez l’utilisateur/mot de passe selon votre config)

### e. Configurer Redis

1. Installer Redis :

```bash
sudo apt install redis-server
```

2. Lancer Redis :

```bash
sudo systemctl start redis
```

### f. Configurer les variables d’environnement

Créer un fichier `.env` dans `backend/` :

```bash
touch backend/.env
```

Exemple de contenu :

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+pymysql://admin:passer@localhost/agro
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-jwt-secret-key-here
```

---

## 2. Migrations de la base de données

```bash
cd backend
source .venv/bin/activate
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

---

## 3. Lancement de l’application

### a. Lancer SRS

```bash
sudo /usr/local/srs/objs/srs -c /usr/local/srs/conf/srs.conf
```

Vérifier que les ports sont ouverts :

```bash
lsof -i :1935,1985,8080,8000
```

### b. Lancer Flask

```bash
source .venv/bin/activate
cd backend
python run.py
```

---

## 4. Accéder à l’application

### a. Création de comptes et connexion

- Documentation API : [http://localhost:5001/apidocs](http://localhost:5001/apidocs)
- Dans l’option `register`, créez deux utilisateurs : un avec le rôle `professor`, l’autre avec le rôle `viewer`.

### b. Connexion via interface web

- Professeur : [http://localhost:5001/auth/login](http://localhost:5001/auth/login)
  - Utilisez : **prof@visiotech.me / motdepasse**
- Spectateur :
  - Utilisez : **viewer@visiotech.me / motdepasse**

---

## 5. Utilisation

### Professeur

- Créez une session sur `/sessions/create`
- Accédez à `/sessions/professor?session_id=` pour diffuser en WebRTC
- Lancez le streaming, créez des quiz

### Spectateur

- Sélectionnez une session via `/sessions/active`
- Visionnez le flux HLS via `/sessions/viewer?session_id=`
- Participez aux quiz

---

## 6. Dépannage

| Problème | Solution |
|----------|----------|
| **Erreur Socket.IO**<br> (ConnectionRefusedError: Missing token) | Vérifiez que `jwt_token` est dans le localStorage (console navigateur). Assurez-vous que `.env` contient bien `JWT_SECRET_KEY`. |
| **Flux vidéo absent** | Testez l’URL HLS dans VLC : `http://localhost:8080/hls/live/session_<id>.m3u8`.<br> Consultez `/usr/local/srs/logs/srs.log`. |
| **Base de données** | Vérifiez la variable `DATABASE_URL` dans `.env`. Réexécutez `flask db upgrade` si nécessaire. |
| **Redis** | Vérifiez que Redis fonctionne : `redis-cli ping` doit répondre `PONG`. |

---

## 7. Ressources

- [SRS (Simple Realtime Server)](https://ossrs.io/lts/zh-cn/docs/v5/doc/getting-started)
- [WebRTC - MDN](https://developer.mozilla.org/fr/docs/Web/API/WebRTC_API)
- [HLS Streaming Overview](https://developer.apple.com/documentation/http_live_streaming)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Socket.IO Documentation](https://socket.io/docs/)

---

**Besoin d’aide ou d’ajout de fonctionnalités (quiz, chat, modération…) ? Demande-moi !**
````
