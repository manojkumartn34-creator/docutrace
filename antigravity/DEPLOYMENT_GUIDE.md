# DOCUTRACE – Cloud Hosting & Deployment Guide

This guide explains how to host your **DOCUTRACE** web application online on the internet with a public URL (e.g. `https://docutrace.onrender.com`).

---

## 🏆 Option 1: Render.com (Recommended – Free & Automatic HTTPS)

**Render** is one of the best free cloud platforms for Python Flask web applications.

### Step 1: Upload Your Project to GitHub
1. Open [https://github.com](https://github.com) and create a free account.
2. Click **"New Repository"**, name it `docutrace`, and set it to **Public** (or Private).
3. In your project terminal in `d:\antigravity`, run:
   ```powershell
   git init
   git add .
   git commit -m "Initial commit of DocuTrace"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/docutrace.git
   git push -u origin main
   ```

### Step 2: Deploy on Render
1. Go to **[https://render.com](https://render.com)** and sign in with GitHub.
2. Click the blue **"New +"** button at the top &rarr; select **"Web Service"**.
3. Select your `docutrace` GitHub repository and click **Connect**.
4. Configure the settings:
   - **Name**: `docutrace-app` (or any name you choose)
   - **Region**: Choose the closest region (e.g., Singapore, Frankfurt, or Oregon)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: **Free**
5. (Optional) If using Firebase, add an Environment Variable:
   - Key: `FIREBASE_CREDENTIALS`
   - Value: paste your `firebase_config.json` contents.
6. Click **"Create Web Service"**.
7. Render will build and deploy the app in ~2 minutes and give you a free live URL:
   ```text
   https://docutrace-app.onrender.com
   ```

---

## 🐍 Option 2: PythonAnywhere (Easiest – No Git Required)

**PythonAnywhere** is designed specifically for hosting Python Flask applications with a visual file manager.

### Step 1: Create Account
1. Visit **[https://www.pythonanywhere.com](https://www.pythonanywhere.com)** and sign up for a free Beginner account.
2. Your live website URL will be: `https://yourusername.pythonanywhere.com`.

### Step 2: Upload Files
1. In PythonAnywhere dashboard, click **"Files"**.
2. Create a folder named `docutrace` and upload your project files.

### Step 3: Install Dependencies
1. Open a **Bash Console** from the dashboard.
2. Run:
   ```bash
   pip install Flask werkzeug qrcode Pillow firebase-admin
   ```

### Step 4: Configure Web App
1. Go to the **"Web"** tab &rarr; click **"Add a new web app"**.
2. Select **Flask** &rarr; **Python 3.10** (or latest).
3. Set the path to `/home/yourusername/docutrace/app.py`.
4. Click the green **"Reload yourusername.pythonanywhere.com"** button.
5. Your application is live!

---

## ⚡ Option 3: Ngrok (Instant 30-Second Public Link for Vivas / Demos)

If you need an immediate live public HTTPS link right now to show your teacher, examiner, or friends on their phone without creating cloud accounts:

1. Download **ngrok** from **[https://ngrok.com](https://ngrok.com)**.
2. Make sure your DocuTrace app is running in your terminal:
   ```powershell
   python run.py
   ```
3. Open a second terminal window and run:
   ```powershell
   ngrok http 5000
   ```
4. Ngrok will instantly give you a worldwide public URL:
   ```text
   Forwarding: https://abcd-1234.ngrok-free.app -> http://localhost:5000
   ```
5. Anyone in the world can open `https://abcd-1234.ngrok-free.app` on their phone or laptop!
