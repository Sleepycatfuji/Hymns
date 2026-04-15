# 🎹 Danish Hymn → Chorale Finder

A simple web app that helps musicians quickly find the correct chorale(s) for hymns in *Den Danske Salmebog*.

---

## 🚀 Live Demo

👉 https://hellokim.me/hymns/

---

## 💡 Project Background

This project was inspired by a real-world need.

My husband is an organist in Denmark, and during church services he receives hymn numbers from the pastor. However, the corresponding melodies are not directly shown in *Den Danske Salmebog*. He must manually look up the melodies in the chorale book (*Koralbog*), which can be time-consuming.

To solve this, I built a small web application that connects hymn numbers and titles to their corresponding chorales, making it faster and easier to prepare for services.

---

## 📖 Problem

When preparing for church services, musicians receive hymn numbers from the pastor.

However:

* The hymn book does **not directly show the melody**
* The organist must manually search the chorale book (*Koralbog*)
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

* Exact hymn number search (e.g. `10` only returns hymn 10)
* Text search by hymn nuber or first line
* Number of verses in each hymn
* Multiple chorale matches per hymn
* Preferred melody selection 
* Personal comment section for each hymn
* Danish 🇩🇰 <-> English 🇬🇧 language toggle
* Fully client-side (no backend required)

---

## 🛠️ Tech Stack

* Python (data preparation)
* JSON (dataset)
* HTML + JavaScript (frontend)

---

## 📂 Project Structure
Hymns/
├── index.html
├── build_dataset.py
├── update_chorales.py
├── data/
│ ├── hymns_dataset.json
│ ├── hymns_dataset_updated.json
│ ├── match_audit_report.json
│ └── reg_kds.pdf


---

## ⚙️ How to Run Locally

### 1. Generate dataset

```bash
python3 build_dataset.py
python3 update_chorales.py
```
2. Start local server
```
python3 -m http.server 8000
```
4. Open in browser
```
http://localhost:8000
```

🌐 Deployment

This project is deployed via GitHub Pages:

👉 https://hellokim.me/hymns/

💾 Notes on Data Storage
Preferences and comments are stored using browser localStorage
Data is device-specific (not synced across devices)

🙌 Acknowledgements
* [Jonas Frederik](https://www.jonasfrederik.com/) for validating the hymn dataset 
* [Den Danske Salmebog Online](https://www.dendanskesalmebogonline.dk/)
* [Thor Callesen Koralbog](https://www.thor-callesen.com/koralbog/pdf/reg_kds.pdf)

👤 Author
Kim Minamoto

