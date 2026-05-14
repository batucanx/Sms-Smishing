package com.example.smishing_app

import android.app.Service
import android.content.Intent
import android.os.IBinder

// Varsayılan SMS uygulaması olabilmek için gerekli - mesajla yanıtla servisi
class SmsReplyService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        stopSelf()
        return START_NOT_STICKY
    }
}
