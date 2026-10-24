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
├── index.html                        # Loads data/hymns_dataset_updated.json
├── build_dataset.py                  # Structured website metadata scraper
├── update_chorales.py                # Supported, validated mapping builder
├── update_chorales_v4.py             # Compatibility entry point to the same builder
├── build_release.py                  # Package frontend + exact hashed dataset
├── verify_release.py                 # Verify local/live files against a commit
├── tests/                            # Offline HTML, PDF, dataset and frontend tests
├── docs/dataset-audit.md              # Findings and source-resolution policy
└── data/
    ├── hymns_dataset.json             # Website metadata with explicit recording URLs
    ├── hymns_dataset_updated.json     # Generated application data
    ├── melody_mapping_audit.json      # Reproducible audit of all 791 hymns
    ├── reference_corrections.json     # Reviewed source conflicts with evidence
    ├── source_manifest.json           # Hashes of audited source pages and PDFs
    ├── reg_kds.pdf
    └── melodihenvisning.pdf
```
---

## ⚙️ How to Run Locally

### 1. Install dependencies and validate the bundled data

Python 3.10+ and Node.js 22+ are supported. A website connection is only needed
when refreshing source metadata; normal builds and tests use committed inputs.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python update_chorales.py --check
python -m unittest discover -s tests -v
node tests/test_frontend.cjs
```

To refresh website metadata and regenerate the application data:

```bash
python build_dataset.py --cache-dir .cache/hymns
python update_chorales.py
```

Use a fresh cache directory when a new website snapshot is required. The scraper
aborts on failed requests or invalid pages, keeping the previous JSON intact.
Review `data/melody_mapping_audit.json` and any source conflicts before committing.
The application uses only `data/hymns_dataset_updated.json`; the old 11-hymn root
sample has been removed. Both mapping script names now run the same builder.

See [the dataset audit](docs/dataset-audit.md) for the mapping and verse-count
policy, liturgical exceptions, and validation coverage.

### 2. Start local server

```bash
python3 -m http.server 8000
```

### 3. Open in browser

```
http://localhost:8000
```

---

## 🌐 Release packaging and deployment

Do not merge or deploy this PR without approval. CI only validates and uploads a
release artifact; it has no deployment step or deployment permissions.

After approval, deploy the **whole release bundle** built from the merged commit,
not separate copies of `index.html` and JSON. The bundle pins the frontend to a
content-hashed dataset and verifies its digest before displaying any hymns.
See [deployment and live verification](docs/deployment.md) for the approval-gated
procedure and the read-only command that checks all live files against the
merged repository commit.

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
