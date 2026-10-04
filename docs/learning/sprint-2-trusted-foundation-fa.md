# راهنمای یادگیری Sprint 2: اعتماد، مالکیت و ارزیابی واقعی

## تصویر کلی

Sprint 1 ثابت کرد مسیر `upload → ingest → retrieve → answer → citation` کار می‌کند. Sprint 2 یک
مرز مهم اضافه می‌کند: هر درخواست باید متعلق به یک کاربر واقعی باشد و هیچ UUID حدس‌زده‌شده‌ای
نباید داده کاربر دیگری را آشکار کند. در کنار آن، مدل رایگان فقط وقتی قابل انتخاب است که روی داده
فارسی/انگلیسی خود پروژه اندازه‌گیری شده باشد.

## Authentication و Authorization

Authentication یعنی «این درخواست از طرف چه کسی است؟». Authorization یعنی «این کاربر اجازه این
عمل را روی این منبع دارد؟». پس از ورود، Backend از session به `user_id` داخلی می‌رسد. همه queryها
مثل collection، document، conversation و vector search شرط `owner_id=user_id` دارند. ایمیل کلید
مالکیت نیست؛ ایمیل قابل تغییر و داده‌ای برای ورود است، ولی UUID هویت پایدار داخلی است.

## مسیر کامل ثبت‌نام تا خروج

1. کاربر نام نمایشی اختیاری، ایمیل و password را در صفحه ثبت‌نام وارد می‌کند.
2. Backend ابتدا Origin مرورگر و سپس سقف تلاش جداگانه برای IP و ایمیل نرمال‌شده را بررسی می‌کند.
3. policy ایمیل و password را validate می‌کند و Argon2id hash را می‌سازد.
4. transaction با یک insert اتمیک ایمیل را claim می‌کند، User و PasswordCredential را می‌سازد و
   session تازه ایجاد می‌کند. اگر درخواست هم‌زمان دیگری همان ایمیل را گرفته باشد، نتیجه امن 409 است.
5. مرورگر session را در cookie از نوع `HttpOnly` می‌گیرد؛ JavaScript نمی‌تواند secret را بخواند.
6. در درخواست بعدی API digest کوکی را پیدا می‌کند، revocation و دو نوع expiry و فعال‌بودن User را
   می‌سنجد و UUID را به use case می‌دهد.
7. logout همان session را در دیتابیس revoke می‌کند؛ تکرار logout بی‌خطر است.

## Argon2id، salt و دلیل استفاده‌نکردن از SHA-256 برای password

Password معمولاً entropy کمی دارد و مهاجم می‌تواند میلیاردها حدس رایج بسازد. SHA-256 عمداً سریع
است، پس برای password انتخاب بدی است. Argon2id با مصرف زمان و حافظه، هر حدس را گران می‌کند. salt
تصادفی داخل hash رمزگذاری‌شده نگه داشته می‌شود و باعث می‌شود دو password یکسان hash یکسان نداشته
باشند. پارامتر اندازه‌گیری‌شده روی Apple M2 این پروژه `64 MiB / time=3 / parallelism=2` است؛ median
hash حدود `56.56ms` و verify حدود `57.84ms` بود. در مقابل session token واقعاً تصادفی و پرentropy
است، پس SHA-256 برای پنهان‌کردن مقدار خام آن در دیتابیس مناسب است.

## Opaque Session در برابر JWT

Opaque token خودش اطلاعات قابل اعتماد ندارد؛ فقط یک کلید تصادفی برای رکورد دیتابیس است. مزیت این
پروژه revocation فوری، logout-all ساده و بررسی disabled user در هر request است. JWT بدون طراحی
blocklist معمولاً تا پایان اعتبار زنده می‌ماند. هزینه opaque session یک lookup دیتابیس است که برای
modular monolith و beta اولیه قابل قبول‌تر از پیچیدگی JWT است.

## Cookie flags، Session Fixation، CSRF و CORS

- `HttpOnly`: اسکریپت مرورگر session secret را نمی‌خواند.
- `Secure`: در staging/production فقط HTTPS؛ برنامه تنظیم ناامن را reject می‌کند.
- `SameSite=Lax`: ارسال cross-site را محدود می‌کند.
- `__Host-`: بدون Domain و با Path=/، scope کوکی را سخت‌تر می‌کند.
- Session fixation: بعد از register/login همیشه token تازه ساخته می‌شود و ورودی کاربر به‌عنوان ID
  session پذیرفته نمی‌شود.

CORS تعیین می‌کند کدام origin اجازه خواندن پاسخ را دارد؛ دفاع کامل CSRF نیست. CSRF یعنی مرورگر
ممکن است cookie را خودکار همراه درخواست مخرب بفرستد. برای methodهای unsafe، Backend هم Origin دقیق
و هم `X-CSRF-Token` متصل به session را می‌خواهد.

سه endpoint ورود، ثبت‌نام و تکمیل reset هنوز Origin مرورگر را دقیق بررسی می‌کنند، اما
به CSRF متصل به session نیاز ندارند. دلیلش این است که ممکن است مرورگر یک cookie منقضی یا revoke‌شده
داشته باشد؛ اگر همان session مرده شرط recovery باشد، کاربر دیگر نمی‌تواند دوباره وارد شود. credential
یا token یک‌بارمصرف مجوز عملیات است و Origin دقیق جلوی login CSRF مرورگری را می‌گیرد.

## Registration و reset lifecycle

Registration دیگر token ندارد. محدودیت IP جلوی ساخت انبوه حساب از یک مبدأ و محدودیت ایمیل جلوی
تکرار پرهزینه برای یک شناسه را می‌گیرد. unique constraint به‌تنهایی کافی نیست، چون دو درخواست ممکن
است هم‌زمان قبل از insert وجود ایمیل را بررسی کنند؛ `ON CONFLICT DO NOTHING` نتیجه را در خود
PostgreSQL اتمیک می‌کند. reset token همچنان digest، انقضا، زمان مصرف و revocation دارد. reset موفق
hash جدید را ذخیره و همه sessionهای قبلی را revoke می‌کند. چون email provider نداریم، ادمین بعد از
احراز هویت خارج از سیستم token کوتاه‌عمر می‌سازد.

## Generic login error و brute-force protection

ایمیل ناشناخته، password اشتباه و user غیرفعال همگی `invalid_credentials` می‌دهند تا وجود حساب لو
نرود. برای ایمیل ناشناخته نیز یک dummy Argon2 verify انجام می‌شود تا اختلاف زمان واضح کم شود. Redis
تعداد تلاش را روی شناسه کاهش‌یافته نگه می‌دارد و پس از حد، `429 + Retry-After` می‌دهد.

## Pagination و resume

Collection و conversation با cursor پایدار صفحه‌بندی می‌شوند؛ offset هنگام اضافه‌شدن رکورد جدید
می‌تواند item را تکراری/گم کند. URL شامل collection/conversation UUID است. برای resume، frontend
پیام‌های persisted را می‌خواند؛ پاسخ قدیمی دوباره به LLM فرستاده نمی‌شود، پس citation و متن دقیقاً
همان نسخه ثبت‌شده باقی می‌ماند.

## مالکیت در retrieval

فیلتر پس از vector search دیر است: حتی score و وجود chunk دیگران لو می‌رود. query dense و lexical
قبل از ranking شرط‌های owner، collection زنده، document زنده و version آماده را اعمال می‌کند. تست
دو کاربر مسیر collection، upload، retry، conversation، message، feedback و deletion را با UUID
کاربر اول از session کاربر دوم امتحان می‌کند.

## حذف idempotent

ابتدا tombstone و یک cleanup job پایدار در یک transaction ثبت می‌شوند. queryهای عادی و retrieval
فوراً tombstone را کنار می‌گذارند. delivery قدیمی worker قبل از claim و قبل از READY دوباره حذف را
بررسی می‌کند. اگر delete دوبار برسد همان job برمی‌گردد؛ این تعریف idempotency است. worker ابتدا
object را حذف می‌کند، سپس citationها را قبل از chunkهای مرجع پاک و metadata کاربر را redact می‌کند.
اگر broker پیام را نگیرد، reconciler job پایدار را دوباره dispatch می‌کند. انقضای backup هنوز policy
زیرساخت جدا می‌خواهد؛ بنابراین «پاک‌سازی application» با «انقضای همه backupها» یکی نیست.

## Feedback و quota

Feedback به user، assistant message و RagRun دقیق متصل است و model/retriever metadata را نگه
می‌دارد. دلیل ساخت‌یافته برای تحلیل بهتر از متن آزاد است، اما خودکار training data نمی‌شود. quotaها
روی Backend اعمال می‌شوند: اندازه فایل، تعداد سند، سؤال روزانه، generation هم‌زمان، session فعال و
login attempt. UI فقط پیام بازیابی دوزبانه است و مرز امنیتی نیست.

## ارزیابی مدل واقعی

Dataset شامل ۸۰ سؤال کنترل‌شده، دو PDF چهارصفحه‌ای فارسی/انگلیسی، سؤال cross-lingual، بی‌پاسخ و
prompt injection است. PDF از همان extractor تولید استفاده می‌کند و checksum drift بررسی می‌شود.
runner Recall@K، MRR، سند+صفحه درست، citation validity/support، relevance، abstention، TTFT، latency،
digest مدل و hardware را ثبت می‌کند. fake provider فقط قرارداد CI را اثبات می‌کند؛ کیفیت محصول نیست.

Qwen 2.5 1.5B روی Apple M2/8GB سریع و بدون هزینه API اجرا شد، ولی baseline خودکار آن groundedness
`0.1875` و relevance `0.3875` داشت؛ پس «مدل محبوب» بدون measurement انتخاب نمی‌شود. human-review
هم باید پاسخ و شاهد را با امتیاز ۰ تا ۲ بررسی کند. تا زمانی که یک مدل gate را پاس نکند، release
عمومی block می‌ماند.

در اجرای اولیه Qwen 3، Backend کل پاسخ Ollama را با `stream:false` می‌گرفت و بعد کلمه‌به‌کلمه نمایش
می‌داد؛ این streaming واقعی نبود. علاوه بر آن، reasoning داخلی مدل median زمان اولین خروجی را به
حدود `8.25s` رساند. adapter اصلاح شد تا stream واقعی Ollama را بخواند، thinking را برای این قرارداد
کوتاه خاموش کند و markerهای داخلی citation/abstention را به UI نفرستد. سپس هر دو مدل از نو و از مسیر
یکسان اندازه‌گیری شدند.

Qwen 3 1.7B با همان retrieval، groundedness proxy را به `0.75`، relevance را به `0.60` و abstention
را به `0.9125` رساند. median زمان اولین token حدود `2.01s` و کل پاسخ حدود `2.35s` شد؛ تقریباً هم‌سطح
Qwen 2.5 اما با proxyهای بسیار بهتر. این نتایج هنوز امتیاز انسانی نیستند. بنابراین Qwen 3 فقط
candidate خودکار برتر است، نه مدل نهایی. گزارش مقایسه در `docs/evaluation/sprint-2.md` است.

## trace یک سند از upload تا delete

مرورگر با session و CSRF فایل را stream می‌کند؛ API owner و quota را می‌سنجد، SHA-256 و MIME را
بررسی و source را در MinIO ذخیره می‌کند، سپس DocumentVersion و IngestionJob را commit می‌کند. worker
صفحات را extract، متن جست‌وجو را normalize، chunkها را embed و نسخه را اتمیک READY می‌کند. سؤال در
conversation ذخیره می‌شود؛ retrieval فقط chunkهای مجاز را pack می‌کند؛ generator شواهد untrusted را
می‌گیرد؛ Backend citation ID را validate و پاسخ را persist/stream می‌کند. هنگام delete، tombstone و
cleanup job قبل از پاسخ API ثبت می‌شوند؛ همان chunk فوراً از retrieval خارج و سپس به‌شکل retryable
از storage و PostgreSQL پاک می‌شود.

## شکست‌ها و درس‌ها

- abstention قبلاً بیشتر به متن stream و یک badge کوچک وابسته بود و API تاریخچه تصمیم مدل را
  برنمی‌گرداند؛ بنابراین پاسخ خالی یا conversation بازشده می‌توانست برای کاربر مبهم باشد. اکنون
  backend یک پیام fallback روشن را persist می‌کند و فیلد `abstained` از وضعیت RagRun در تاریخچه
  برمی‌گردد. UI حتی با متن خالی یک حالت مستقل نشان می‌دهد: پاسخ در اسناد پیدا نشد، سؤال را با
  عبارت دقیق‌تر امتحان کنید یا سند مرتبط اضافه کنید. این UX به‌جای حدس‌زدن، کمبود شاهد را صریح
  می‌گوید.
- provider قطعی محیط توسعه نام فایل را با عبارت `According to ...` داخل خود answer قرار می‌داد،
  درحالی‌که همان منبع جداگانه در citation معتبر ارسال می‌شد. این تکرار مسئولیت متن پاسخ و نمایش
  منبع را مخلوط می‌کرد. نسخه `extractive-overlap-v2` فقط جملهٔ پشتیبان را به‌عنوان answer می‌فرستد
  و نام سند همچنان در citation قابل بازرسی باقی می‌ماند؛ پاسخ‌های تاریخی عمداً بازنویسی نمی‌شوند.
- مسیرهای JSON از Axios استفاده می‌کردند و Axios به‌صورت مرکزی cookie و CSRF header را می‌فرستاد،
  اما answer stream به‌دلیل خواندن تدریجی SSE از `fetch` مستقل استفاده می‌کرد. `fetch` در درخواست
  cross-origin بدون `credentials: include`، session cookie را نفرستاد و پاسخ `401` شد؛ اگر فقط
  cookie اصلاح می‌شد، نبود `X-CSRF-Token` پاسخ `403` می‌داد. اکنون streaming هر دو بخش قرارداد
  امنیتی را صریح می‌فرستد و تست request shape جلوی بازگشت این تفاوت را می‌گیرد.
- اجرای اول مدل واقعی پس از چند ده سؤال timeout شد؛ نبود سقف خروجی می‌توانست generation را runaway
  کند. اکنون `num_predict`، timeout و ثبت provider failure وجود دارد.
- streaming نمایشی می‌توانست TTFT را اشتباه نشان دهد؛ اکنون delta مستقیماً از stream واقعی provider
  می‌آید و footer کنترلی پیش از نمایش نگه داشته و توسط Backend parse/validate می‌شود.
- مدل کوچک در RAM جا شد اما کیفیت grounded کافی نبود؛ feasibility فقط memory نیست.
- citation دارای foreign key محدودکننده بود؛ cleanup باید اول citation را حذف کند و بعد chunk را.
  این ترتیب نمونه‌ای از dependency-safe deletion است.
- اجرای واقعی Celery نشان داد وجود جدول در PostgreSQL کافی نیست: هر process باید همه مدل‌های
  SQLAlchemy را در registry خودش بارگذاری کند. API به‌طور اتفاقی از مسیر routeها مدل `users` را
  import می‌کرد، اما worker مستقل این کار را نمی‌کرد و cleanup پیش از claim با
  `NoReferencedTableError` متوقف می‌شد. اکنون ساخت هر `Database` رجیستری canonical را بارگذاری
  می‌کند و یک تست در process تازه کل گراف foreign key را resolve می‌کند. لاگ‌های cleanup نیز فقط
  شناسه هم‌بستگی، نوع منبع، مدت، error code و نوع exception را ثبت می‌کنند؛ نه نام فایل، storage
  key یا متن سند را.
- مالکیت Auth داخلی یعنی patching، recovery، incident response و تست امنیتی مسئولیت خود پروژه است.

## واژه‌نامه کوتاه

- Transaction: مجموعه تغییراتی که یا همگی commit می‌شوند یا هیچ‌کدام.
- Revocation: بی‌اعتبارکردن server-side پیش از expiry.
- Entropy: میزان غیرقابل‌حدس‌بودن token.
- Tombstone: علامت حذف پایدار به‌جای پاک‌سازی فوری همه ردیف‌ها.
- Groundedness: میزان پشتیبانی پاسخ توسط شواهد ارائه‌شده.
- TTFT: زمان تا اولین بخش قابل نمایش پاسخ.
