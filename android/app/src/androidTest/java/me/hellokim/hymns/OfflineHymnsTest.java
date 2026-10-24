package me.hellokim.hymns;

import static org.junit.Assert.*;

import android.graphics.Bitmap;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import java.io.File;
import java.io.FileOutputStream;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public class OfflineHymnsTest {
    private String js(ActivityScenario<MainActivity> scenario, String script) throws Exception {
        CountDownLatch done = new CountDownLatch(1);
        AtomicReference<String> value = new AtomicReference<>();
        scenario.onActivity(activity -> activity.getBridge().getWebView().evaluateJavascript(script, result -> {
            value.set(result);
            done.countDown();
        }));
        assertTrue("JavaScript callback timed out", done.await(10, TimeUnit.SECONDS));
        return value.get();
    }

    private void ready(ActivityScenario<MainActivity> scenario) throws Exception {
        for (int attempt = 0; attempt < 100; attempt++) {
            if ("true".equals(js(scenario, "document.querySelectorAll('.chorale-option').length > 10"))) return;
            Thread.sleep(200);
        }
        fail("Offline hymn dataset did not load");
    }

    private void search(ActivityScenario<MainActivity> scenario, int hymn) throws Exception {
        js(scenario, "document.getElementById('searchInput').value='" + hymn + "'; document.getElementById('searchButton').click();");
    }

    private void screenshot(int hymn) throws Exception {
        Bitmap bitmap = InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();
        File dir = InstrumentationRegistry.getInstrumentation().getTargetContext().getExternalFilesDir(null);
        try (FileOutputStream out = new FileOutputStream(new File(dir, "hymn-" + hymn + ".png"))) {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, out));
        }
        bitmap.recycle();
    }

    @Test
    public void offlineReferencesAndPreferencesSurviveRestart() throws Exception {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            scenario.onActivity(activity -> {
                activity.getBridge().getWebView().getSettings().setBlockNetworkLoads(true);
                activity.getBridge().getWebView().reload();
            });
            ready(scenario);
            for (int hymn : new int[]{5, 6, 438, 440}) {
                search(scenario, hymn);
                String codes = js(scenario, "JSON.stringify(Array.from(document.querySelectorAll('[data-chorale-number]'), e => e.dataset.choraleNumber))");
                String expected = hymn == 438 ? "\"[]\"" : hymn == 440 ? "\"[\\\"416\\\"]\"" : "\"[\\\"424\\\",\\\"563\\\"]\"";
                assertEquals("Hymn " + hymn, expected, codes);
                int verses = hymn == 5 ? 7 : hymn == 438 ? 1 : 3;
                assertEquals("true", js(scenario, "document.getElementById('results').innerText.includes('Antal vers: " + verses + "')"));
                if (hymn == 438 || hymn == 440) {
                    String label = hymn == 438 ? "Bogside 568" : "Bogside 570";
                    assertEquals("true", js(scenario, "document.querySelector('[data-reference-type=book_page]').innerText.includes('" + label + "')"));
                    assertEquals("0", js(scenario, "document.querySelectorAll('[data-reference-type=book_page] input').length"));
                }
                screenshot(hymn);
            }
            search(scenario, 5);
            js(scenario, "document.querySelector('input[value=\"kds:563\"]').click()");
            js(scenario, "document.getElementById('comment-5').value='Sunday service'; document.querySelector('.save-comment-button').click()");
        }
        // A new Activity/WebView must recover the existing on-device preference.
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            ready(scenario);
            search(scenario, 5);
            assertEquals("\"kds:563\"", js(scenario, "document.querySelector('input[type=radio]:checked').value"));
            assertEquals("\"Sunday service\"", js(scenario, "document.getElementById('comment-5').value"));
        }
    }
}
