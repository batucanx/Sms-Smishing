package com.example.smishing_app

import android.app.Activity
import android.os.Bundle

// Varsayılan SMS uygulaması olabilmek için gerekli - SMS gönderme aktivitesi
class SendSmsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Bu uygulama SMS göndermez, sadece varsayılan SMS gereksinimini karşılar
        finish()
    }
}
