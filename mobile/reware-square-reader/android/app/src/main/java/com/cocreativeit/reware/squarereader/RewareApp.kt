package com.cocreativeit.reware.squarereader

import android.app.Application
import android.util.Log
import com.squareup.sdk.mobilepayments.MobilePaymentsSdk

class RewareApp : Application() {
    override fun onCreate() {
        super.onCreate()
        val appId = getString(R.string.square_application_id)
        if (appId.isNotBlank()) {
            try {
                MobilePaymentsSdk.initialize(appId, this)
            } catch (e: Exception) {
                Log.e("RewareApp", "Square SDK init failed", e)
            }
        }
    }
}
