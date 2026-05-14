import 'dart:convert';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart';
import 'package:flutter_sms_inbox/flutter_sms_inbox.dart';
import 'dart:async';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  const AndroidInitializationSettings initializationSettingsAndroid = AndroidInitializationSettings('@mipmap/launcher_icon');
  const InitializationSettings initializationSettings = InitializationSettings(android: initializationSettingsAndroid);
  await flutterLocalNotificationsPlugin.initialize(settings: initializationSettings);

  runApp(const SmishingApp());
}

class SmishingApp extends StatelessWidget {
  const SmishingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SMS Security',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: Colors.transparent,
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFFFFFFF),
          secondary: Color(0xFFE5E5E5),
        ),
        textTheme: GoogleFonts.oswaldTextTheme(ThemeData.dark().textTheme),
        useMaterial3: true,
      ),
      home: const SplashScreen(),
    );
  }
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(milliseconds: 5500), () {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (context) => const HomeScreen()),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: FractionallySizedBox(
          widthFactor: 0.8,
          child: Image.asset(
            'assets/logo.gif',
            fit: BoxFit.contain,
          ),
        ),
      ),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _ipController = TextEditingController(text: "192.168.1.X");
  final TextEditingController _manualSmsController = TextEditingController();
  final TextEditingController _manualSenderController = TextEditingController();

  List<SmsMessage> _inboxMessages = [];
  // originalIndex -> prediction result
  Map<int, Map<String, dynamic>> _predictions = {};
  bool _isLoadingInbox = false;
  bool _isPredictingManual = false;
  bool _isScanning = false;
  int _scanProgress = 0;
  bool _isDefaultSmsApp = false;
  Map<String, dynamic>? _manualPredictionResult;
  List<String> _blockedNumbers = [];
  List<Map<String, dynamic>> _systemSpamMessages = [];
  Map<int, Map<String, dynamic>> _systemSpamPredictions = {};

  final SmsQuery query = SmsQuery();
  static const _platform = MethodChannel('com.smishing_app/file_export');

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 5, vsync: this);
    _requestPermissions();
    _checkDefaultSmsApp();
    _scheduleReminder();
  }

  Future<void> _scheduleReminder() async {
    final status = await Permission.notification.request();
    if (status.isGranted) {
      const AndroidNotificationDetails androidPlatformChannelSpecifics = AndroidNotificationDetails(
        'reminder_channel',
        'Tarama Hatırlatıcı',
        channelDescription: 'Haftalık tarama hatırlatmaları yapar',
        importance: Importance.max,
        priority: Priority.high,
      );
      const NotificationDetails platformChannelSpecifics = NotificationDetails(android: androidPlatformChannelSpecifics);

      await flutterLocalNotificationsPlugin.periodicallyShow(
        id: 0,
        title: 'Tarama Vakti Geldi!',
        body: 'Zararlı mesajlarınız birikmiş olabilir. Tarama yapmak ister misiniz?',
        repeatInterval: RepeatInterval.weekly,
        notificationDetails: platformChannelSpecifics,
        androidScheduleMode: AndroidScheduleMode.inexact,
      );
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _ipController.dispose();
    _manualSmsController.dispose();
    _manualSenderController.dispose();
    super.dispose();
  }

  Future<void> _requestPermissions() async {
    final status = await Permission.sms.request();
    if (status.isGranted) {
      // İzin verildikten sonra eğer varsayılan SMS uygulaması değilsek soralım
      final isDefault = await _platform.invokeMethod<bool>('isDefaultSmsApp') ?? false;
      if (!isDefault) {
        await _requestDefaultSmsApp();
      }
      _loadInbox();
    }
  }

  Future<void> _checkDefaultSmsApp() async {
    try {
      final isDefault = await _platform.invokeMethod<bool>('isDefaultSmsApp') ?? false;
      if (mounted) setState(() => _isDefaultSmsApp = isDefault);
    } catch (_) {}
  }

  Future<void> _requestDefaultSmsApp() async {
    await _platform.invokeMethod('requestDefaultSmsApp');
    // Kullanıcı diyaloğu kapattıktan sonra tekrar kontrol et
    await Future.delayed(const Duration(seconds: 2));
    await _checkDefaultSmsApp();
  }

  Future<void> _loadBlockedNumbers() async {
    try {
      final List<dynamic>? result = await _platform.invokeMethod('getBlockedNumbers');
      if (result != null && mounted) {
        setState(() {
          _blockedNumbers = result.cast<String>();
        });
      }
    } catch (e) {
      debugPrint("Engellenen numaralar alınamadı: \$e");
    }
  }

  Future<void> _loadSystemSpam() async {
    try {
      final List<dynamic>? result = await _platform.invokeMethod('getSystemSpamMessages');
      if (result != null && mounted) {
        setState(() {
          _systemSpamMessages = result.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        });
        debugPrint("Google Spam: ${_systemSpamMessages.length} mesaj bulundu");
      }
    } catch (e) {
      debugPrint("Sistem spam mesajları alınamadı: \$e");
    }
  }
  Future<void> _debugSmsTypes() async {
    try {
      final String? result = await _platform.invokeMethod<String>('debugSmsTypes');
      if (result != null && mounted) {
        debugPrint(result);
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1C1C1E),
            title: Text('SMS Debug', style: GoogleFonts.oswald(color: Colors.white)),
            content: SizedBox(
              width: double.maxFinite,
              child: SingleChildScrollView(
                child: SelectableText(
                  result,
                  style: const TextStyle(color: Colors.white70, fontSize: 11, fontFamily: 'monospace'),
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Kapat', style: TextStyle(color: Color(0xFFFFFFFF))),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      debugPrint("Debug hatasi: $e");
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Debug hatasi: $e'), backgroundColor: Colors.redAccent),
        );
      }
    }
  }

  Future<void> _moveToInbox(int messageId, String address) async {
    try {
      final isDefault = await _platform.invokeMethod<bool>('isDefaultSmsApp') ?? false;
      if (!isDefault) {
        _showDefaultSmsRequiredDialog(1); // Varsayılan SMS uygulaması olmasını iste
        return;
      }
      
      final bool success = await _platform.invokeMethod('moveToInbox', {
        'messageId': messageId,
        'address': address,
      }) ?? false;
      if (success) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('$address mesajı Gelen Kutusuna taşındı!'),
              backgroundColor: Colors.green.shade700,
            ),
          );
        }
        await _loadSystemSpam();
        await _loadBlockedNumbers();
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Taşıma başarısız oldu.'), backgroundColor: Colors.redAccent),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Hata: \$e'), backgroundColor: Colors.redAccent),
        );
      }
    }
  }

  Future<void> _loadInbox() async {
    setState(() => _isLoadingInbox = true);
    await _loadBlockedNumbers();
    await _loadSystemSpam();
    try {
      List<SmsMessage> messages = await query.querySms(
        kinds: [SmsQueryKind.inbox],
      );
      setState(() {
        _inboxMessages = messages;
        _predictions = {};
        _isLoadingInbox = false;
      });
    } catch (e) {
      setState(() => _isLoadingInbox = false);
    }
  }

  Future<Map<String, dynamic>?> checkSmsWithApi(String message, String sender) async {
    String ip = _ipController.text.trim();
    if (ip.isEmpty || ip.contains('X')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Lütfen geçerli bir API IP adresi girin!')),
      );
      return null;
    }

    // Sonda '/' varsa kaldır
    if (ip.endsWith('/')) {
      ip = ip.substring(0, ip.length - 1);
    }

    try {
      String urlString;
      if (ip.startsWith('http')) {
        urlString = '$ip/predict'; // Örn: https://smishing.onrender.com/predict
      } else if (ip.contains('onrender.com')) {
        urlString = 'https://$ip/predict'; // Kullanıcı sadece linki yapıştırırsa
      } else {
        urlString = 'http://$ip:8000/predict'; // Eskisi gibi lokal testler için
      }

      final response = await http.post(
        Uri.parse(urlString),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'message': message, 'sender': sender}),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('API Hatası: \${response.statusCode}')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Bağlantı Hatası: \$e')),
        );
      }
    }
    return null;
  }

  Future<List<dynamic>?> checkBulkSmsWithApi(List<Map<String, String>> messages) async {
    String ip = _ipController.text.trim();
    if (ip.isEmpty || ip.contains('X')) return null;

    // Sonda '/' varsa kaldır
    if (ip.endsWith('/')) {
      ip = ip.substring(0, ip.length - 1);
    }

    try {
      String urlString;
      if (ip.startsWith('http')) {
        urlString = '$ip/predict_bulk';
      } else if (ip.contains('onrender.com')) {
        urlString = 'https://$ip/predict_bulk';
      } else {
        urlString = 'http://$ip:8000/predict_bulk';
      }

      final response = await http.post(
        Uri.parse(urlString),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'messages': messages}),
      ).timeout(const Duration(seconds: 60)); // Toplu tarama uzun sürebilir

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        return decoded['results'] as List<dynamic>;
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('API Hatası: \${response.statusCode} - \${response.body}')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Bağlantı Hatası: \$e')),
        );
      }
    }
    return null;
  }

  Future<void> _testManualMessage() async {
    if (_manualSmsController.text.isEmpty) return;
    setState(() {
      _isPredictingManual = true;
      _manualPredictionResult = null;
    });
    final result = await checkSmsWithApi(_manualSmsController.text, _manualSenderController.text);
    setState(() {
      _manualPredictionResult = result;
      _isPredictingManual = false;
    });
  }

  Future<void> _scanAllMessages() async {
    final ip = _ipController.text.trim();
    if (ip.isEmpty || ip.contains('X')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Önce API IP adresini girin!')),
      );
      return;
    }

    final bool? shouldContinue = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1C1C1E),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            const Icon(Icons.info_outline, color: Color(0xFFFFFFFF), size: 28),
            const SizedBox(width: 10),
            Expanded(
              child: Text('Google Mesajlar Bilgilendirmesi',
                  style: GoogleFonts.oswald(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
            ),
          ],
        ),
        content: const Text(
          'Eğer varsayılan SMS uygulaması olarak Google Mesajlar kullanıyorsanız, Google bazı zararsız (reklam/tanıtım) mesajlarını kendi inisiyatifiyle "Spam ve engellenenler" klasöründe gizleyebilir.\n\nEn sağlıklı tarama sonucu için, Google Mesajlar\'da "Spam ve engellenenler" klasörüne gidip, sizin için önemli olan ama spam\'a düşmüş mesajları "Spam değil" olarak işaretlemenizi öneririz.',
          style: TextStyle(color: Colors.white70, fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('İptal', style: TextStyle(color: Colors.white54)),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Color(0xFFFFFFFF).withValues(alpha: 0.2),
              foregroundColor: const Color(0xFFFFFFFF),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('Anladım, Taramayı Başlat'),
          ),
        ],
      ),
    );

    if (shouldContinue != true) return;

    setState(() {
      _isScanning = true;
      _scanProgress = 0;
      _predictions = {};
    });

    for (int i = 0; i < _inboxMessages.length; i++) {
      if (!_isScanning) break; // iptal kontrolü
      final msg = _inboxMessages[i];
      final result = await checkSmsWithApi(msg.body ?? '', msg.address ?? '');
      setState(() {
        if (result != null) _predictions[i] = result;
        _scanProgress = i + 1;
      });
    }

    final spamCount = _predictions.values.where((p) => p['etiket'] == 'spam').length;
    setState(() => _isScanning = false);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Tarama tamamlandı! ${_inboxMessages.length} mesaj tarandı, $spamCount spam tespit edildi.',
        ),
        backgroundColor: spamCount > 0 ? Colors.red.shade800 : Colors.green.shade800,
        duration: const Duration(seconds: 4),
      ),
    );

    // Spam varsa spam sekmesine geç
    if (spamCount > 0) {
      _tabController.animateTo(1);
    }
  }

  void _cancelScan() {
    setState(() => _isScanning = false);
  }

  Future<void> _exportSpamNumbers() async {
    final numbers = _spamEntries
        .map((e) => e.value.address ?? '')
        .where((n) => n.isNotEmpty)
        .toSet()
        .toList();

    if (numbers.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Henüz spam tespit edilmedi!')),
      );
      return;
    }

    try {
      final isDefault = await _platform.invokeMethod<bool>('isDefaultSmsApp') ?? false;
      if (mounted) setState(() => _isDefaultSmsApp = isDefault);
      
      if (!isDefault) {
        _showDefaultSmsRequiredDialog(numbers.length);
        return;
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Durum kontrolü başarısız: $e')),
        );
      }
      return;
    }
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Engelleme işlemi başlıyor...'), duration: Duration(seconds: 1)),
      );
    }

    // Yükleniyor göster
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1C1C1E),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(color: Color(0xFFFFFFFF)),
            const SizedBox(height: 16),
            Text('${numbers.length} numara engelleniyor...',
                style: GoogleFonts.oswald(color: Colors.white)),
          ],
        ),
      ),
    );

    try {
      // Önce direkt engellemeyi dene
      final blockResult = await _platform.invokeMethod<Map>('blockNumbers', {'numbers': numbers});
      final successCount = blockResult?['success'] as int? ?? 0;
      final failCount = blockResult?['fail'] as int? ?? 0;

      // İşlemden hemen sonra listeyi güncelle (Sistemin işlemesi için kısa bir gecikme ekliyoruz)
      await Future.delayed(const Duration(milliseconds: 500));
      await _loadInbox();

      if (mounted) Navigator.of(context, rootNavigator: true).pop(); // loading kapat

      if (successCount > 0 && failCount == 0) {
        // Tam başarı
        if (mounted) _showBlockSuccessDialog(successCount);
      } else if (successCount == 0) {
        // Hiç çalışmadı → dosyaya kaydet
        final filePath = await _platform.invokeMethod<String>('exportSpamNumbers', {'numbers': numbers});
        if (mounted) _showExportSuccessDialog(filePath ?? 'İndirilenler/spam_engel_listesi.txt', numbers.length);
      } else {
        // Kısmi başarı
        if (mounted) _showBlockSuccessDialog(successCount, failed: failCount);
      }
    } catch (e) {
      if (mounted) Navigator.of(context, rootNavigator: true).pop();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Hata: $e'), backgroundColor: Colors.red.shade800),
        );
      }
    }
  }

  void _showDefaultSmsRequiredDialog(int numberCount) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1C1C1E),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            const Icon(Icons.info_outline, color: Color(0xFFFFFFFF), size: 28),
            const SizedBox(width: 10),
            Expanded(
              child: Text('Bir Adım Gerekli',
                  style: GoogleFonts.oswald(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.orange.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.orange.withValues(alpha: 0.4)),
              ),
              child: Text(
                '$numberCount spam numarayı engellemek için SMS Security\'nin geçici olarak varsayılan mesaj uygulaması olması gerekiyor.',
                style: GoogleFonts.oswald(color: Colors.white70, fontSize: 13),
              ),
            ),
            const SizedBox(height: 16),
            _buildStep('1', '"Varsayılan Yap" butonuna bas'),
            _buildStep('2', 'Açılan sistemin diyaloğunda "SMS Security\'yi seç"'),
            _buildStep('3', 'Uygulamaya geri dön ve tekrar "Engelle" butonuna bas'),
            _buildStep('4', 'Engelleme bittikten sonra Google Messages\'a geri dönebilirsin'),
            const SizedBox(height: 8),
            Text(
              '⚠️ Bu süreçte yeni SMS almak için telefonunu kapat/aç gerekmez.',
              style: GoogleFonts.oswald(color: Colors.white54, fontSize: 12),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Vazgeç', style: GoogleFonts.oswald(color: Colors.white54)),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.pop(ctx);
              _requestDefaultSmsApp();
            },
            icon: const Icon(Icons.settings, size: 16),
            label: Text('Varsayılan Yap', style: GoogleFonts.oswald(fontWeight: FontWeight.bold)),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFFFFFFF),
              foregroundColor: Colors.black,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteSpamMessages(BuildContext ctx) async {
    Navigator.pop(ctx);
    
    final messageIds = _spamEntries
        .map((e) => e.value.id)
        .where((id) => id != null)
        .cast<int>()
        .toList();

    if (messageIds.isEmpty) return;

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Spam mesajlar siliniyor...')),
      );
    }

    try {
      final deletedCount = await _platform.invokeMethod<int>('deleteMessages', {'messageIds': messageIds});
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$deletedCount adet spam mesaj telefonunuzdan silindi!'),
            backgroundColor: Colors.green.shade700,
          ),
        );
        // Listeyi yenile
        await _loadInbox();
        
        // İşlemler bittiği için artık kullanıcının ana mesaj uygulamasına dönebilmesi adına yönlendir
        _platform.invokeMethod('openDefaultSmsSettings');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Silme işlemi başarısız: $e'), backgroundColor: Colors.red.shade700),
        );
      }
    }
  }

  Future<void> _unblockNumber(String number) async {
    try {
      final successCount = await _platform.invokeMethod<int>('unblockNumbers', {'numbers': [number]});
      if (successCount != null && successCount > 0) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('\$number numaralı engellenen gönderici Gelen Kutusuna geri alındı!'),
              backgroundColor: Colors.green.shade700,
            ),
          );
        }
        await _loadBlockedNumbers(); // Listeyi yenile
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Engel kaldırılamadı.'), backgroundColor: Colors.redAccent),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Hata: \$e'), backgroundColor: Colors.redAccent),
        );
      }
    }
  }

  void _showBlockSuccessDialog(int count, {int failed = 0}) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1C1C1E),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            const Icon(Icons.block, color: Colors.redAccent, size: 28),
            const SizedBox(width: 10),
            Expanded(
              child: Text('Numaralar Engellendi!',
                  style: GoogleFonts.oswald(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.green.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.greenAccent.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.check_circle, color: Colors.greenAccent, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text('$count numara başarıyla engellendi.',
                        style: GoogleFonts.oswald(color: Colors.greenAccent)),
                  ),
                ],
              ),
            ),
            if (failed > 0) ...[
              const SizedBox(height: 8),
              Text('$failed numara engellenemedi (yetersiz izin).',
                  style: GoogleFonts.oswald(color: Colors.white54, fontSize: 12)),
            ],
            const SizedBox(height: 12),
            Text(
              'Bu numaralar artık "Numaraları ve spam\'i engelle → Numaraları engelle" ekranında görünecek.',
              style: GoogleFonts.oswald(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: () => _deleteSpamMessages(ctx),
              icon: const Icon(Icons.delete_forever, size: 18),
              label: Text('Tüm Spam Mesajları Sil',
                  style: GoogleFonts.oswald(fontWeight: FontWeight.bold, fontSize: 13)),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red.shade800,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
            const SizedBox(height: 8),
            ElevatedButton.icon(
              onPressed: () {
                Navigator.pop(ctx);
                _platform.invokeMethod('openDefaultSmsSettings');
              },
              icon: const Icon(Icons.settings, size: 18),
              label: Text('Varsayılan Mesaj Uygulamasını Seç',
                  style: GoogleFonts.oswald(fontWeight: FontWeight.bold, fontSize: 13)),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFFFFFFF),
                foregroundColor: Colors.black,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Kapat', style: GoogleFonts.oswald(color: Colors.white54)),
          ),
        ],
      ),
    );
  }

  void _showExportSuccessDialog(String filePath, int count) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1C1C1E),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.greenAccent, size: 28),
            const SizedBox(width: 10),
            Text(
              'Dosya Kaydedildi!',
              style: GoogleFonts.oswald(color: Colors.white, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Color(0xFF1C1C1E),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.greenAccent.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.folder, color: Colors.greenAccent, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        filePath,
                        style: GoogleFonts.oswald(color: Colors.greenAccent, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Text(
                '$count numara dışa aktarıldı.',
                style: GoogleFonts.oswald(color: Colors.white70, fontSize: 13),
              ),
              const SizedBox(height: 16),
              Text(
                'Samsung Messages\'a nasıl eklersin?',
                style: GoogleFonts.oswald(color: const Color(0xFFFFFFFF), fontWeight: FontWeight.bold, fontSize: 14),
              ),
              const SizedBox(height: 12),
              _buildStep('1', 'Samsung Messages uygulamasını aç'),
              _buildStep('2', 'Sağ üst köşedeki ⋮ menüsüne dokun'),
              _buildStep('3', 'Ayarlar → Numaraları engelle'),
              _buildStep('4', 'Sağ üst ⋮ → Dosyadan içe aktar'),
              _buildStep('5', '"spam_engel_listesi.txt" dosyasını seç\n(İndirilenler klasöründe)'),
              _buildStep('6', 'Tümünü engelle → $count numara engellendi ✅'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Anladım', style: GoogleFonts.oswald(color: const Color(0xFFFFFFFF))),
          ),
        ],
      ),
    );
  }

  Widget _buildStep(String num, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: Color(0xFFFFFFFF).withValues(alpha: 0.2),
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0x1AFFFFFF)),
            ),
            child: Center(
              child: Text(num, style: GoogleFonts.oswald(color: const Color(0xFFFFFFFF), fontSize: 12, fontWeight: FontWeight.bold)),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text, style: GoogleFonts.oswald(color: Colors.white70, fontSize: 13)),
          ),
        ],
      ),
    );
  }

  // Filtered getters
  List<MapEntry<int, SmsMessage>> get _safeEntries => _inboxMessages
      .asMap()
      .entries
      .where((e) => !_predictions.containsKey(e.key) || _predictions[e.key]!['etiket'] != 'spam')
      .toList();

  List<MapEntry<int, SmsMessage>> get _spamEntries => _inboxMessages
      .asMap()
      .entries
      .where((e) => _predictions.containsKey(e.key) && _predictions[e.key]!['etiket'] == 'spam')
      .toList();

  Map<String, List<MapEntry<int, SmsMessage>>> _groupMessages(List<MapEntry<int, SmsMessage>> entries) {
    final Map<String, List<MapEntry<int, SmsMessage>>> grouped = {};
    for (var entry in entries) {
      final sender = entry.value.address ?? 'Bilinmeyen';
      if (!grouped.containsKey(sender)) {
        grouped[sender] = [];
      }
      grouped[sender]!.add(entry);
    }
    return grouped;
  }

  Map<String, List<Map<String, dynamic>>> _groupSystemSpam(List<Map<String, dynamic>> messages) {
    final Map<String, List<Map<String, dynamic>>> grouped = {};
    for (var msg in messages) {
      final sender = msg['address']?.toString() ?? 'Bilinmeyen';
      if (!grouped.containsKey(sender)) {
        grouped[sender] = [];
      }
      grouped[sender]!.add(msg);
    }
    return grouped;
  }

  Widget _buildGlassmorphismCard({required Widget child, Color? borderColor, Color? bgColor}) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: bgColor ?? Color(0xFF1C1C1E),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: borderColor ?? Color(0xFFFFFFFF),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.2),
                blurRadius: 10,
                spreadRadius: 2,
              )
            ],
          ),
          child: child,
        ),
      ),
    );
  }

  Widget _buildPredictionBadge(Map<String, dynamic> data) {
    bool isSpam = data['etiket'] == 'spam';
    bool isKumar = isSpam && data['guven'] == '99.0%'; // Backend'de hard-rule ile 0.99 (%99.0) atanıyor.
    
    Color bgColor = isKumar ? Colors.pinkAccent.withValues(alpha: 0.2) 
                   : (isSpam ? Colors.red.withValues(alpha: 0.2) : Colors.green.withValues(alpha: 0.2));
    Color borderColor = isKumar ? Colors.pinkAccent 
                       : (isSpam ? Colors.redAccent : Colors.greenAccent);
    Color textColor = isKumar ? Colors.pinkAccent 
                     : (isSpam ? Colors.redAccent : Colors.greenAccent);
    IconData iconData = isKumar ? Icons.casino 
                       : (isSpam ? Icons.warning_amber_rounded : Icons.check_circle_outline);
    String label = isKumar ? '🎰 KUMAR/BAHİS • ${data['guven']}' 
                  : (isSpam ? 'SPAM • ${data['guven']}' : 'Güvenli • ${data['guven']}');

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(iconData, color: textColor, size: 14),
          const SizedBox(width: 6),
          Text(
            label,
            style: GoogleFonts.oswald(
              fontSize: 12,
              color: textColor,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageCard(int originalIndex, SmsMessage msg, {bool showScanButton = false, bool isNested = false}) {
    final hasPrediction = _predictions.containsKey(originalIndex);
    
    Widget content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: isNested ? MainAxisAlignment.end : MainAxisAlignment.spaceBetween,
          children: [
            if (!isNested)
              Text(
                msg.address ?? 'Bilinmeyen',
                style: GoogleFonts.oswald(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
              ),
            Text(
              "${msg.date?.toLocal()}".split('.')[0],
              style: const TextStyle(fontSize: 10, color: Colors.white54),
            ),
          ],
        ),
        const SizedBox(height: 8),
          Text(msg.body ?? '', style: const TextStyle(color: Colors.white70)),
          if (hasPrediction) _buildPredictionBadge(_predictions[originalIndex]!),
          if (showScanButton && !hasPrediction) ...[
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton.icon(
                onPressed: () async {
                  final result = await checkSmsWithApi(msg.body ?? '', msg.address ?? '');
                  if (result != null) setState(() => _predictions[originalIndex] = result);
                },
                icon: const Icon(Icons.security, size: 16),
                label: const Text('Tara'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Color(0xFFFFFFFF),
                  foregroundColor: const Color(0xFFFFFFFF),
                  side: const BorderSide(color: Color(0xFFFFFFFF)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                ),
              ),
            ),
          ],
        ],
      );
    if (isNested) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 16.0),
        child: content,
      );
    }
    return _buildGlassmorphismCard(child: content);
  }

  Widget _buildScanProgress() {
    final total = _inboxMessages.length;
    final progress = total > 0 ? _scanProgress / total : 0.0;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Color(0x1AFFFFFF).withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Taranıyor: $_scanProgress / $total',
                style: GoogleFonts.oswald(color: const Color(0xFFFFFFFF), fontWeight: FontWeight.w600),
              ),
              TextButton(
                onPressed: _cancelScan,
                child: const Text('İptal', style: TextStyle(color: Colors.redAccent)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: progress,
              backgroundColor: Color(0xFFFFFFFF),
              color: const Color(0xFFFFFFFF),
              minHeight: 8,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final safeEntries = _safeEntries;
    final spamEntries = _spamEntries;

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF0F172A),
            Color(0xFF1C1C1E),
            Color(0xFF000000),
          ],
        ),
      ),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          centerTitle: true,
          title: Text(
            'SMS Security',
            style: GoogleFonts.oswald(fontWeight: FontWeight.w700, letterSpacing: 1.2),
          ),
          backgroundColor: Colors.transparent,
          elevation: 0,
          bottom: TabBar(
            controller: _tabController,
            indicatorColor: const Color(0xFFFFFFFF),
            labelColor: const Color(0xFFFFFFFF),
            unselectedLabelColor: Colors.white54,
            tabs: [
              Tab(icon: const Icon(Icons.inbox), text: "Gelen Kutusu (${safeEntries.length})"),
              Tab(
                icon: Badge(
                  isLabelVisible: spamEntries.isNotEmpty,
                  label: Text('${spamEntries.length}'),
                  child: const Icon(Icons.warning_amber_rounded),
                ),
                text: "Spam",
              ),
              Tab(
                icon: const Icon(Icons.block),
                text: "Engellenen Numaralar",
              ),
              Tab(
                icon: const Icon(Icons.folder_delete),
                text: "Google Spam (${_systemSpamMessages.length})",
              ),
              const Tab(icon: Icon(Icons.shield_moon), text: "Manuel Test"),
            ],
          ),
        ),
        body: Column(
          children: [
            // IP Adresi satırı
            ClipRRect(
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 5, sigmaY: 5),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: Color(0xFF1C1C1E),
                    border: Border(bottom: BorderSide(color: Color(0xFFFFFFFF))),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.wifi, color: Color(0xFFFFFFFF)),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: _ipController,
                          style: GoogleFonts.oswald(color: Colors.white, fontWeight: FontWeight.w500),
                          decoration: const InputDecoration(
                            labelText: "API IP Adresi",
                            border: InputBorder.none,
                            labelStyle: TextStyle(color: Colors.white54),
                            isDense: true,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      // Tüm Mesajları Tara butonu
                      _isScanning
                          ? const SizedBox(
                              width: 20, height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFFFFFFFF)),
                            )
                          : ElevatedButton.icon(
                              onPressed: _isLoadingInbox ? null : _scanAllMessages,
                              icon: const Icon(Icons.radar, size: 16),
                              label: const Text('Tümünü Tara'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Color(0xFFFFFFFF).withValues(alpha: 0.15),
                                foregroundColor: const Color(0xFFFFFFFF),
                                side: const BorderSide(color: Color(0xFFFFFFFF)),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              ),
                            ),
                    ],
                  ),
                ),
              ),
            ),

            // Tarama progress bar
            if (_isScanning) _buildScanProgress(),

            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  // ── TAB 1: Gelen Kutusu (spam olmayanlar) ──
                  _isLoadingInbox
                      ? const Center(child: CircularProgressIndicator(color: Color(0xFFFFFFFF)))
                      : safeEntries.isEmpty
                          ? Center(
                              child: Text(
                                _predictions.isEmpty
                                    ? 'Mesaj yok veya izin verilmedi.'
                                    : '🎉 Tüm mesajlar temiz!\nSpam tespit edilmedi.',
                                textAlign: TextAlign.center,
                                style: GoogleFonts.oswald(color: Colors.white54, fontSize: 16),
                              ),
                            )
                          : Builder(
                              builder: (context) {
                                final grouped = _groupMessages(safeEntries);
                                final senders = grouped.keys.toList();
                                return ListView.builder(
                                  padding: const EdgeInsets.all(16),
                                  itemCount: senders.length,
                                  itemBuilder: (context, i) {
                                    final sender = senders[i];
                                    final messages = grouped[sender]!;
                                    return _buildGlassmorphismCard(
                                      child: Theme(
                                        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                                        child: ExpansionTile(
                                          tilePadding: EdgeInsets.zero,
                                          title: Row(
                                            children: [
                                              const Icon(Icons.person, color: Color(0xFFFFFFFF)),
                                              const SizedBox(width: 8),
                                              Expanded(
                                                child: Text(
                                                  "$sender (${messages.length} Mesaj)",
                                                  style: GoogleFonts.oswald(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                                                ),
                                              ),
                                            ],
                                          ),
                                          children: messages.map((entry) {
                                            return _buildMessageCard(entry.key, entry.value, showScanButton: true, isNested: true);
                                          }).toList(),
                                        ),
                                      ),
                                    );
                                  },
                                );
                              },
                            ),

                  // ── TAB 2: Spam Kutusu ──
                  spamEntries.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.check_circle_outline, color: Colors.greenAccent, size: 64),
                              const SizedBox(height: 16),
                              Text(
                                'Spam kutusu boş!\nTümünü Tara butonuna bas.',
                                textAlign: TextAlign.center,
                                style: GoogleFonts.oswald(color: Colors.white54, fontSize: 16),
                              ),
                            ],
                          ),
                        )
                      : Column(
                          children: [
                            // Dışa Aktar Butonu
                            Padding(
                              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                              child: SizedBox(
                                width: double.infinity,
                                child: ElevatedButton.icon(
                                  onPressed: _exportSpamNumbers,
                                  icon: const Icon(Icons.block, size: 18),
                                  label: Text(
                                    'Tüm Spam Numaralarını Engelle (${spamEntries.length})',
                                    style: GoogleFonts.oswald(fontWeight: FontWeight.w600),
                                  ),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.red.shade900,
                                    foregroundColor: Colors.white,
                                    side: BorderSide(color: Colors.redAccent.withValues(alpha: 0.6)),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                    padding: const EdgeInsets.symmetric(vertical: 14),
                                  ),
                                ),
                              ),
                            ),
                            Expanded(
                              child: Builder(
                                builder: (context) {
                                  final groupedSpam = _groupMessages(spamEntries);
                                  final senders = groupedSpam.keys.toList();
                                  return ListView.builder(
                                    padding: const EdgeInsets.all(16),
                                    itemCount: senders.length,
                                    itemBuilder: (context, i) {
                                      final sender = senders[i];
                                      final messages = groupedSpam[sender]!;
                                      return _buildGlassmorphismCard(
                                        bgColor: Color(0xFF450a0a).withValues(alpha: 0.4),
                                        borderColor: Colors.redAccent.withValues(alpha: 0.6),
                                        child: Theme(
                                          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                                          child: ExpansionTile(
                                            tilePadding: EdgeInsets.zero,
                                            title: Row(
                                              children: [
                                                const Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 20),
                                                const SizedBox(width: 8),
                                                Expanded(
                                                  child: Text(
                                                    "$sender (${messages.length} Mesaj)",
                                                    style: GoogleFonts.oswald(
                                                      fontWeight: FontWeight.bold, fontSize: 16, color: Colors.redAccent,
                                                    ),
                                                  ),
                                                ),
                                              ],
                                            ),
                                            children: messages.map((entry) {
                                              return _buildMessageCard(entry.key, entry.value, showScanButton: false, isNested: true);
                                            }).toList(),
                                          ),
                                        ),
                                      );
                                    },
                                  );
                                },
                              ),
                            ),
                          ],
                        ),

                  // ── TAB 3: Google Spam / Engellenenler ──
                  _blockedNumbers.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.security, color: Colors.greenAccent, size: 64),
                              const SizedBox(height: 16),
                              Text(
                                'Engellenen Numara Yok',
                                textAlign: TextAlign.center,
                                style: GoogleFonts.oswald(color: Colors.white54, fontSize: 16),
                              ),
                              const SizedBox(height: 20),
                              ElevatedButton.icon(
                                onPressed: _loadBlockedNumbers,
                                icon: const Icon(Icons.refresh),
                                label: const Text('Listeyi Yenile'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Color(0xFFFFFFFF),
                                  foregroundColor: Colors.white,
                                ),
                              ),
                            ],
                          ),
                        )
                      : Column(
                          children: [
                            Padding(
                              padding: const EdgeInsets.all(16.0),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    'Toplam ${_blockedNumbers.length} numara engelli',
                                    style: GoogleFonts.oswald(color: Colors.white70, fontSize: 14),
                                  ),
                                  IconButton(
                                    onPressed: _loadBlockedNumbers,
                                    icon: const Icon(Icons.refresh, color: Color(0xFFFFFFFF)),
                                    tooltip: 'Listeyi Yenile',
                                  ),
                                ],
                              ),
                            ),
                            Expanded(
                              child: ListView.builder(
                                padding: const EdgeInsets.symmetric(horizontal: 16),
                                itemCount: _blockedNumbers.length,
                                itemBuilder: (context, i) {
                                  final number = _blockedNumbers[i];
                                  return _buildGlassmorphismCard(
                                    bgColor: const Color(0xFF1C1C1E),
                                    borderColor: Colors.redAccent.withValues(alpha: 0.3),
                                    child: Row(
                                      children: [
                                        const Icon(Icons.block, color: Colors.redAccent, size: 28),
                                        const SizedBox(width: 12),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                number,
                                                style: GoogleFonts.oswald(
                                                    fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                                              ),
                                              const SizedBox(height: 4),
                                              Text(
                                                "Bu gönderici sistem tarafından engellenmiş.",
                                                style: const TextStyle(color: Colors.white54, fontSize: 12),
                                              ),
                                            ],
                                          ),
                                        ),
                                        ElevatedButton.icon(
                                          onPressed: () => _unblockNumber(number),
                                          icon: const Icon(Icons.check_circle, size: 16),
                                          label: const Text('Engeli Kaldır'),
                                          style: ElevatedButton.styleFrom(
                                            backgroundColor: Colors.green.shade800,
                                            foregroundColor: Colors.white,
                                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                          ),
                                        ),
                                      ],
                                    ),
                                  );
                                },
                              ),
                            ),
                          ],
                        ),

                  // ── TAB 4: Google Spam / Gelen Kutusuna Alma ──
                  _systemSpamMessages.isEmpty
                      ? Center(
                          child: SingleChildScrollView(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.mark_email_read, color: Colors.greenAccent, size: 64),
                                const SizedBox(height: 16),
                                Text(
                                  _isDefaultSmsApp
                                      ? 'Google Spam Kutusu Boş'
                                      : 'Spam Mesajları Göremiyoruz',
                                  textAlign: TextAlign.center,
                                  style: GoogleFonts.oswald(color: Colors.white54, fontSize: 16, fontWeight: FontWeight.bold),
                                ),
                                const SizedBox(height: 12),
                                Container(
                                  margin: const EdgeInsets.symmetric(horizontal: 32),
                                  padding: const EdgeInsets.all(16),
                                  decoration: BoxDecoration(
                                    color: Color(0xFF1C1C1E),
                                    borderRadius: BorderRadius.circular(16),
                                    border: Border.all(color: Colors.orange.withValues(alpha: 0.3)),
                                  ),
                                  child: Text(
                                    _isDefaultSmsApp
                                        ? 'Uygulama varsayılan SMS uygulaması olarak ayarlı ancak gizli spam mesaj bulunamadı. Google Mesajlar spam mesajlarını kendi özel veritabanında saklıyor olabilir.'
                                        : 'Google Mesajlar, spam olarak işaretlediği mesajları kendi özel veritabanında saklar. Bu mesajları görebilmek için SMS Security\'nin geçici olarak varsayılan SMS uygulaması olması gerekir.',
                                    textAlign: TextAlign.center,
                                    style: GoogleFonts.oswald(color: Colors.white38, fontSize: 13),
                                  ),
                                ),
                                const SizedBox(height: 20),
                                if (!_isDefaultSmsApp)
                                  ElevatedButton.icon(
                                    onPressed: () async {
                                      await _requestDefaultSmsApp();
                                      await Future.delayed(const Duration(seconds: 1));
                                      await _checkDefaultSmsApp();
                                      await _loadSystemSpam();
                                    },
                                    icon: const Icon(Icons.settings, size: 18),
                                    label: const Text('Varsayılan SMS Uygulaması Yap'),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Color(0xFFFFFFFF).withValues(alpha: 0.2),
                                      foregroundColor: const Color(0xFFFFFFFF),
                                      side: const BorderSide(color: Color(0xFFFFFFFF)),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                                    ),
                                  ),
                                if (_isDefaultSmsApp)
                                  ElevatedButton.icon(
                                    onPressed: _loadSystemSpam,
                                    icon: const Icon(Icons.refresh, size: 18),
                                    label: const Text('Yeniden Tara'),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Color(0xFFFFFFFF),
                                      foregroundColor: Colors.white,
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                                    ),
                                  ),
                                const SizedBox(height: 12),
                                TextButton.icon(
                                  onPressed: _debugSmsTypes,
                                  icon: const Icon(Icons.bug_report, size: 16, color: Colors.white38),
                                  label: Text('SMS Veritabanı Bilgisi',
                                      style: GoogleFonts.oswald(color: Colors.white38, fontSize: 12)),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  _isDefaultSmsApp ? '✅ Varsayılan SMS Uygulaması' : '❌ Varsayılan SMS Uygulaması Değil',
                                  style: GoogleFonts.oswald(
                                    color: _isDefaultSmsApp ? Colors.greenAccent : Colors.redAccent,
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        )
                      : Builder(
                          builder: (context) {
                            final groupedSpam = _groupSystemSpam(_systemSpamMessages);
                            final senders = groupedSpam.keys.toList();
                            return ListView.builder(
                              padding: const EdgeInsets.all(16),
                              itemCount: senders.length,
                              itemBuilder: (context, i) {
                                final sender = senders[i];
                                final messages = groupedSpam[sender]!;
                                return _buildGlassmorphismCard(
                                  bgColor: Color(0xFF1C1C1E),
                                  borderColor: Color(0xFFFFFFFF),
                                  child: Theme(
                                    data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                                    child: ExpansionTile(
                                      tilePadding: EdgeInsets.zero,
                                      title: Row(
                                        children: [
                                          const Icon(Icons.folder_delete, color: Colors.orangeAccent, size: 20),
                                          const SizedBox(width: 8),
                                          Expanded(
                                            child: Text(
                                              "$sender (${messages.length} Mesaj)",
                                              style: GoogleFonts.oswald(
                                                fontWeight: FontWeight.bold, fontSize: 16, color: Colors.orangeAccent,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                      children: messages.map((msg) {
                                        final int id = msg['id'] as int;
                                        final bool isScanned = _systemSpamPredictions.containsKey(id);
                                        final bool isSpam = isScanned && _systemSpamPredictions[id]!['etiket'] == 'spam';
                                        
                                        return Padding(
                                          padding: const EdgeInsets.only(bottom: 16.0),
                                          child: Container(
                                            padding: const EdgeInsets.all(12),
                                            decoration: BoxDecoration(
                                              color: isScanned
                                                  ? (isSpam ? Color(0xFF450a0a).withValues(alpha: 0.5) : Color(0xFF064e3b).withValues(alpha: 0.5))
                                                  : Colors.black.withValues(alpha: 0.2),
                                              borderRadius: BorderRadius.circular(12),
                                              border: Border.all(
                                                color: isScanned
                                                    ? (isSpam ? Colors.redAccent : Colors.greenAccent)
                                                    : Color(0xFF1C1C1E),
                                              ),
                                            ),
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                Row(
                                                  mainAxisAlignment: MainAxisAlignment.end,
                                                  children: [
                                                    Text(
                                                      DateTime.fromMillisecondsSinceEpoch(msg['date'] as int).toString().split('.')[0],
                                                      style: const TextStyle(fontSize: 10, color: Colors.white54),
                                                    ),
                                                  ],
                                                ),
                                                const SizedBox(height: 8),
                                                Text(msg['body']?.toString() ?? '', style: const TextStyle(color: Colors.white70)),
                                                if (isScanned) _buildPredictionBadge(_systemSpamPredictions[id]!),
                                                const SizedBox(height: 12),
                                                Row(
                                                  mainAxisAlignment: MainAxisAlignment.end,
                                                  children: [
                                                    if (!isScanned)
                                                      ElevatedButton.icon(
                                                        onPressed: () async {
                                                          final result = await checkSmsWithApi(msg['body']?.toString() ?? '', msg['address']?.toString() ?? '');
                                                          if (result != null) {
                                                            setState(() {
                                                              _systemSpamPredictions[id] = result;
                                                            });
                                                          }
                                                        },
                                                        icon: const Icon(Icons.radar, size: 16),
                                                        label: const Text('Tara'),
                                                        style: ElevatedButton.styleFrom(
                                                          backgroundColor: Color(0xFFFFFFFF).withValues(alpha: 0.15),
                                                          foregroundColor: const Color(0xFFFFFFFF),
                                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                                        ),
                                                      ),
                                                    if (isScanned && !isSpam) ...[
                                                      const SizedBox(width: 8),
                                                      Expanded(
                                                        child: Container(
                                                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                                          decoration: BoxDecoration(
                                                            color: Colors.green.withValues(alpha: 0.1),
                                                            borderRadius: BorderRadius.circular(12),
                                                            border: Border.all(color: Colors.greenAccent.withValues(alpha: 0.3)),
                                                          ),
                                                          child: Row(
                                                            children: [
                                                              const Icon(Icons.info_outline, color: Colors.greenAccent, size: 16),
                                                              const SizedBox(width: 6),
                                                              Expanded(
                                                                child: Text(
                                                                  'Google mesajlarda spam olarak gözüken mesaj aslında spam değil.',
                                                                  style: GoogleFonts.oswald(color: Colors.greenAccent, fontSize: 12),
                                                                ),
                                                              ),
                                                            ],
                                                          ),
                                                        ),
                                                      ),
                                                    ]
                                                  ],
                                                ),
                                              ],
                                            ),
                                          ),
                                        );
                                      }).toList(),
                                    ),
                                  ),
                                );
                              },
                            );
                          },
                        ),

                  // ── TAB 5: Manuel Test ──
                  SingleChildScrollView(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      children: [
                        TextField(
                          controller: _manualSenderController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            labelText: 'Gönderen (Örn: THY, 0532...)',
                            labelStyle: const TextStyle(color: Colors.white54),
                            filled: true,
                            fillColor: Color(0xFF1C1C1E),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: Color(0xFFFFFFFF)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: const BorderSide(color: Color(0xFFFFFFFF), width: 2),
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _manualSmsController,
                          maxLines: 4,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            labelText: 'SMS Metnini Buraya Yapıştırın',
                            labelStyle: const TextStyle(color: Colors.white54),
                            filled: true,
                            fillColor: Color(0xFF1C1C1E),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: Color(0xFFFFFFFF)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: const BorderSide(color: Color(0xFFFFFFFF), width: 2),
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),
                        SizedBox(
                          width: double.infinity,
                          height: 55,
                          child: Container(
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                colors: [Color(0xFFFFFFFF), Color(0xFF7000FF)],
                                begin: Alignment.centerLeft,
                                end: Alignment.centerRight,
                              ),
                              borderRadius: BorderRadius.circular(12),
                              boxShadow: [
                                BoxShadow(
                                  color: Color(0xFFFFFFFF).withValues(alpha: 0.3),
                                  blurRadius: 10,
                                  offset: const Offset(0, 4),
                                )
                              ],
                            ),
                            child: ElevatedButton(
                              onPressed: _isPredictingManual ? null : _testManualMessage,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.transparent,
                                shadowColor: Colors.transparent,
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              ),
                              child: _isPredictingManual
                                  ? const CircularProgressIndicator(color: Colors.white)
                                  : Text(
                                      'Yapay Zeka ile Analiz Et',
                                      style: GoogleFonts.oswald(
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                        color: Colors.white,
                                        letterSpacing: 1.1,
                                      ),
                                    ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),
                        if (_manualPredictionResult != null) ...[
                          _buildGlassmorphismCard(
                            bgColor: _manualPredictionResult!['etiket'] == 'spam'
                                ? Color(0xFF450a0a).withValues(alpha: 0.5)
                                : Color(0xFF064e3b).withValues(alpha: 0.5),
                            borderColor: _manualPredictionResult!['etiket'] == 'spam'
                                ? Colors.redAccent
                                : Colors.greenAccent,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Icon(
                                      _manualPredictionResult!['etiket'] == 'spam'
                                          ? Icons.warning_amber_rounded
                                          : Icons.check_circle_outline,
                                      color: _manualPredictionResult!['etiket'] == 'spam'
                                          ? Colors.redAccent
                                          : Colors.greenAccent,
                                      size: 28,
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Text(
                                        _manualPredictionResult!['sonuc'],
                                        style: GoogleFonts.oswald(
                                          color: _manualPredictionResult!['etiket'] == 'spam'
                                              ? Colors.redAccent
                                              : Colors.greenAccent,
                                          fontSize: 18,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: Colors.black.withValues(alpha: 0.5),
                                        borderRadius: BorderRadius.circular(20),
                                      ),
                                      child: Text(
                                        "Güven: ${_manualPredictionResult!['guven']}",
                                        style: GoogleFonts.oswald(fontSize: 12, color: Colors.white),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 12),
                                Text("Tehlike Skoru: ${_manualPredictionResult!['tehlike_skoru']}",
                                    style: const TextStyle(color: Colors.white70, fontSize: 13)),
                                Text(
                                  "BTK: ${_manualPredictionResult!['btk_kodu'] == true ? '✅' : '❌'} "
                                  "MERSIS: ${_manualPredictionResult!['mersis'] == true ? '✅' : '❌'} "
                                  "IYS: ${_manualPredictionResult!['iys_bilgi'] == true ? '✅' : '❌'}",
                                  style: const TextStyle(color: Colors.white54, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
