package com.example.smishing_app

import android.content.ContentValues
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.BlockedNumberContract
import android.provider.MediaStore
import android.provider.Telephony
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.FileOutputStream

class MainActivity : FlutterActivity() {

    private val CHANNEL = "com.smishing_app/file_export"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {

                // Uygulamanın varsayılan SMS uygulaması olup olmadığını kontrol et
                "isDefaultSmsApp" -> {
                    try {
                        val isDefault = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                            val roleManager = getSystemService(android.app.role.RoleManager::class.java)
                            roleManager?.isRoleHeld(android.app.role.RoleManager.ROLE_SMS) == true
                        } else {
                            val defaultApp = Telephony.Sms.getDefaultSmsPackage(this)
                            packageName == defaultApp
                        }
                        result.success(isDefault)
                    } catch (e: Throwable) {
                        result.success(false)
                    }
                }

                // Varsayılan SMS uygulaması yapma diyaloğunu aç
                "requestDefaultSmsApp" -> {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        val roleManager = getSystemService(android.app.role.RoleManager::class.java)
                        if (roleManager?.isRoleAvailable(android.app.role.RoleManager.ROLE_SMS) == true) {
                            val intent = roleManager.createRequestRoleIntent(android.app.role.RoleManager.ROLE_SMS)
                            startActivityForResult(intent, 101)
                        }
                    } else {
                        val intent = Intent(Telephony.Sms.Intents.ACTION_CHANGE_DEFAULT)
                        intent.putExtra(Telephony.Sms.Intents.EXTRA_PACKAGE_NAME, packageName)
                        startActivity(intent)
                    }
                    result.success(null)
                }

                // Soru sormadan doğrudan varsayılan uygulamaları listeleyen ekranı aç
                "openDefaultSmsSettings" -> {
                    try {
                        val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                            Intent(android.provider.Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS)
                        } else {
                            Intent(android.provider.Settings.ACTION_SETTINGS)
                        }
                        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
                        startActivity(intent)
                    } catch (e: Exception) {
                        val fallbackIntent = Intent(android.provider.Settings.ACTION_SETTINGS)
                        fallbackIntent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
                        startActivity(fallbackIntent)
                    }
                    result.success(null)
                }

                // Numaraları BlockedNumberContract ile engelle
                "blockNumbers" -> {
                    val numbers = call.argument<List<String>>("numbers") ?: emptyList()
                    var successCount = 0
                    var failCount = 0

                    for (number in numbers) {
                        try {
                            val values = ContentValues().apply {
                                put(BlockedNumberContract.BlockedNumbers.COLUMN_ORIGINAL_NUMBER, number)
                            }
                            val uri = contentResolver.insert(
                                BlockedNumberContract.BlockedNumbers.CONTENT_URI,
                                values
                            )
                            if (uri != null) successCount++ else failCount++
                        } catch (e: SecurityException) {
                            failCount++
                        } catch (e: Throwable) {
                            failCount++
                        }
                    }

                    result.success(mapOf("success" to successCount, "fail" to failCount))
                }

                // Numaraların engelini kaldır (Gelen kutusuna geri döner)
                "unblockNumbers" -> {
                    val numbers = call.argument<List<String>>("numbers") ?: emptyList()
                    var successCount = 0
                    for (number in numbers) {
                        try {
                            val deleted = contentResolver.delete(
                                BlockedNumberContract.BlockedNumbers.CONTENT_URI,
                                "${BlockedNumberContract.BlockedNumbers.COLUMN_ORIGINAL_NUMBER} = ?",
                                arrayOf(number)
                            )
                            if (deleted > 0) successCount++
                        } catch (e: Exception) {}
                    }
                    result.success(successCount)
                }

                // Engellenen numaraların listesini getir
                "getBlockedNumbers" -> {
                    val blockedList = mutableListOf<String>()
                    try {
                        val cursor = contentResolver.query(
                            BlockedNumberContract.BlockedNumbers.CONTENT_URI,
                            arrayOf(BlockedNumberContract.BlockedNumbers.COLUMN_ORIGINAL_NUMBER),
                            null, null, null
                        )
                        cursor?.use {
                            val colIndex = it.getColumnIndex(BlockedNumberContract.BlockedNumbers.COLUMN_ORIGINAL_NUMBER)
                            if (colIndex != -1) {
                                while (it.moveToNext()) {
                                    blockedList.add(it.getString(colIndex))
                                }
                            }
                        }
                    } catch (e: Exception) {}
                    result.success(blockedList)
                }

                // Sistemin (Google/Samsung) Spam Klasöründeki Mesajları Getir
                "getSystemSpamMessages" -> {
                    val spamList = mutableListOf<Map<String, Any>>()
                    val seenIds = mutableSetOf<Int>()
                    
                    // ── Strateji 1 & 4 Birleşik: Gizli mesajlar ve filtreli mesajlar ──
                    try {
                        val uri = Uri.parse("content://sms")
                        // block_filtered_status != 0 olanlar veya standart dısı (type > 6 vb.) olanlar
                        val selection = "block_filtered_status != 0 OR type NOT IN (1, 2, 3, 4, 5, 6)"
                        
                        
                        val cursor = contentResolver.query(
                            uri,
                            arrayOf("_id", "address", "body", "date", "type", "block_filtered_status"),
                            selection,
                            null,
                            "date DESC"
                        )
                        cursor?.use {
                            val idIdx = it.getColumnIndex("_id")
                            val addrIdx = it.getColumnIndex("address")
                            val bodyIdx = it.getColumnIndex("body")
                            val dateIdx = it.getColumnIndex("date")
                            val typeIdx = it.getColumnIndex("type")
                            val filterIdx = it.getColumnIndex("block_filtered_status")
                            
                            while (it.moveToNext()) {
                                val id = if (idIdx != -1) it.getInt(idIdx) else continue
                                if (seenIds.contains(id)) continue
                                seenIds.add(id)
                                val map = mutableMapOf<String, Any>()
                                map["id"] = id
                                if (addrIdx != -1) map["address"] = it.getString(addrIdx) ?: ""
                                if (bodyIdx != -1) map["body"] = it.getString(bodyIdx) ?: ""
                                if (dateIdx != -1) map["date"] = it.getLong(dateIdx)
                                if (typeIdx != -1) map["type"] = it.getInt(typeIdx)
                                if (filterIdx != -1) map["filter_status"] = it.getInt(filterIdx)
                                map["source"] = "system_filter"
                                spamList.add(map)
                            }
                        }
                    } catch (e: Exception) {}
                    
                    // ── Strateji 2: Engellenen numaralardan gelen mesajları bul ──
                    try {
                        // Engellenen numaraları al
                        val blockedNumbers = mutableListOf<String>()
                        val blockedCursor = contentResolver.query(
                            BlockedNumberContract.BlockedNumbers.CONTENT_URI,
                            arrayOf(BlockedNumberContract.BlockedNumbers.COLUMN_ORIGINAL_NUMBER),
                            null, null, null
                        )
                        blockedCursor?.use {
                            val colIndex = it.getColumnIndex(BlockedNumberContract.BlockedNumbers.COLUMN_ORIGINAL_NUMBER)
                            if (colIndex != -1) {
                                while (it.moveToNext()) {
                                    blockedNumbers.add(it.getString(colIndex))
                                }
                            }
                        }
                        
                        // Engellenen numaralardan gelen inbox mesajlarını da ekle
                        if (blockedNumbers.isNotEmpty()) {
                            for (blockedNum in blockedNumbers) {
                                val cursor = contentResolver.query(
                                    Uri.parse("content://sms"),
                                    arrayOf("_id", "address", "body", "date", "type"),
                                    "address = ?",
                                    arrayOf(blockedNum),
                                    "date DESC"
                                )
                                cursor?.use {
                                    val idIdx = it.getColumnIndex("_id")
                                    val addrIdx = it.getColumnIndex("address")
                                    val bodyIdx = it.getColumnIndex("body")
                                    val dateIdx = it.getColumnIndex("date")
                                    val typeIdx = it.getColumnIndex("type")
                                    
                                    while (it.moveToNext()) {
                                        val id = if (idIdx != -1) it.getInt(idIdx) else continue
                                        if (seenIds.contains(id)) continue
                                        seenIds.add(id)
                                        val map = mutableMapOf<String, Any>()
                                        map["id"] = id
                                        if (addrIdx != -1) map["address"] = it.getString(addrIdx) ?: ""
                                        if (bodyIdx != -1) map["body"] = it.getString(bodyIdx) ?: ""
                                        if (dateIdx != -1) map["date"] = it.getLong(dateIdx)
                                        if (typeIdx != -1) map["type"] = it.getInt(typeIdx)
                                        map["source"] = "blocked"
                                        spamList.add(map)
                                    }
                                }
                            }
                        }
                    } catch (e: Exception) {}
                    
                    // ── Strateji 3 ve 4 kaldırıldı çünkü spam olmayan mesajları da getiriyordu ──
                    
                    result.success(spamList)
                }

                // Debug: Kapsamlı SMS veritabanı analizi (String olarak döner)
                "debugSmsTypes" -> {
                    val sb = StringBuilder()
                    
                    // 1. Varsayılan SMS uygulaması bilgisi
                    try {
                        val defaultApp = Telephony.Sms.getDefaultSmsPackage(this@MainActivity) ?: "null"
                        sb.appendLine("=== UYGULAMA BİLGİSİ ===")
                        sb.appendLine("Varsayılan SMS: $defaultApp")
                        sb.appendLine("Bizim paket: $packageName")
                        sb.appendLine("Eslesme: ${if (defaultApp == packageName) "EVET" else "HAYIR"}")
                    } catch (e: Exception) {
                        sb.appendLine("Uygulama bilgisi alinamadi: ${e.message}")
                    }
                    
                    // 2. Tüm SMS tipleri
                    sb.appendLine("")
                    sb.appendLine("=== MESAJ TIPLERI ===")
                    try {
                        val cursor = contentResolver.query(
                            Uri.parse("content://sms"),
                            null, null, null, null
                        )
                        cursor?.use {
                            sb.appendLine("Toplam: ${it.count} mesaj")
                            sb.appendLine("Sutunlar: ${it.columnNames.joinToString(", ")}")
                            
                            val typeIdx = it.getColumnIndex("type")
                            val typeMap = mutableMapOf<Int, Int>()
                            if (typeIdx != -1) {
                                while (it.moveToNext()) {
                                    val type = it.getInt(typeIdx)
                                    typeMap[type] = (typeMap[type] ?: 0) + 1
                                }
                            }
                            val typeNames = mapOf(1 to "Inbox", 2 to "Sent", 3 to "Draft", 4 to "Outbox", 5 to "Failed", 6 to "Queued")
                            typeMap.forEach { (type, count) ->
                                sb.appendLine("  Type $type (${typeNames[type] ?: "?"}): $count")
                            }
                        } ?: sb.appendLine("Cursor null!")
                    } catch (e: Exception) {
                        sb.appendLine("HATA: ${e.message}")
                    }
                    
                    // 3. Farklı URI'leri dene
                    sb.appendLine("")
                    sb.appendLine("=== URI SONUCLARI ===")
                    val urisToTry = listOf(
                        "content://sms/inbox", "content://sms/sent", "content://sms/draft",
                        "content://sms/outbox", "content://sms/failed", "content://sms/queued",
                        "content://sms/spam", "content://sms/undelivered",
                        "content://mms-sms/conversations", "content://mms", "content://mms/inbox"
                    )
                    for (uriStr in urisToTry) {
                        try {
                            val cursor = contentResolver.query(Uri.parse(uriStr), arrayOf("_id"), null, null, null)
                            val count = cursor?.count ?: -1
                            cursor?.close()
                            sb.appendLine("  ${uriStr.removePrefix("content://")}: $count")
                        } catch (e: Exception) {
                            sb.appendLine("  ${uriStr.removePrefix("content://")}: HATA")
                        }
                    }
                    
                    // 4. Google Messages content provider
                    sb.appendLine("")
                    sb.appendLine("=== GOOGLE MESSAGES ===")
                    val googleUris = listOf(
                        "content://com.google.android.apps.messaging/conversations",
                        "content://com.google.android.apps.messaging/messages"
                    )
                    for (uriStr in googleUris) {
                        try {
                            val cursor = contentResolver.query(Uri.parse(uriStr), null, null, null, null)
                            if (cursor != null) {
                                sb.appendLine("  ${uriStr.substringAfterLast("/")}: ${cursor.count} satir")
                                sb.appendLine("    Sutunlar: ${cursor.columnNames.take(8).joinToString(", ")}")
                                cursor.close()
                            } else {
                                sb.appendLine("  ${uriStr.substringAfterLast("/")}: null")
                            }
                        } catch (e: SecurityException) {
                            sb.appendLine("  ${uriStr.substringAfterLast("/")}: ERISIM REDDI")
                        } catch (e: Exception) {
                            sb.appendLine("  ${uriStr.substringAfterLast("/")}: ${e.javaClass.simpleName}")
                        }
                    }
                    
                    // 5. Bilinen spam göndericileri ara
                    sb.appendLine("")
                    sb.appendLine("=== SPAM GONDERICI ARAMA ===")
                    val spamSenders = listOf("LCWCOM", "LONEX YAZLM", ".LONEX2.", "GigData LTD", "MADPARFMEUR", "0850 452 4529")
                    for (sender in spamSenders) {
                        try {
                            val cursor = contentResolver.query(
                                Uri.parse("content://sms"),
                                arrayOf("_id", "address", "type"),
                                "address LIKE ?",
                                arrayOf("%$sender%"),
                                null
                            )
                            cursor?.use {
                                if (it.count > 0) {
                                    val types = mutableListOf<Int>()
                                    val typeIdx = it.getColumnIndex("type")
                                    while (it.moveToNext()) {
                                        if (typeIdx != -1) types.add(it.getInt(typeIdx))
                                    }
                                    sb.appendLine("  $sender: ${it.count} mesaj, tipler=$types")
                                } else {
                                    sb.appendLine("  $sender: BULUNAMADI")
                                }
                            }
                        } catch (e: Exception) {
                            sb.appendLine("  $sender: HATA")
                        }
                    }
                    
                    // 6. Engellenen numara sayısı
                    sb.appendLine("")
                    sb.appendLine("=== ENGELLENEN NUMARALAR ===")
                    try {
                        val cursor = contentResolver.query(
                            BlockedNumberContract.BlockedNumbers.CONTENT_URI,
                            arrayOf(BlockedNumberContract.BlockedNumbers.COLUMN_ORIGINAL_NUMBER),
                            null, null, null
                        )
                        cursor?.use {
                            sb.appendLine("Toplam: ${it.count} engellenen numara")
                            while (it.moveToNext()) {
                                sb.appendLine("  - ${it.getString(0)}")
                            }
                        }
                    } catch (e: Exception) {
                        sb.appendLine("HATA: ${e.message}")
                    }
                    
                    result.success(sb.toString())
                }

                "moveToInbox" -> {
                    val messageId = call.argument<Int>("messageId")
                    val address = call.argument<String>("address")
                    var success = false
                    
                    if (messageId != null) {
                        try {
                            // 1. Önce mesajı bulalım (Selection kullanarak daha güvenli arama)
                            val cursor = contentResolver.query(
                                Uri.parse("content://sms"),
                                arrayOf("_id", "address", "body", "date", "type"),
                                "_id = ?",
                                arrayOf(messageId.toString()),
                                null
                            )
                            
                            var addr = ""
                            var body = ""
                            var date = System.currentTimeMillis()
                            var found = false

                            cursor?.use {
                                if (it.moveToFirst()) {
                                    val addrIdx = it.getColumnIndex("address")
                                    val bodyIdx = it.getColumnIndex("body")
                                    val dateIdx = it.getColumnIndex("date")
                                    if (addrIdx != -1) addr = it.getString(addrIdx) ?: ""
                                    if (bodyIdx != -1) body = it.getString(bodyIdx) ?: ""
                                    if (dateIdx != -1) date = it.getLong(dateIdx)
                                    found = true
                                }
                            }

                            if (found) {
                                // 2. YÖNTEM A: Mevcut mesajı güncellemeyi dene (En hızlı yöntem)
                                try {
                                    val updateValues = ContentValues().apply {
                                        put("type", 1) // Inbox
                                        put("read", 1)
                                        put("seen", 1)
                                        try { put("block_filtered_status", 0) } catch (e: Exception) {}
                                        try { put("is_spam", 0) } catch (e: Exception) {}
                                    }
                                    val updated = contentResolver.update(
                                        Uri.parse("content://sms/$messageId"), 
                                        updateValues, null, null
                                    )
                                    if (updated > 0) success = true
                                } catch (e: Exception) {
                                    android.util.Log.e("SMS_MOVE", "Update failed: ${e.message}")
                                }

                                // 3. YÖNTEM B: Eğer güncelleme başarısızsa veya Google inat ediyorsa, sil-ekle yap
                                if (!success) {
                                    try {
                                        // Engel varsa kaldır
                                        if (address != null && address.isNotEmpty()) {
                                            contentResolver.delete(BlockedNumberContract.BlockedNumbers.CONTENT_URI, "${BlockedNumberContract.BlockedNumbers.COLUMN_ORIGINAL_NUMBER} = ?", arrayOf(address))
                                        }
                                        
                                        // Sil ve Gelen Kutusu'na tertemiz ekle
                                        contentResolver.delete(Uri.parse("content://sms/$messageId"), null, null)
                                        val newValues = ContentValues().apply {
                                            put("address", addr)
                                            put("body", body)
                                            put("date", date)
                                            put("type", 1)
                                            put("read", 1)
                                            put("seen", 1)
                                            try { put("block_filtered_status", 0) } catch (e: Exception) {}
                                        }
                                        val newUri = contentResolver.insert(Uri.parse("content://sms/inbox"), newValues)
                                        if (newUri != null) success = true
                                    } catch (e: Exception) {
                                        android.util.Log.e("SMS_MOVE", "Insert failed: ${e.message}")
                                    }
                                }
                            } else {
                                android.util.Log.e("SMS_MOVE", "Message $messageId not found in content://sms")
                            }
                        } catch (e: Exception) {
                            android.util.Log.e("SMS_MOVE", "Force re-insert failed: ${e.message}")
                        }
                    }
                    result.success(success)
                }

                // Spam mesajlarını sil (sadece default SMS app iken çalışır)
                "deleteMessages" -> {
                    val messageIds = call.argument<List<Int>>("messageIds") ?: emptyList()
                    var deletedCount = 0
                    for (id in messageIds) {
                        try {
                            val uri = Uri.parse("content://sms/$id")
                            val deleted = contentResolver.delete(uri, null, null)
                            if (deleted > 0) deletedCount++
                        } catch (e: Exception) {}
                    }
                    result.success(deletedCount)
                }

                // Spam numaralarını dosyaya kaydet (yedek yöntem)
                "exportSpamNumbers" -> {
                    val numbers = call.argument<List<String>>("numbers") ?: emptyList()
                    val fileName = "spam_engel_listesi.txt"
                    val content = numbers.joinToString("\n")

                    try {
                        val filePath: String

                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                            val values = ContentValues().apply {
                                put(MediaStore.Downloads.DISPLAY_NAME, fileName)
                                put(MediaStore.Downloads.MIME_TYPE, "text/plain")
                                put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                            }
                            val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                            if (uri != null) {
                                contentResolver.openOutputStream(uri)?.use { it.write(content.toByteArray()) }
                                filePath = "İndirilenler/$fileName"
                            } else {
                                result.error("FILE_ERROR", "Dosya oluşturulamadı", null)
                                return@setMethodCallHandler
                            }
                        } else {
                            val dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                            val file = java.io.File(dir, fileName)
                            FileOutputStream(file).use { it.write(content.toByteArray()) }
                            filePath = file.absolutePath
                        }

                        result.success(filePath)
                    } catch (e: Exception) {
                        result.error("FILE_ERROR", e.message, null)
                    }
                }

                else -> result.notImplemented()
            }
        }
    }
}
