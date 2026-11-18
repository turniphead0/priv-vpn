package com.kardesler.vpn

import android.content.Context
import android.content.Intent
import android.graphics.Typeface
import android.net.VpnService
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.wireguard.android.backend.GoBackend
import com.wireguard.android.backend.Tunnel
import com.wireguard.config.Config
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import org.json.JSONObject
import java.io.BufferedReader
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    private val io = Executors.newSingleThreadExecutor()
    private val prefs by lazy { getSharedPreferences("vpn", Context.MODE_PRIVATE) }
    private val backend by lazy { App.backend(this) }

    private lateinit var status: TextView
    private lateinit var toggle: Button
    private lateinit var setup: LinearLayout
    private lateinit var server: EditText
    private lateinit var code: EditText
    private lateinit var device: EditText
    private lateinit var paste: EditText
    private lateinit var invite: LinearLayout

    private val scanner = registerForActivityResult(ScanContract()) { r ->
        r.contents?.let { saveConfig(it) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val pad = (16 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(pad, pad * 2, pad, pad) }

        root.addView(TextView(this).apply {
            text = getString(R.string.app_name); textSize = 26f; setTypeface(typeface, Typeface.BOLD); gravity = Gravity.CENTER
        })
        status = TextView(this).apply { textSize = 18f; gravity = Gravity.CENTER; setPadding(0, pad, 0, pad) }
        root.addView(status)
        toggle = Button(this).apply { textSize = 20f; setOnClickListener { onToggle() } }
        root.addView(toggle)

        setup = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(0, pad * 2, 0, 0) }
        setup.addView(TextView(this).apply { text = "Cihazı kaydet"; textSize = 18f; setTypeface(typeface, Typeface.BOLD) })
        setup.addView(Button(this).apply {
            text = "QR kodu tara"; textSize = 18f
            setOnClickListener {
                scanner.launch(ScanOptions().setDesiredBarcodeFormats(ScanOptions.QR_CODE)
                    .setPrompt("Sunucudaki QR kodu okutun").setBeepEnabled(false).setOrientationLocked(false))
            }
        })
        setup.addView(TextView(this).apply { text = "\nveya WireGuard ayarını yapıştır:" })
        paste = field("[Interface] ...", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE).apply { minLines = 3 }
        setup.addView(paste)
        setup.addView(Button(this).apply { text = "Ayarı kaydet"; setOnClickListener { saveConfig(paste.text.toString()) } })

        invite = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; visibility = LinearLayout.GONE }
        server = field("Sunucu adresi (https://...)", InputType.TYPE_TEXT_VARIATION_URI)
        code = field("Davet kodu", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        device = field("Cihaz adı (ör. telefon)", InputType.TYPE_CLASS_TEXT)
        server.setText(prefs.getString("server", ""))
        invite.addView(server); invite.addView(code); invite.addView(device)
        invite.addView(Button(this).apply { text = "Kaydol"; setOnClickListener { register() } })
        setup.addView(TextView(this).apply {
            text = "\nDavet kodum var ›"; setPadding(0, pad, 0, 0)
            setOnClickListener { invite.visibility = if (invite.visibility == LinearLayout.GONE) LinearLayout.VISIBLE else LinearLayout.GONE }
        })
        setup.addView(invite)
        root.addView(setup)

        root.addView(Button(this).apply {
            text = "Cihaz kaydını sıfırla"; setOnClickListener { reset() }
        })
        setContentView(ScrollView(this).apply { addView(root) })
        refresh()
    }

    private fun field(hint: String, type: Int) = EditText(this).apply {
        this.hint = hint; inputType = type
    }

    private fun refresh() {
        val hasConfig = prefs.getString("config", null) != null
        val up = hasConfig && backend.getState(App.tunnel) == Tunnel.State.UP
        status.text = when {
            !hasConfig -> "Cihaz kayıtlı değil"
            up -> "Bağlı ✓"
            else -> "Bağlı değil"
        }
        toggle.text = if (up) "Bağlantıyı kes" else "Bağlan"
        toggle.isEnabled = hasConfig
        setup.visibility = if (hasConfig) LinearLayout.GONE else LinearLayout.VISIBLE
    }

    private fun onToggle() {
        val up = backend.getState(App.tunnel) == Tunnel.State.UP
        if (!up) {
            val intent = VpnService.prepare(this)
            if (intent != null) { startActivityForResult(intent, REQ_VPN); return }
        }
        setState(!up)
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_VPN && resultCode == RESULT_OK) setState(true)
    }

    private fun setState(up: Boolean) {
        val text = prefs.getString("config", null) ?: return
        toggle.isEnabled = false
        status.text = if (up) "Bağlanıyor..." else "Kesiliyor..."
        io.execute {
            val err = runCatching {
                val cfg = Config.parse(text.byteInputStream())
                backend.setState(App.tunnel, if (up) Tunnel.State.UP else Tunnel.State.DOWN, cfg)
            }.exceptionOrNull()
            runOnUiThread {
                refresh()
                if (err != null) status.text = "Hata: ${err.message ?: err.javaClass.simpleName}"
            }
        }
    }

    private fun register() {
        val base = server.text.toString().trim().trimEnd('/')
        val body = JSONObject().put("kod", code.text.toString().trim()).put("cihaz", device.text.toString().trim().lowercase())
        if (!base.startsWith("https://")) { status.text = "Sunucu adresi https:// ile başlamalı"; return }
        prefs.edit().putString("server", base).apply()
        status.text = "Kaydediliyor..."
        io.execute {
            val result = runCatching {
                val c = URL("$base/api/cihaz").openConnection() as HttpURLConnection
                c.requestMethod = "POST"; c.doOutput = true; c.connectTimeout = 10000; c.readTimeout = 20000
                c.setRequestProperty("Content-Type", "application/json")
                c.outputStream.use { it.write(body.toString().toByteArray()) }
                val stream = if (c.responseCode in 200..299) c.inputStream else c.errorStream
                val json = JSONObject(stream.bufferedReader().use(BufferedReader::readText))
                if (c.responseCode !in 200..299) error(json.optString("hata", "HTTP ${c.responseCode}"))
                json.getString("config")
            }
            runOnUiThread {
                result.onSuccess { saveConfig(it) }
                    .onFailure { status.text = "Kayıt başarısız: ${it.message}" }
            }
        }
    }

    private fun saveConfig(raw: String) {
        val text = raw.trim() + "\n"
        val ok = runCatching { Config.parse(text.byteInputStream()) }
        if (ok.isFailure) { status.text = "Ayar geçersiz: ${ok.exceptionOrNull()?.message}"; return }
        prefs.edit().putString("config", text).apply()
        paste.setText("")
        refresh()
    }

    private fun reset() {
        io.execute {
            runCatching { backend.setState(App.tunnel, Tunnel.State.DOWN, null) }
            runOnUiThread { prefs.edit().remove("config").apply(); refresh() }
        }
    }

    companion object { private const val REQ_VPN = 1 }
}

object App {
    val tunnel = object : Tunnel {
        override fun getName() = "kardesler"
        override fun onStateChange(newState: Tunnel.State) {}
    }
    @Volatile private var b: GoBackend? = null
    fun backend(ctx: Context): GoBackend = b ?: synchronized(this) { b ?: GoBackend(ctx.applicationContext).also { b = it } }
}
