package com.cocreativeit.reware.squarereader

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

data class PendingCheckout(
    val id: Int,
    val name: String,
    val accessToken: String,
    val amount: Double,
    val currency: String,
    val saleOrder: String,
    val partner: String,
)

data class SquareConfig(
    val environment: String,
    val applicationId: String,
    val accessToken: String,
    val locationId: String,
)

class OdooApiClient(
    private var baseUrl: String,
    private var apiKey: String,
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    fun updateCredentials(baseUrl: String, apiKey: String) {
        this.baseUrl = baseUrl.trimEnd('/')
        this.apiKey = apiKey
    }

    private fun authRequest(path: String): Request.Builder {
        return Request.Builder()
            .url("${baseUrl.trimEnd('/')}$path")
            .header("Authorization", "Bearer $apiKey")
            .header("Accept", "application/json")
    }

    fun fetchConfig(): SquareConfig {
        val response = client.newCall(authRequest("/square/reader/config").get().build()).execute()
        val body = response.body?.string().orEmpty()
        if (!response.isSuccessful) error("Config HTTP ${response.code}: $body")
        val json = JSONObject(body)
        if (!json.optBoolean("ok", false)) error(json.optString("error", "config failed"))
        return SquareConfig(
            environment = json.optString("environment", "sandbox"),
            applicationId = json.optString("application_id"),
            accessToken = json.optString("access_token"),
            locationId = json.optString("location_id"),
        )
    }

    fun fetchPending(): List<PendingCheckout> {
        val response = client.newCall(authRequest("/square/reader/pending").get().build()).execute()
        val body = response.body?.string().orEmpty()
        if (!response.isSuccessful) error("Pending HTTP ${response.code}: $body")
        val json = JSONObject(body)
        if (!json.optBoolean("ok", false)) error(json.optString("error", "pending failed"))
        val arr: JSONArray = json.optJSONArray("checkouts") ?: JSONArray()
        val out = mutableListOf<PendingCheckout>()
        for (i in 0 until arr.length()) {
            val row = arr.getJSONObject(i)
            out.add(
                PendingCheckout(
                    id = row.getInt("id"),
                    name = row.getString("name"),
                    accessToken = row.getString("access_token"),
                    amount = row.getDouble("amount"),
                    currency = row.getString("currency"),
                    saleOrder = row.getString("sale_order"),
                    partner = row.optString("partner"),
                )
            )
        }
        return out
    }

    fun complete(checkout: PendingCheckout, squarePaymentId: String) {
        val payload = JSONObject()
            .put("checkout_id", checkout.id)
            .put("access_token", checkout.accessToken)
            .put("square_payment_id", squarePaymentId)
            .toString()
        val body = payload.toRequestBody("application/json; charset=utf-8".toMediaType())
        val response = client.newCall(
            authRequest("/square/reader/complete").post(body).build()
        ).execute()
        val text = response.body?.string().orEmpty()
        if (!response.isSuccessful) error("Complete HTTP ${response.code}: $text")
        val json = JSONObject(text)
        if (!json.optBoolean("ok", false)) error(json.optString("error", "complete failed"))
    }

    fun fail(checkout: PendingCheckout, message: String) {
        val payload = JSONObject()
            .put("checkout_id", checkout.id)
            .put("access_token", checkout.accessToken)
            .put("message", message)
            .toString()
        val body = payload.toRequestBody("application/json; charset=utf-8".toMediaType())
        client.newCall(authRequest("/square/reader/fail").post(body).build()).execute().close()
    }
}
