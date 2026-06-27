# 🎹 Danish Hymn → Chorale Finder
A lightweight web app that connects hymns from *Den Danske Salmebog* to their corresponding chorales. The app also shows alternative melodies and the number of verses for each hymn.

## 💡 Project Background

This project was inspired by a real-world need.

My husband is an organist in Denmark, and during church services he receives hymn numbers from the pastor. However, the corresponding melodies are not directly shown in *Den Danske Salmebog*. He must manually look up the melodies in the chorale book (*Koralbog*), which can be time-consuming.

To solve this, I built a small web application that connects hymn numbers and titles to their corresponding chorales, making it faster and easier to prepare for services. The web app also lists different meleodies that might be used, along with the number of verses for each Hymn.

---

## 📖 Problem

When preparing for church services, organists receive hymn numbers from the pastor, but the corresponding melodies are not directly shown in *Den Danske Salmebog*.

This means:

* The hymn book does **not display the melody**
* The organist must manually search the chorale book (*Koralbog*)
* This process is time-consuming and interrupts preparation

## 🤖 Use of AI

Parts of this project were developed with the assistance of ChatGPT.

AI was used to:
- Help structure and refine code
- Debug issues during development
- Improve the user interface

All logic, data processing, and final decisions were reviewed and adjusted by me & Jonas.

## 📖 Problem

When preparing for church services, musicians receive hymn numbers from the pastor. But the hymn itself is not linked to the Choral Book. This means that the musician needs to look through the Choral book manually in order to find the song.

However:

* The hymn book does **not directly show the melody**
* The organist must manually search from the chorale book
* This process is slow and frustrating


---

## 💡 Solution

This app allows users to:

* 🔍 Search hymns by number or text
* 🎼 View all matching chorales
* ⭐ Select a preferred melody
* 📝 Leave personal notes for each hymn
* 💾 Save preferences locally in the browser

---

## 🚀 Features

* Exact hymn number search (e.g. `10` only returns hymn 10 from the Choral Book)
* Text search by title or first line
* Multiple chorale matches per hymn
* Preferred melody selection with clear button
* Comment/notes for each hymn
* Danish 🇩🇰 <-> English 🇬🇧 language toggle
* Fully client-side (no backend required)

---

## 🛠️ Tech Stack

* Python (data preparation)
* JSON (dataset)
* HTML + JavaScript (frontend)

---

## 📂 Project Structure

```
Hymns/
├── index.html                  # Frontend app
├── build_dataset.py            # Scrapes hymn data
├── update_chorales.py          # Matches hymns → chorales
├── data/
│   ├── hymns_dataset.json
│   ├── hymns_dataset_updated.json
│   ├── match_audit_report.json
│   └── reg_kds.pdf
```
---

## ⚙️ How to Run Locally

### 1. Generate dataset

```bash
python3 build_dataset.py
python3 update_chorales.py
```

### 2. Start local server

```bash
python3 -m http.server 8000
```

### 3. Open in browser

```
http://localhost:8000
```

---

## 🌐 Deployment (GitHub Pages)

1. Push repository to GitHub
2. Go to **Settings → Pages**
3. Under **Source**, select:

   * Branch: `main`
   * Folder: `/ (root)`
4. Save

Your app will be available at:

```
https://your-username.github.io/repository-name/
```

---

## 📱 Usage on Mobile (Android / iPhone)

Open the app in a browser and add it to the home screen:

### Android (Chrome)

1. Open the link
2. Tap the **⋮ menu (top right)**
3. Tap **“Add to Home screen”**

### iPhone (Safari)

1. Open the link
2. Tap the **Share button**
3. Tap **“Add to Home Screen”**

This makes the app behave like a simple mobile app.

---

## 💾 Notes on Data Storage

* Preferred melodies and comments are stored in the browser (`localStorage`)
* Data is **device-specific** (not synced across devices)

---

## 🙌 Acknowledgements

* [Jonas](https://www.jonasfrederik.com/) for checking the final database, feedback, and not holding back on requests to improve the app.
- [Den Danske Salmebog Online](https://www.dendanskesalmebogonline.dk/)
- [Thor Callesen Koralbog](https://www.thor-callesen.com/koralbog/)
