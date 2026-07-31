package com.cocreativeit.reware.squarereader

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.squareup.sdk.mobilepayments.MobilePaymentsSdk
import com.squareup.sdk.mobilepayments.payment.PaymentManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Store-counter companion: poll Odoo pending checkouts and charge via Square Reader.
 *
 * Square Mobile Payments SDK payment APIs evolve by version — after opening in Android Studio,
 * wire PaymentManager.startPaymentActivity / takePayment to the installed SDK version
 * (see https://developer.squareup.com/docs/mobile-payments-sdk/android).
 */
class MainActivity : AppCompatActivity() {

    private lateinit var api: OdooApiClient
    private lateinit var status: TextView
    private lateinit var adapter: CheckoutAdapter
    private var squareConfig: SquareConfig? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val urlInput = findViewById<EditText>(R.id.odooUrl)
        val keyInput = findViewById<EditText>(R.id.apiKey)
        status = findViewById(R.id.status)
        val list = findViewById<RecyclerView>(R.id.list)

        urlInput.setText(getString(R.string.odoo_base_url))
        keyInput.setText(getString(R.string.odoo_api_key))

        api = OdooApiClient(urlInput.text.toString(), keyInput.text.toString())
        adapter = CheckoutAdapter { checkout -> confirmCharge(checkout) }
        list.layoutManager = LinearLayoutManager(this)
        list.adapter = adapter

        findViewById<Button>(R.id.btnRefresh).setOnClickListener {
            api.updateCredentials(urlInput.text.toString(), keyInput.text.toString())
            refresh()
        }
        findViewById<Button>(R.id.btnPair).setOnClickListener {
            // Opens Square settings / pairing UI when available in the linked SDK version.
            try {
                MobilePaymentsSdk.settingsManager().showSettings(this)
                status.text = "Opened Square reader settings"
            } catch (e: Exception) {
                status.text = "Pair Reader: ${e.message}. Use Square settings UI for your SDK version."
            }
        }
    }

    private fun refresh() {
        status.text = "Loading…"
        lifecycleScope.launch {
            try {
                val pending = withContext(Dispatchers.IO) {
                    squareConfig = api.fetchConfig()
                    api.fetchPending()
                }
                adapter.submit(pending)
                status.text = "Pending: ${pending.size}  |  env=${squareConfig?.environment}"
            } catch (e: Exception) {
                status.text = "Error: ${e.message}"
            }
        }
    }

    private fun confirmCharge(checkout: PendingCheckout) {
        AlertDialog.Builder(this)
            .setTitle(checkout.saleOrder)
            .setMessage(
                "Charge ${checkout.amount} ${checkout.currency}\n${checkout.partner}\n\n" +
                    "Customer should tap/insert on the Square Reader."
            )
            .setPositiveButton("Take payment") { _, _ -> takePayment(checkout) }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun takePayment(checkout: PendingCheckout) {
        status.text = "Starting Square payment for ${checkout.name}…"
        val cfg = squareConfig
        if (cfg == null || cfg.accessToken.isBlank() || cfg.locationId.isBlank()) {
            status.text = "Missing Square config from Odoo. Check Application ID / token / location."
            return
        }

        // Authorize SDK (API differs slightly by SDK version — adjust if compile fails).
        try {
            val auth = MobilePaymentsSdk.authorizationManager()
            auth.authorize(cfg.accessToken, cfg.locationId) { result ->
                result.onSuccess {
                    runOnUiThread {
                        // Placeholder: replace with PaymentManager take-payment call for your SDK version.
                        // After SDK returns a payment id, call completeOnOdoo(checkout, paymentId).
                        Toast.makeText(
                            this,
                            "Authorized. Wire PaymentManager.takePayment here (see Square Android docs).",
                            Toast.LENGTH_LONG
                        ).show()
                        status.text =
                            "SDK authorized. Implement takePayment for amount=${checkout.amount} then POST complete."
                    }
                }
                result.onFailure { error ->
                    runOnUiThread {
                        status.text = "Authorize failed: $error"
                    }
                }
            }
        } catch (e: Exception) {
            status.text = "SDK authorize error: ${e.message}"
        }
    }

    private fun completeOnOdoo(checkout: PendingCheckout, squarePaymentId: String) {
        lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) { api.complete(checkout, squarePaymentId) }
                status.text = "Odoo marked paid: ${checkout.saleOrder}"
                refresh()
            } catch (e: Exception) {
                status.text = "Odoo complete failed: ${e.message}"
            }
        }
    }
}

class CheckoutAdapter(
    private val onClick: (PendingCheckout) -> Unit,
) : RecyclerView.Adapter<CheckoutAdapter.VH>() {

    private val items = mutableListOf<PendingCheckout>()

    fun submit(data: List<PendingCheckout>) {
        items.clear()
        items.addAll(data)
        notifyDataSetChanged()
    }

    class VH(val view: TextView) : RecyclerView.ViewHolder(view)

    override fun onCreateViewHolder(parent: android.view.ViewGroup, viewType: Int): VH {
        val tv = TextView(parent.context).apply {
            setPadding(24, 32, 24, 32)
            textSize = 16f
        }
        return VH(tv)
    }

    override fun getItemCount() = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]
        holder.view.text = "${item.saleOrder}  •  ${item.amount} ${item.currency}\n${item.partner}"
        holder.view.setOnClickListener { onClick(item) }
    }
}
