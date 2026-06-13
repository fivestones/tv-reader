package im.dat.tvreader

import android.annotation.SuppressLint
import android.app.Activity
import android.graphics.Color
import android.text.InputType
import android.os.Bundle
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.view.Window
import android.view.WindowManager
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var root: FrameLayout
    private lateinit var webView: WebView
    private lateinit var errorView: TextView
    private lateinit var serverOverlay: LinearLayout
    private lateinit var serverInput: EditText
    private var currentServerUrl = ""

    @Suppress("DEPRECATION")
    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestWindowFeature(Window.FEATURE_NO_TITLE)
        window.setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        root = FrameLayout(this).apply {
            setBackgroundColor(Color.BLACK)
            layoutParams = FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            )
        }

        errorView = TextView(this).apply {
            setTextColor(Color.rgb(255, 247, 223))
            setBackgroundColor(Color.rgb(5, 5, 5))
            textSize = 28f
            gravity = Gravity.CENTER
            visibility = View.GONE
            setPadding(48, 48, 48, 48)
            layoutParams = FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            )
        }

        webView = WebView(this).apply {
            setBackgroundColor(Color.BLACK)
            isFocusable = true
            isFocusableInTouchMode = true
            overScrollMode = View.OVER_SCROLL_NEVER
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.cacheMode = WebSettings.LOAD_DEFAULT
            settings.mediaPlaybackRequiresUserGesture = false
            webChromeClient = WebChromeClient()
            addJavascriptInterface(AndroidBridge(), "AndroidTvReader")
            webViewClient = object : WebViewClient() {
                override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                    errorView.visibility = View.GONE
                }

                override fun onReceivedError(
                    view: WebView?,
                    request: WebResourceRequest?,
                    error: WebResourceError?,
                ) {
                    if (request?.isForMainFrame == true) {
                        showError(error?.description?.toString() ?: getString(R.string.load_error))
                    }
                }
            }
            layoutParams = FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            )
        }

        serverOverlay = buildServerOverlay()

        root.addView(webView)
        root.addView(errorView)
        root.addView(serverOverlay)
        setContentView(root)

        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        currentServerUrl = savedServerUrl()
        if (currentServerUrl.isBlank()) {
            showServerOverlay()
        } else {
            webView.loadUrl(tvUrlForServer(currentServerUrl))
        }
        webView.requestFocus()
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (event.action != KeyEvent.ACTION_DOWN || event.repeatCount > 0) {
            return super.dispatchKeyEvent(event)
        }

        if (serverOverlay.visibility == View.VISIBLE) {
            if (event.keyCode == KeyEvent.KEYCODE_BACK && currentServerUrl.isNotBlank()) {
                hideServerOverlay()
            }
            return true
        }

        if (errorView.visibility == View.VISIBLE && event.keyCode == KeyEvent.KEYCODE_DPAD_CENTER) {
            webView.reload()
            return true
        }

        return when (event.keyCode) {
            KeyEvent.KEYCODE_BACK,
            KeyEvent.KEYCODE_MENU,
            -> openSettings()

            KeyEvent.KEYCODE_DPAD_RIGHT,
            KeyEvent.KEYCODE_MEDIA_NEXT,
            KeyEvent.KEYCODE_SPACE,
            KeyEvent.KEYCODE_ENTER,
            KeyEvent.KEYCODE_DPAD_CENTER,
            -> sendReaderCommand("right")

            KeyEvent.KEYCODE_DPAD_LEFT,
            KeyEvent.KEYCODE_MEDIA_PREVIOUS,
            -> sendReaderCommand("left")

            else -> super.dispatchKeyEvent(event)
        }
    }

    private fun sendReaderCommand(command: String): Boolean {
        webView.evaluateJavascript(
            "window.tvReaderCommand && window.tvReaderCommand(${command.jsString()})",
            null,
        )
        return true
    }

    private fun openSettings(): Boolean {
        if (errorView.visibility == View.VISIBLE || webView.url.isNullOrBlank()) {
            showServerOverlay()
            return true
        }
        webView.evaluateJavascript(
            """
                if (window.tvReaderOpenSettings) {
                    window.tvReaderOpenSettings();
                } else {
                    var overlay = document.querySelector('.settings-overlay');
                    if (overlay) overlay.classList.remove('hidden');
                }
            """.trimIndent(),
            null,
        )
        return true
    }

    private fun showError(message: String) {
        errorView.text = getString(R.string.error_template, tvUrlForServer(currentServerUrl), message)
        errorView.visibility = View.VISIBLE
    }

    private fun String.jsString(): String {
        return "'" + replace("\\", "\\\\").replace("'", "\\'") + "'"
    }

    private fun buildServerOverlay(): LinearLayout {
        val paper = Color.rgb(255, 247, 223)
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            visibility = View.GONE
            setBackgroundColor(Color.argb(230, 0, 0, 0))
            setPadding(72, 72, 72, 72)
            layoutParams = FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            )
        }

        panel.addView(TextView(this).apply {
            text = getString(R.string.server_settings_title)
            setTextColor(paper)
            textSize = 34f
            gravity = Gravity.CENTER
        })

        panel.addView(TextView(this).apply {
            text = getString(R.string.server_settings_body)
            setTextColor(Color.rgb(214, 203, 174))
            textSize = 20f
            gravity = Gravity.CENTER
            setPadding(0, 18, 0, 24)
        })

        serverInput = EditText(this).apply {
            setSingleLine(true)
            inputType = InputType.TYPE_TEXT_VARIATION_URI
            hint = getString(R.string.server_url_hint)
            textSize = 22f
            setTextColor(Color.rgb(22, 19, 14))
            setHintTextColor(Color.rgb(120, 109, 89))
            setPadding(18, 12, 18, 12)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            ).apply {
                width = 760
            }
        }
        panel.addView(serverInput)

        panel.addView(Button(this).apply {
            text = getString(R.string.server_save_button)
            textSize = 20f
            setOnClickListener { saveServerFromInput() }
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            ).apply {
                topMargin = 24
            }
        })

        return panel
    }

    private fun showServerOverlay() {
        serverInput.setText(currentServerUrl.ifBlank { BuildConfig.TV_READER_SERVER_URL })
        serverOverlay.visibility = View.VISIBLE
        serverInput.requestFocus()
    }

    private fun hideServerOverlay() {
        serverOverlay.visibility = View.GONE
        webView.requestFocus()
    }

    private fun saveServerFromInput() {
        val normalized = normalizeServerUrl(serverInput.text.toString())
        if (normalized.isBlank()) {
            serverInput.error = getString(R.string.server_url_required)
            return
        }
        loadServer(normalized)
    }

    private fun loadServer(serverUrl: String) {
        currentServerUrl = normalizeServerUrl(serverUrl)
        getPreferences(MODE_PRIVATE)
            .edit()
            .putString(PREF_SERVER_URL, currentServerUrl)
            .apply()
        hideServerOverlay()
        errorView.visibility = View.GONE
        webView.loadUrl(tvUrlForServer(currentServerUrl))
        webView.requestFocus()
    }

    private fun savedServerUrl(): String {
        val saved = getPreferences(MODE_PRIVATE).getString(PREF_SERVER_URL, "") ?: ""
        return normalizeServerUrl(saved.ifBlank { BuildConfig.TV_READER_SERVER_URL })
    }

    private fun normalizeServerUrl(value: String): String {
        var text = value.trim()
        if (text.isBlank()) {
            return ""
        }
        if (!text.contains("://")) {
            text = "http://$text"
        }
        text = text.trimEnd('/')
        if (text.endsWith("/tv")) {
            text = text.removeSuffix("/tv")
        }
        return text.trimEnd('/')
    }

    private fun tvUrlForServer(serverUrl: String): String {
        val normalized = normalizeServerUrl(serverUrl)
        return if (normalized.isBlank()) "" else "$normalized/tv"
    }

    inner class AndroidBridge {
        @JavascriptInterface
        fun getServerUrl(): String {
            return currentServerUrl.ifBlank { BuildConfig.TV_READER_SERVER_URL }
        }

        @JavascriptInterface
        fun setServerUrl(url: String) {
            runOnUiThread {
                val normalized = normalizeServerUrl(url)
                if (normalized.isNotBlank()) {
                    loadServer(normalized)
                }
            }
        }
    }

    companion object {
        private const val PREF_SERVER_URL = "server_url"
    }
}
