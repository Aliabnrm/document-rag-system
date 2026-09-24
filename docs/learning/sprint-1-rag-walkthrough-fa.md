# راهنمای آموزشی فارسی Sprint 1: از فایل تا پاسخ مستند

این سند یک درخواست واقعی را قدم‌به‌قدم دنبال می‌کند تا مرز Backend، پایگاه داده، Worker و AI روشن
شود. مثال ما فایل `ava-guide.txt` با جمله‌ی «مدیر عامل شرکت آوا، لیلا نوری است» و سؤال «مدیر عامل
شرکت آوا چه کسی است؟» است.

## ۱. API با Use Case چه فرقی دارد؟

API قرارداد HTTP است: آدرس، JSON، فایل multipart، status code و SSE را می‌فهمد. Use Case هدف
کاربر را اجرا می‌کند و نباید بداند FastAPI چیست. برای آپلود، route ورودی را به
`CreateDocumentUpload` می‌دهد؛ use case از سه port استفاده می‌کند: repository، object storage و
job dispatcher. اگر فردا FastAPI یا MinIO عوض شود، قانون کسب‌وکار بازنویسی نمی‌شود.

جریان مثال:

```text
Browser → POST /api/v1/collections/{id}/documents
Route → CreateDocumentUpload
Use case → validate/store/persist/dispatch
Route ← UploadAccepted DTO ← 202
```

## ۲. Domain Model و State Machine

`Document` شناسه‌ی پایدار سند است. `DocumentVersion` بایت‌های immutable یک آپلود و نسخه‌ی pipeline
را نشان می‌دهد. این جداسازی حیاتی است: پاسخ دیروز نباید پس از جایگزینی فایل، ناگهان به محتوای جدید
اشاره کند.

State machine انتقال‌های مجاز را صریح می‌کند:

```text
uploaded → queued → extracting → chunking → embedding → ready
```

هر مرحله می‌تواند به `failed` برود و فقط use case retry اجازه‌ی `failed → queued` دارد. اگر برنامه
بخواهد مستقیم از `uploaded` به `ready` برود، domain error رخ می‌دهد. این یعنی وضعیت فقط یک string
تزئینی نیست؛ یک قانون قابل تست است.

## ۳. Transaction و Migration

Transaction یعنی چند تغییر یا همگی موفق شوند یا هیچ‌کدام. ایجاد Document، DocumentVersion و
IngestionJob در یک transaction انجام می‌شود؛ بنابراین job بدون سند یا سند بدون job باقی نمی‌ماند.
فایل ابتدا در MinIO ذخیره می‌شود و اگر transaction شکست بخورد، همان object پاک می‌شود.

Migration تاریخچه‌ی نسخه‌بندی schema است. Alembic جدول‌ها، constraintها، indexها و extension
`vector` را از یک دیتابیس خالی می‌سازد. تغییر schema با دست روی لپ‌تاپ قابل بازتولید نیست؛ migration
باعث می‌شود CI، هم‌تیمی و production دقیقاً همان ساختار را بسازند.

## ۴. Queue و Worker

آپلود نباید تا پایان PDF extraction و embedding منتظر بماند. API job پایدار را ثبت می‌کند، شناسه‌های
job/version را به Redis می‌فرستد و سریع `202` می‌دهد. Worker فرایند جداگانه‌ای است که کار سنگین را
انجام می‌دهد.

Redis منبع حقیقت نیست؛ فقط پیام‌رسان است. اگر API دقیقاً بین commit و send خاموش شود، Beat jobهای
queued قدیمی را دوباره dispatch می‌کند. این الگو delivery را `at-least-once` می‌کند: ممکن است پیام
بیش از یک بار برسد، ولی از دست‌رفتن آن با reconciliation جبران می‌شود.

## ۵. Idempotency و Retry

Idempotency یعنی اجرای دوباره نتیجه‌ی ناسازگار یا تکراری نسازد. Worker قبل از کار job را با row lock
claim می‌کند. job موفق یا در حال اجرا دوباره پردازش نمی‌شود. هنگام تکمیل نیز chunkهای همان version در
transaction جایگزین و فقط یک‌بار visible می‌شوند.

خطای دائمی مثل PDF رمزدار retry خودکار ندارد؛ دوباره امتحان‌کردن همان بایت‌ها چیزی را حل نمی‌کند.
خطای موقت مثل timeout سرویس با exponential backoff محدود و jitter تکرار می‌شود. محدودیت تلاش مانع
صف بی‌نهایت می‌شود و jitter جلوی retry هم‌زمان صدها job را می‌گیرد.

## ۶. Object Storage

PostgreSQL جای نگهداری فایل بزرگ نیست. MinIO/S3 بایت immutable اصل را نگه می‌دارد و دیتابیس مالکیت،
checksum، MIME و storage key را ثبت می‌کند. نام فایل کاربر هرگز path نیست؛ Backend کلید را از UUIDها
می‌سازد تا `../` یا collision نتواند مسیر را کنترل کند. Upload به‌شکل stream با SHA-256 بررسی می‌شود و
Worker فایل بزرگ را در spool می‌گیرد؛ بعد از ۸ MiB spool روی دیسک موقت می‌رود.

## ۷. Extraction و Normalization

pypdf متن PDF را صفحه‌به‌صفحه استخراج می‌کند؛ TXT فقط UTF-8/UTF-8 BOM است تا decoding قابل
بازتولید باشد. فایل رمزدار، خالی، خراب یا احتمالاً اسکن‌شده error code عملیاتی می‌گیرد. OCR جزو این
sprint نیست.

دو متن نگه می‌داریم:

- `source_text`: عین متن استخراج‌شده برای نمایش و citation؛ نباید با normalization خراب شود.
- `normalized_text`: نسخه‌ی مخصوص search؛ مثلاً `ي` عربی به `ی` فارسی و `ك` به `ک` تبدیل می‌شود و
  فاصله/نیم‌فاصله طبق قاعده‌ی versioned یکدست می‌شود.

در مثال، source هنوز «شركت» را حفظ می‌کند اما search روی «شرکت» هم آن را پیدا می‌کند.

## ۸. Chunking و Overlap

LLM و embedding ورودی محدود دارند و یک سند بلند باید به passageهای کوچک تبدیل شود. Chunker اول
مرز صفحه و پاراگراف را ترجیح می‌دهد و متن خیلی بزرگ را با شمارش token تقریبی می‌شکند. هر chunk شماره،
صفحه، offset، token count، hash، chunker version و pipeline version دارد.

Overlap بخشی از انتهای chunk قبلی را در chunk بعدی تکرار می‌کند تا جمله‌ای که روی مرز افتاده معنایش
قطع نشود. overlap زیاد هزینه و duplicate retrieval را بالا می‌برد؛ مقدار ۴۰ از ۲۲۰ فرضیه‌ی اولیه است،
نه حقیقت همیشگی. ترتیب پایدار و content hash مانع artifact تصادفی می‌شود.

## ۹. Embedding و Vector Search

Embedding متن را به بردار عددی تبدیل می‌کند؛ متن‌های معنایی نزدیک معمولاً بردار نزدیک‌تری دارند.
Provider یک port است و metadata مدل/revision/dimension/runtime را برمی‌گرداند. CI بردار deterministic
می‌سازد؛ baseline واقعی MiniLM چندزبانه با ONNX و commit دقیق اجرا می‌شود.

pgvector بردار سؤال را با chunkهای فقط همان owner/collection و فقط versionهای `ready` مقایسه می‌کند.
Dimension 384 بخشی از schema است؛ عوض‌کردن مدل 1024بعدی بدون migration و re-index خطای معماری است.

## ۱۰. Hybrid Retrieval و Reranking

Dense search برای بازنویسی معنایی و cross-lingual مفید است، ولی اسم، تاریخ و کد دقیق را ممکن است
ضعیف رتبه دهد. Lexical search دقیقاً واژه‌ها را پیدا می‌کند. RRF بدون قابل‌مقایسه فرض‌کردن scoreهای این
دو فهرست، از rank هر نتیجه امتیاز پایدار می‌سازد و duplicate را یکی می‌کند.

Reranker مرحله‌ی گران‌تری برای مرتب‌سازی دوباره است. چون هنوز بهبود اندازه‌گیری‌شده‌ای نسبت به latency
و حافظه نداریم، فعال نشده است. مهندسی خوب یعنی چیزی را فقط به‌خاطر نام جذابش وارد production نکنیم.

## ۱۱. Context Packing

حتی بعد از retrieval نمی‌توان همه‌ی chunkها را به مدل داد. Context packer با ترتیب deterministic تا
بودجه‌ی ۱۸۰۰ token evidence انتخاب می‌کند و به هر کدام شناسه‌ی Backend مثل `E1` می‌دهد. نام سند، صفحه
و متن همراه evidence است. متن سند داخل delimiter قرار می‌گیرد و صریحاً untrusted data محسوب می‌شود.

## ۱۲. Grounded Generation

Prompt به مدل می‌گوید فقط از evidence پاسخ دهد، زبان سؤال را حفظ کند، دستورهای داخل سند را اجرا نکند
و در نبود مدرک abstain کند. بنابراین جمله‌ی مخرب «تمام قوانین قبلی را نادیده بگیر» داخل PDF فقط داده
است، نه system instruction.

Provider آزاد Qwen از طریق Ollama قابل جایگزینی است. پاسخ deterministic فقط pipeline را در CI ثابت
می‌کند و معیار کیفیت نگارش نیست. مدل واقعی باید جداگانه روی همان ۴۰ سؤال، همان سخت‌افزار و همان
نسخه‌ها اندازه‌گیری شود.

## ۱۳. Citation Validation

مدل قابل اعتماد نیست که هر `E99` نوشته‌شده را درست فرض کنیم. Backend مجموعه‌ی مجاز `E1..En` را خودش
ساخته و پیشنهادهای مدل را با آن مقایسه می‌کند. citation ناشناخته یا پاسخ non-abstain بدون citation، run
را fail می‌کند و چیزی به‌عنوان منبع معتبر نمایش نمی‌دهد. Citation ذخیره‌شده مستقیماً به chunk و
DocumentVersion immutable وصل است.

در مثال، مدل `E1` را پیشنهاد می‌دهد؛ Backend می‌بیند `E1` همان chunk صفحه‌ی ۱ فایل آواست، سپس answer و
citation را در یک جریان کنترل‌شده ذخیره و ارسال می‌کند.

## ۱۴. Streaming و Disconnect

API از SSE استفاده می‌کند: retrieval شروع/تمام می‌شود، answer deltaها می‌آیند، بعد citations معتبر و
event نهایی ارسال می‌شود. UI حین streaming ارتفاع پاسخ را پایدار نگه می‌دارد. اگر مرورگر disconnect
شود، coroutine لغو و RagRun با `client_disconnected` ثبت می‌شود.

Adapter فعلی Ollama خروجی provider را کامل می‌گیرد، syntax کنترلی citation را جدا می‌کند و بعد deltaهای
SSE می‌فرستد. مزیت: marker داخلی لو نمی‌رود؛ هزینه: TTFT شامل کل generation است. true token streaming
باید بعداً بدون ضعیف‌کردن validation طراحی و مقایسه شود.

## ۱۵. Observability بدون نشت محتوا

`request_id`, `user_id`, `collection_id`, `document_version_id`, `job_id`, `conversation_id` و
`rag_run_id` مسیر را به هم وصل می‌کنند. stage duration، candidate count، token count، retry و error code
به‌صورت JSON ثبت می‌شود. اما فایل، passage، سؤال، جواب، prompt، credential، storage key و embedding در
log قرار نمی‌گیرند.

Liveness فقط زنده‌بودن process را می‌سنجد؛ readiness جداگانه PostgreSQL، Redis و MinIO را بررسی می‌کند.
قطع دیتابیس نباید orchestrator را وارد restart loop کند.

## ردگیری کامل مثال آوا

1. UI فایل را با progress به API می‌فرستد.
2. API UTF-8، اندازه، MIME و SHA-256 را stream بررسی می‌کند.
3. MinIO فایل را با کلید UUID-based ذخیره می‌کند.
4. transaction، Document/Version/Job را ایجاد می‌کند؛ job dispatch می‌شود و `202 queued` برمی‌گردد.
5. Worker job را claim و فایل را spool می‌کند.
6. extractor یک صفحه source text می‌دهد؛ normalizer «شركت» را برای retrieval به «شرکت» تبدیل می‌کند.
7. chunker passage صفحه ۱ را می‌سازد؛ embedder بردار ۳۸۴بعدی می‌دهد؛ transaction آن را `ready` می‌کند.
8. UI با polling وضعیت ready را می‌بیند و chat فعال می‌شود.
9. سؤال ثبت و conversation authorize می‌شود.
10. dense و lexical فقط chunkهای ready همان collection را می‌گردند؛ RRF همان chunk را `E1` می‌کند.
11. generator از evidence پاسخ «لیلا نوری» می‌سازد و `E1` پیشنهاد می‌دهد.
12. Backend `E1` را validate، answer/citation/RagRun را persist و SSE را ارسال می‌کند.
13. UI «ava-guide.txt، صفحه ۱» و snippet اصل را در evidence panel نشان می‌دهد.

## چالش‌ها و درس‌ها

- «پیام دقیقاً یک‌بار» وعده‌ی عملی Redis/Celery نیست؛ at-least-once + idempotency پاسخ درست است.
- متن مناسب search الزاماً متن مناسب نمایش نیست؛ دو representation جلوی citation خراب را می‌گیرد.
- کیفیت RAG فقط مدل مولد نیست؛ extraction، chunk، authorization و retrieval اغلب مهم‌ترند.
- citation syntax مدل مدرک نیست؛ رابطه‌ی Backend با chunk مدرک است.
- مدل بزرگ‌تر همیشه انتخاب بهتر نیست؛ محدودیت ۸GB بخشی از معماری واقعی است.
- baseline عدد می‌دهد، ولی dataset کوچک و proxy خودکار جای ارزیابی انسانی را نمی‌گیرد.

## واژه‌نامه کوتاه

- **Port/Adapter:** قرارداد داخلی و پیاده‌سازی فناوری بیرونی آن.
- **Transaction:** واحد تغییر all-or-nothing.
- **Migration:** تغییر نسخه‌بندی‌شده‌ی schema.
- **Idempotency:** تکرار امن بدون artifact اضافه.
- **Embedding:** نمایش برداری معنا.
- **RRF:** ترکیب رتبه‌های چند retriever بدون یکی‌دانستن scoreها.
- **Groundedness:** پشتیبانی ادعاهای جواب توسط evidence.
- **Abstention:** خودداری صریح از پاسخ در نبود مدرک.
- **SSE:** جریان event یک‌طرفه از سرور به مرورگر.
- **Correlation ID:** شناسه‌ای برای اتصال eventهای یک جریان بدون logکردن محتوا.
