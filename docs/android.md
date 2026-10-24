# Android app and Google Play

The Android app reuses the website's tested search, chorale selection, notes,
composer information and Danish/English display. All 791 hymns ship inside the
app and work offline. Chorale numbers and book pages remain distinct. No score
PDFs, lyrics, ads, analytics, login or server are added.

Working app name: **Salme og Koral**. Application ID: **me.hellokim.hymns**.
Confirm these before the first Play upload: the application ID is permanent
once published. Version: 1.0.0, versionCode: 1.

## Build and test

GitHub Actions → **Build Android app** runs on pull requests and main. It validates
the dataset, builds a debug APK and an **unsigned** release AAB, runs Android lint,
and tests offline search for 5, 6, 438 and 440 on an API 35 emulator. It also checks
that a saved chorale and note survive reopening. Screenshots and test reports
are uploaded as artifacts. A successful build does not publish to Google Play.

The debug APK is for testing only. Its CI debug signing key is disposable; do not
use it for distributing updates or storing irreplaceable notes. Reinstalling an
APK signed with a different key may require uninstalling and losing local data.

For local builds, install Node 22+, Python requirements, and Android Studio
2025.2.1 or newer with SDK 36 and Java 21. From a clean, committed checkout:

```sh
npm ci
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
npm test
python build_mobile.py
npm run android:sync
npm run android:open
```

`build_mobile.py` refuses an existing output directory to prevent stale data from
entering an app. Before rebuilding, remove only the generated `mobile-www/`
directory. It packages the same validated JSON as the website, with its hash check.
Capacitor copies that bundle into the Android assets. Do not set `server.url`:
that would replace the offline bundle with a remote website.

## Sign and upload

1. Test on a real phone, including airplane mode, Danish/English, text scaling,
   landscape, preferences, notes, and an update installed over the previous build.
2. In Android Studio choose **Build → Generate Signed App Bundle / APK → Android
   App Bundle**. Create or select your own upload keystore and choose `release`.
   Keep the key and passwords in secure storage outside this repository.
   Keystores are ignored by Git. The CI AAB is unsigned and cannot be uploaded as-is.
3. In your Google Play Console account create the app and configure Play App
   Signing. Upload the signed AAB to **internal testing** first.
4. Complete the store listing, support contact, public privacy-policy URL,
   content rating, target audience, ads declaration and Data safety questionnaire.
   The app collects/transmits no user data; preferences and notes stay locally.
   Verify this declaration again if plugins or networking are added.
5. Complete any testing and production-access requirements shown for your account.
   Review Google's pre-launch report before requesting production publication.

No signing key, Play credentials, account registration, payment, acceptance of
Play terms, upload to Play, or production release is performed by the repository workflow.

## First-time Play Console account

Start at [Play Console signup](https://play.google.com/console/signup) with the
Google account you want to own the app. Choose Personal for your own hobby project,
or Organization if publishing for a business or organization. Complete the
identity/contact verification, review the developer agreement, and pay Google's
one-time US$25 registration fee yourself. A new personal account also needs
Android-device verification. See [Google's registration guide](https://support.google.com/googleplay/android-developer/answer/6112435).

New personal accounts currently need a closed test with at least **12 testers
opted in continuously for 14 days** before applying for production access.
Internal testing and the CI emulator tests do not replace that requirement.
Follow [Google's testing requirements](https://support.google.com/googleplay/android-developer/answer/14151465)
and the requirements displayed in your account; check them again before launch.

## Updates and storage

The website still updates automatically from main. Android builds are generated
from main too, but installed Android apps receive data/UI updates **through a new
Google Play app release**, not from the live website. Increase `versionCode` for
every Play upload; change `versionName` for the displayed release version in
`android/app/build.gradle`. Gradle overrides are available as
`-PappVersionCode=2 -PappVersionName=1.0.1`.

Use the same application ID and signing identity for updates. Local preferences
and notes are kept in the app's WebView storage; they are separate from browser
storage and do not sync. Android backups and device transfer are excluded.
Clearing app storage or uninstalling removes the data. No export is implemented.

## Store materials to review

- Icon: `mobile/play-icon.png` (512 × 512).
- Suggested short description: “Find Danish hymn chorale numbers, alternatives and verse counts offline.”
- Suggested full description: “Salme og Koral helps organists find chorale numbers
  in Koralbog til Den Danske Salmebog for all 791 hymns. Search by hymn number or
  title, see alternative melodies and verse counts, choose a preferred chorale,
  and keep personal notes. Book-page references are clearly distinguished from
  chorale numbers. Works offline, with Danish and English display. Includes
  reference metadata, not hymn lyrics or sheet music. Notes stay on your device.”
- In-app privacy text: `mobile/about.html`. Before publication, provide a public
  privacy page with your support contact and review the source-data permissions.
- Device screenshots are captured by the Android tests. Review them for the
  store listing; a feature graphic and final listing languages remain to prepare.

Official guidance: [Capacitor Android setup](https://capacitorjs.com/docs/android),
[environment requirements](https://capacitorjs.com/docs/getting-started/environment-setup),
[Google Play app setup](https://support.google.com/googleplay/android-developer/answer/9859152).
