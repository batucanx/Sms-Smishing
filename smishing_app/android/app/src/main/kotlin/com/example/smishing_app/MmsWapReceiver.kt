package com.example.smishing_app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

// Varsayılan SMS uygulaması olabilmek için gerekli - MMS/WAP alıcısı
class MmsWapReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        // Sadece varsayılan SMS gereksinimi için - işlem yapılmıyor
    }
}
