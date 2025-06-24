# 📡 Plateforme de Télé-Éducation

Une plateforme de **streaming éducatif en direct**, permettant aux **professeurs** de diffuser des cours via **WebRTC**, et aux **spectateurs** de les visionner en **HLS**, avec des fonctionnalités interactives :

- 💬 Commentaires
- ❓ Quiz en direct
- 🧠 Authentification JWT

---

## 🧾 Prérequis

| Élément | Description |
|--------|-------------|
| 💻 Système | Ubuntu Linux (testé sur Ubuntu 22.04) |
| 🐍 Python | Version 3.12 |
| 🟢 Node.js | Pour Tailwind CSS (optionnel) |
| 🧠 Redis | Caching et gestion de sessions |
| 🐬 MySQL | Base de données relationnelle |
| 📺 SRS | [Simple Realtime Server](https://github.com/ossrs/srs) pour WebRTC + HLS |
| 🌐 Navigateur | Chrome, Firefox ou Safari (support HLS requis) |

---

## 🔧 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/nospi510/tele_education.git
cd tele_education
git checkout api
````

### 2. Créer l'environnement virtuel

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

---

## 🗃️ Configuration des Services

### 📚 MySQL

```bash
mysql -u nospi -p
CREATE DATABASE education;
exit
```

### 🔁 Redis

```bash
sudo apt install redis-server
sudo systemctl start redis
```

### 🔐 Fichier `.env`

Crée un fichier `.env` dans le dossier `backend/` :

```bash
touch backend/.env
```

Et ajoute les variables suivantes :

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+pymysql://nospi:passer@localhost/education
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-jwt-secret-key-here
```

> Générez une clé secrète avec :
> `python3 -c "import secrets; print(secrets.token_hex(16))"`

---

## 🧱 Migrations de la base de données

```bash
cd backend
source .venv/bin/activate

flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

---

## 🚀 Lancement de l'application

### 1. Lancer SRS

```bash
sudo /usr/local/srs/objs/srs -c /usr/local/srs/conf/srs.conf
```

### 2. Vérifier les ports

```bash
lsof -i :1935,1985,8080,8000
```

### 3. Lancer Flask

```bash
cd backend
source .venv/bin/activate
python run.py
```

---

## 🔑 Accès et Création de Comptes

1. Accédez à la documentation Swagger :
   👉 [http://localhost:5001/apidocs](http://localhost:5001/apidocs)

2. Dans la section `register`, créez deux utilisateurs :

   * 👨‍🏫 `prof@visiotech.me` avec rôle `professor`
   * 🎓 `viewer@visiotech.me` avec rôle `viewer`

3. Connectez-vous à l’interface web :
   👉 [http://localhost:5001/auth/login](http://localhost:5001/auth/login)

---

## 🧠 Utilisation

### 🎥 Professeur

* Créez une session sur : `/sessions/create`
* Lancez le live WebRTC sur : `/sessions/professor?session_id=<id>`
* Générez et diffusez des quiz en direct

### 👀 Spectateur

* Accédez à : `/sessions/active`
* Visionnez la session HLS sur : `/sessions/viewer?session_id=<id>`
* Répondez aux quiz interactifs

---

## 🧯 Dépannage

### ❌ Erreur Socket.IO (ex: `ConnectionRefusedError: Missing token`)

* Vérifiez la présence de `jwt_token` dans `localStorage` (console navigateur)
* Assurez-vous que `.env` contient `JWT_SECRET_KEY`

### 📺 Flux HLS non visible

* Testez l’URL dans VLC :

  ```bash
  http://localhost:8080/hls/live/session_<id>.m3u8
  ```
* Consultez les logs SRS :

  ```bash
  tail -f /usr/local/srs/logs/srs.log
  ```

### 🛢️ Problèmes MySQL

* Vérifiez la variable `DATABASE_URL` dans `.env`
* Exécutez de nouveau :

  ```bash
  flask db upgrade
  ```

### 🔁 Problèmes Redis

* Vérifiez que Redis fonctionne :

  ```bash
  redis-cli ping
  # => PONG
  ```

---

## 📁 Structure du projet

```
tele_education/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   ├── models/
│   │   ├── templates/
│   │   └── static/
│   ├── run.py
│   ├── config.py
│   └── requirements.txt
├── frontend/
│   └── (interface web utilisateur, si activée)
├── README.md
└── .env
```

---

## 👨‍💻 Auteur

Développé par **Nick Alix** – [visiotech.me](https://visiotech.me)
