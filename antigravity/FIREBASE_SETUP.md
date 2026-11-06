# How to Connect Firebase Cloud Firestore to DOCUTRACE

This guide shows you how to connect **Google Firebase Cloud Firestore** so that user registration and login details are securely stored in the online cloud database.

---

## 5-Minute Quick Setup

### Step 1: Create a Free Firebase Project
1. Open your browser and go to: **[https://console.firebase.google.com/](https://console.firebase.google.com/)**
2. Sign in with your Google account.
3. Click **"Add project"** (or "Create a project").
4. Enter a project name, e.g., `docutrace-cloud`, and click **Continue**.
5. (Optional) You can disable Google Analytics, then click **Create project**.

---

### Step 2: Enable Cloud Firestore Database
1. In the left navigation menu, click **Build** &rarr; **Firestore Database**.
2. Click the **"Create database"** button.
3. Select your preferred database location (e.g., `asia-south1` or `us-central1`).
4. In Secure Rules, select **"Start in test mode"** (allows instant read/write for your project).
5. Click **Enable**.

---

### Step 3: Download Your Service Account Private Key
1. Click the **Gear icon (⚙️)** next to "Project Overview" in the top left &rarr; select **Project settings**.
2. Click on the **Service accounts** tab at the top.
3. Under the code snippet, make sure **Python** is selected.
4. Click the blue **"Generate new private key"** button.
5. Click **"Generate key"** in the confirmation popup. A `.json` file will download to your computer.

---

### Step 4: Add the Key to Your DocuTrace Project
1. Move the downloaded `.json` file into your project folder: `d:\antigravity\`
2. Rename the file to:
   ```text
   firebase_config.json
   ```
   *(Ensure the filename is exactly `firebase_config.json`)*

---

### Step 5: Install Dependency & Start DocuTrace
Open your terminal in `d:\antigravity` and run:

```powershell
pip install firebase-admin
python run.py
```

You will see:
```text
 [✓] Cloud Storage: Connected to Firebase Cloud Firestore
```

And in your browser navbar, the badge will glow green:
```text
☁️ FIRESTORE ONLINE
```

---

## What Happens When Cloud Firestore is Connected?

- **User Registration**: When a user registers, their username, email, and salted cryptographic password hash are saved directly to the **`users`** collection in Firebase Cloud Firestore.
- **User Authentication**: When logging in, credentials are confirmed against the live Cloud Firestore database.
- **Admin Tool**: Running `python change_admin.py` updates the admin credentials both locally and in the cloud!
- **Zero Downtime Fallback**: If internet connection drops or the JSON file is removed, DocuTrace automatically falls back to local SQLite without crashing.
