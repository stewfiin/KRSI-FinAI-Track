# Product Requirements Document (PRD) & Arsitektur Proses Bisnis: FinAI Track

**Nama Produk**: FinAI Track — *Smart Personal Finance & AI Runway Assistant*  
**Versi Dokumen**: 2.0 (Full-Stack MVP + Envelope Banking & Multi-Stream Runway Engine)  
**Target Platform**: Mobile-First Web Application (Next.js) & Omnichannel Bot (Telegram)  

---

## 1. Ringkasan Eksekutif & Visi Produk

**FinAI Track** adalah aplikasi manajemen keuangan pribadi cerdas berbasis AI yang dirancang khusus untuk menjawab tiga masalah utama pengguna sehari-hari:
1. **Friksi Pencatatan Transaksi**: Mencatat pengeluaran manual terasa merepotkan. FinAI Track menyelesaikannya dengan input bahasa alami (*Natural Language Processing*), pesan suara (*Voice Note* via Groq Whisper), dan integrasi **Bot Telegram**.
2. **Ilusi Saldo Gabungan**: Banyak pengguna merasa uangnya masih banyak di rekening, padahal sebagian adalah uang tabungan atau uang tagihan rutin (seperti iCloud, listrik, kos). FinAI Track menerapkan **Pocket / Envelope Banking** yang memisahkan dompet `operational`, `savings`, dan `subscription`.
3. **Ketidakpastian Bertahan Hidup Sampai Gajian (*Financial Runway*)**: Aplikasi keuangan biasa hanya mencatat masa lalu (*backward-looking*). FinAI Track memiliki **Dynamic Daily Runway Engine** (*forward-looking*) yang menghitung secara *real-time* berapa batas belanja ideal hari ini, berapa hari uang akan bertahan, dan simulasi *"Bisa Beli Nggak?"* sebelum pengguna berbelanja.

---

## 2. Arsitektur Proses Bisnis Utama (End-to-End Business Process)

Berikut adalah diagram alur proses bisnis utama yang menghubungkan pengguna, kanal input, manajemen amplop dompet, hingga mesin proyeksi finansial:

```mermaid
flowchart TD
    User(["👤 Pengguna (Web / Mobile / Telegram)"])

    subgraph Onboarding["1. Onboarding & Setup Awal"]
        Auth["🔐 Registrasi / Login JWT"]
        Seed["🌱 Auto-Seed Dompet Tunai & Kategori Dasar"]
        Privacy["👁️ Default Privacy Masking (Nominal Disensor)"]
        Auth --> Seed --> Privacy
    end

    subgraph Envelope["2. Pocket / Envelope Banking"]
        W_Op["💼 Dompet Operasional (BCA, Tunai - Kas Harian)"]
        W_Sav["💰 Dompet Tabungan (Savings, Anniv - Dana Disimpan)"]
        W_Sub["💳 Dompet Tagihan (Subscription - Cadangan Rutin)"]
    end

    subgraph InputChannels["3. Multi-Channel Transaction Input"]
        Manual["📝 Form Manual (Masuk / Keluar / Transfer)"]
        AIChat["✨ Quick AI Bar & FinAI Chat (NLP Gemini + Regex Fallback)"]
        Voice["🎙️ Voice Note (Groq Whisper large-v3-turbo)"]
        TeleBot["🤖 Bot Telegram (@FinAi_track_bot via OTP Pairing)"]
    end

    subgraph CoreEngine["4. Core Ledger & Forecast Engine"]
        TxService["⚙️ Transaction Service (Atomic Balance Update)"]
        FixedToggle["📋 1-Tap Checklist Tagihan Pasti (Auto-Debit & Refund)"]
        MultiIncome["💵 Multi-Stream Income (Harian, Mingguan, 2-Mingguan, Bulanan)"]
        RunwayCalc["🧭 Dynamic Daily Runway & Burn Rate Engine"]
        Simulator["💡 Simulasi Belanja What-If (Bisa Beli Nggak?)"]
    end

    User --> Onboarding
    Onboarding --> Envelope
    User --> InputChannels
    InputChannels --> TxService
    TxService --> Envelope
    Envelope --> RunwayCalc
    MultiIncome --> RunwayCalc
    FixedToggle --> TxService
    FixedToggle --> RunwayCalc
    RunwayCalc --> Simulator
```

---

## 3. Spesifikasi Alur Lengkap per Modul (Detailed User & System Flows)

### 3.1. Modul Autentikasi, Onboarding & Privasi Saldo
* **Kode Terkait**: `backend/app/api/v1/auth.py`, `frontend/lib/store.ts`, `frontend/app/dashboard/page.tsx`
* **Alur Proses**:
  1. **Registrasi Akun Baru**: Saat pengguna mendaftar (`POST /api/v1/auth/register`), sistem secara atomik membuat akun, meng-hash password dengan `bcrypt`, lalu menjalankan *auto-seeding* berupa 1 dompet `Tunai` (`purpose="operational"`, saldo Rp0) serta 9 kategori standar pemasukan dan pengeluaran.
  2. **Privasi Default (*Balance Masking*)**: Saat pengguna pertama kali membuka Dashboard, state `isBalanceHidden` bernilai `true` secara default. Seluruh nominal saldo gabungan, pemasukan, pengeluaran, dan saldo per dompet disensor menjadi `Rp •••••••` hingga pengguna menekan tombol ikon mata.
  3. **Reset Akun Seperti Baru (*Factory Reset*)**: Di halaman Pengaturan (`POST /api/v1/auth/reset-data`), pengguna dapat mengetik kata konfirmasi `RESET` untuk menghapus seluruh transaksi, dompet tambahan, blueprint, tagihan pasti, dan wishlist, lalu mengembalikan akun ke kondisi awal (1 dompet Tunai Rp0) tanpa perlu membuat akun baru.

---

### 3.2. Modul Manajemen Dompet & Sistem Amplop (*Pocket / Envelope Banking*)
* **Kode Terkait**: `backend/app/models/wallet.py`, `backend/app/api/v1/wallets.py`, `frontend/app/settings/page.tsx`
* **Aturan Bisnis Peruntukan Dompet (`purpose`)**:
  Setiap dompet memiliki atribut `purpose` yang dapat diatur/diubah kapan saja dengan 1 klik dari halaman **Pengaturan** maupun halaman **Proyeksi**:

| Peruntukan (`purpose`) | Label UI | Fungsi dalam Proses Bisnis | Dampak ke Jatah Belanja Harian |
| :--- | :--- | :--- | :--- |
| **`operational`** | 💼 Operasional | Menyimpan uang kas harian/uang makan & jajan (cth: BCA, Tunai, GoPay). | **Menjadi pembilang utama** dalam perhitungan *Safe-to-Spend* & *Batas Belanja Ideal Hari Ini*. |
| **`savings`** | 💰 Tabungan | Menyimpan tabungan riil/dana darurat/tujuan khusus (cth: Savings, Anniv). | **Dikunci & Diamankan**. Tidak boleh ikut terbagi ke jatah belanja harian; dihitung sebagai *Tabungan Tersimpan*. |
| **`subscription`** | 💳 Tagihan | Menyimpan dana khusus pembayaran tagihan rutin bulanan (cth: Subscription). | **Dicadangkan untuk Tagihan**. Menanggung beban *Tagihan Pasti* agar tidak memotong uang makan harian. |

---

### 3.3. Modul Pencatatan Transaksi (Manual, Transfer, AI NLP & Voice Note)
* **Kode Terkait**: `backend/app/services/transaction_service.py`, `backend/app/services/ai_service.py`

```mermaid
sequenceDiagram
    actor U as Pengguna
    participant FE as Frontend / Telegram
    participant AI as AIService (Whisper + Gemini + Regex)
    participant TX as TransactionService
    participant DB as PostgreSQL

    U->>FE: Kirim Teks ("makan siang 25rb pakai BCA") atau Voice Note
    alt Input berupa Suara (Audio/OGG/WebM)
        FE->>AI: POST /api/v1/ai/voice
        AI->>AI: Transkripsi via Groq Whisper (whisper-large-v3-turbo, id)
    else Input berupa Teks
        FE->>AI: POST /api/v1/ai/chat
    end
    AI->>AI: Klasifikasi Intent (record_tx / create_wallet / query_finance / general_chat)
    AI->>AI: Ekstrak Entitas (Nominal, Tipe, Kategori, Nama Dompet, Tanggal)
    AI->>TX: create_transaction(user_id, wallet_id, category_id, amount, type)
    TX->>DB: Simpan baris Transaction & Update Wallet.balance secara atomik
    DB-->>FE: Kembalikan Konfirmasi Transaksi & Saldo Terbaru
```

* **3 Jenis Transaksi**:
  1. **Pemasukan (`INCOME`)**: Menambah saldo dompet tujuan (`wallet.balance += amount`).
  2. **Pengeluaran (`EXPENSE`)**: Mengurangi saldo dompet asal (`wallet.balance -= amount`).
  3. **Transfer Antar-Dompet (`TRANSFER`)**: Mengurangi saldo dompet asal dan menambah saldo dompet tujuan secara atomik (misal memindahkan gaji dari dompet `BCA` ke dompet `Savings` atau `Subscription`).
* **Hybrid AI Engine (Zero-Downtime NLP)**:
  - Menggunakan **Google Gemini (`gemini-flash-latest`)** untuk ekstraksi entitas kontekstual.
  - Dilengkapi **Deterministic Regex Engine** sebagai *instant fallback* jika kuota API habis atau jaringan lambat, yang mampu memahami singkatan bahasa Indonesia sehari-hari (`25rb`, `25k`, `1,5jt`, `gajian`, `bayar kos pakai bca`, dll) hingga multi-transaksi dalam satu kalimat.

---

### 3.4. Modul Proyeksi, Multi-Sumber Pendapatan & Runway Finansial
* **Kode Terkait**: `backend/app/services/forecast_service.py`, `backend/app/api/v1/forecast.py`, `frontend/app/forecast/page.tsx`

Modul ini adalah inti kecerdasan finansial FinAI Track yang menggantikan pencatatan spreadsheet manual menjadi otomatis:

#### A. Multi-Stream Income (Aliran Pendapatan Multi-Siklus)
Pengguna yang memiliki lebih dari 1 sumber pemasukan dengan jadwal berbeda dapat mendaftarkan rincian aliran pendapatan (`IncomeStream`):
- **Harian (`daily`)**: $\text{Ekuivalen Bulanan} = \text{Nominal} \times \text{Total Hari Siklus}$
- **Mingguan (`weekly`)**: $\text{Ekuivalen Bulanan} = \text{Nominal} \times (\frac{\text{Total Hari Siklus}}{7})$ (dilengkapi penanda hari cair, misal setiap Senin).
- **2-Mingguan (`biweekly`)**: $\text{Ekuivalen Bulanan} = \text{Nominal} \times (\frac{\text{Total Hari Siklus}}{14})$
- **Bulanan (`monthly`)**: $\text{Ekuivalen Bulanan} = \text{Nominal}$ (dilengkapi tanggal gajian 1–31).

Jadwal pencairan ini otomatis ditandai pada **Rekap Pengeluaran Harian** di tanggal uang tersebut dijadwalkan masuk.

#### B. Tagihan Pasti (*Fixed Expenses*) dengan Auto-Debit Dompet
1. Pengguna mendaftarkan tagihan rutin bulanan (misal: *iCloud Rp45.000*, *Token Listrik Rp100.000*) dan memilih **Dompet Pembayar** (misal: dompet `Subscription`).
2. **Logika Pencadangan (*Buffer*)**:
   - Selama tagihan berstatus **Belum Lunas**, nominalnya dicadangkan sebagai *Unpaid Buffer*.
   - Jika tagihan ditautkan ke dompet `Subscription`, maka beban tagihan ditanggung oleh saldo dompet `Subscription` terlebih dahulu. Hanya jika saldo `Subscription` kurang, selisih kekurangannya baru memotong saldo `Operasional`.
3. **1-Tap Toggle Lunas / Belum Lunas**:
   - **Dicentang Lunas**: Sistem otomatis memotong saldo dompet pembayar (`wallet.balance -= expense.amount`), membuat riwayat transaksi pengeluaran (`Pembayaran tagihan: [Nama]`), dan menyimpan `paid_transaction_id`.
   - **Centang Dibatalkan**: Sistem otomatis me-*refund* saldo kembali ke dompet pembayar (`wallet.balance += tx.amount`) dan menghapus transaksi terkait.

#### C. Rumus Matematika *Dynamic Daily Runway*
Sistem menghitung batas belanja ideal hari ini berdasarkan uang riil yang siap dipakai:

$$\text{Safe to Spend Operasional} = \max\left(0, \text{Saldo Dompet Operasional} - \text{Sisa Tagihan Beban Operasional}\right)$$

$$\text{Daily Cash Runway} = \frac{\text{Safe to Spend Operasional}}{\text{Sisa Hari dalam Siklus}}$$

- Jika pengguna menetapkan patokan batas harian di Blueprint ($\text{Daily Living Budget} > 0$), maka:
  $$\text{Batas Belanja Ideal Hari Ini} = \min\left(\text{Daily Living Budget}, \text{Daily Cash Runway}\right)$$
- Jika patokan harian diatur `0`, maka sistem otomatis menggunakan **$\text{Daily Cash Runway}$** secara penuh.
- **Daya Tahan Uang (*Runway Days*)**:
  $$\text{Runway Days} = \frac{\text{Safe to Spend Operasional}}{\text{Rata-rata Laju Pengeluaran 7 Hari Terakhir (Burn Rate)}}$$

#### D. Simulasi Belanja *"Bisa Beli Nggak?"* (*What-If Simulator*) & Wishlist
Sebelum membeli barang (misal: *Sepatu Rp350.000*), pengguna dapat menguji dampaknya dari dua sumber dana:
1. **Ambil dari Tabungan (`savings_pool`)**: Menguji apakah saldo dompet `Savings` mencukupi dan apakah sisa tabungan masih di atas ambang aman (minimal 50% tersisa untuk status `safe`). Tidak memotong jatah makan harian.
2. **Ambil dari Uang Jajan Operasional (`operational_wallet`)**: Menghitung berapa penurunan jatah belanja harian untuk sisa hari bulan ini jika barang tersebut dibeli dari kas operasional. Memberikan vonis instan: `✅ Aman Dibeli`, `⚠️ Jatah Harian Menjadi Ketat`, atau `❌ Jangan Beli (Boncos)`.

---

### 3.5. Modul Integrasi Omnichannel Bot Telegram
* **Kode Terkait**: `backend/app/services/telegram_bot.py`, `backend/app/api/v1/telegram.py`

```mermaid
sequenceDiagram
    actor U as Pengguna
    participant Web as Web Pengaturan
    participant Redis as Redis (TTL 5 Menit)
    participant Bot as Telegram Bot (@FinAi_track_bot)
    participant DB as PostgreSQL

    U->>Web: Klik "Hubungkan Telegram"
    Web->>Redis: Generate Kode OTP 6 Digit (Key: telegram_otp:{code} -> user_id)
    Redis-->>Web: Tampilkan Kode OTP (cth: 482910)
    U->>Bot: Kirim "/start 482910" atau ketik "482910"
    Bot->>Redis: Validasi Kode OTP
    Bot->>DB: Simpan user.telegram_chat_id & Hapus OTP dari Redis
    Bot-->>U: "✅ Akun berhasil terhubung! Kirim teks atau Voice Note kapan saja."
```

* **Kemampuan Bot Telegram**:
  - Menerima chat natural (contoh: *"beli bensin 35rb pakai tunai"*) dan langsung mencatat ke database yang sama dengan Web.
  - Menerima **Voice Note Telegram** (`.ogg`), mengunduh file dari server Telegram, mentranskripsikannya lewat Groq Whisper API, mengekstrak transaksi, dan membalas rincian pencatatan beserta sisa saldo dompet secara *real-time*.

---

## 4. Arsitektur Data (Entity-Relationship Diagram)

Berikut adalah skema relasi tabel di database PostgreSQL yang menopang seluruh proses bisnis di atas:

```mermaid
erDiagram
    USERS ||--o{ WALLETS : owns
    USERS ||--o{ CATEGORIES : owns
    USERS ||--o{ TRANSACTIONS : records
    USERS ||--o{ BUDGETS : sets
    USERS ||--o{ FINANCIAL_PLANS : configures
    USERS ||--o{ INCOME_STREAMS : receives
    USERS ||--o{ FIXED_EXPENSES : pays
    USERS ||--o{ WISHLISTS : plans
    USERS ||--o{ AI_CHAT_LOGS : chats

    WALLETS ||--o{ TRANSACTIONS : funds
    WALLETS ||--o{ FIXED_EXPENSES : assigned_to
    CATEGORIES ||--o{ TRANSACTIONS : classifies
    CATEGORIES ||--o{ BUDGETS : limits
    CATEGORIES ||--o{ FIXED_EXPENSES : categorizes
    TRANSACTIONS ||--o| FIXED_EXPENSES : settles

    USERS {
        uuid id PK
        string name
        string email UK
        string password_hash
        bigint telegram_chat_id UK
        string default_currency
    }

    WALLETS {
        uuid id PK
        uuid user_id FK
        string name
        enum type "CASH | BANK | EWALLET"
        string purpose "operational | savings | subscription"
        decimal balance
    }

    TRANSACTIONS {
        uuid id PK
        uuid user_id FK
        uuid wallet_id FK
        uuid category_id FK
        decimal amount
        enum type "INCOME | EXPENSE | TRANSFER"
        string description
        date transaction_date
        enum source "MANUAL_WEB | AI_CHAT | AI_VOICE | TELEGRAM_BOT"
    }

    FINANCIAL_PLANS {
        uuid id PK
        uuid user_id FK
        decimal monthly_income
        decimal daily_living_budget
        decimal monthly_savings_target
        int cycle_start_day
        boolean is_active
    }

    INCOME_STREAMS {
        uuid id PK
        uuid user_id FK
        string name
        decimal amount
        string frequency "daily | weekly | biweekly | monthly"
        int receive_day
        boolean is_active
    }

    FIXED_EXPENSES {
        uuid id PK
        uuid user_id FK
        uuid category_id FK
        uuid wallet_id FK
        uuid paid_transaction_id FK
        string name
        decimal amount
        int due_day_of_month
        boolean is_paid_this_cycle
    }

    WISHLISTS {
        uuid id PK
        uuid user_id FK
        string item_name
        decimal estimated_price
        string priority
        string target_source "savings_pool | operational_wallet"
        boolean is_Completed
    }
```

---

## 5. Peta Navigasi UI & Fitur Frontend (Mobile-First 5 Menu Utama)

Aplikasi dirancang dengan kerangka simulator smartphone (`iPhone 15 Pro Max` frame pada layar desktop, dan *native full-screen* pada perangkat mobile) dengan 5 tab navigasi bawah (*Bottom Navigation Bar*):

1. **🏠 Dashboard (`/dashboard`)**:
   - *Quick AI Input Bar* (Teks & Rekam Suara langsung di atas halaman).
   - *Hero Card* Total Saldo Gabungan dengan *Privacy Eye Toggle* (sensor nominal default).
   - Ringkasan Pemasukan & Pengeluaran bulan berjalan + 3 tombol aksi cepat (`+ Masuk`, `- Keluar`, `⇄ Transfer`).
   - Grid Dompet & Rekening beserta badge peruntukan (`Tabungan`, `Tagihan`).
   - Visualisasi Grafik *Donut Category Breakdown* & *7-Days Cashflow Bar Chart* serta 5 transaksi terakhir.
2. **🧭 Proyeksi (`/forecast`)**:
   - *Hero Card* **Batas Belanja Hari Ini** (`/ hari Ideal`), bar progres pemakaian hari ini, *Saldo Operasional Bebas*, *Daya Tahan Uang (Runway)*, dan *Tabungan Tersimpan*.
   - Strip rincian amplop (`Operasional`, `Tabungan`, `Tagihan`) + tombol **`⚙️ Atur Dompet`** untuk mengubah fungsi dompet secara instan.
   - Tombol **`Blueprint`** untuk mengatur multi-sumber pendapatan (harian/mingguan/bulanan), target tabungan, dan tanggal gajian.
   - **Tab 1 (📅 Harian)**: Buku besar realisasi pengeluaran harian vs plafon ideal harian + indikator jadwal pemasukan cair.
   - **Tab 2 (📋 Tagihan Pasti)**: Checklist 1-Tap Lunas/Belum Lunas dengan pemilihan dompet pembayar otomatis.
   - **Tab 3 (💡 Simulasi)**: Kalkulator *"Bisa Beli Nggak?"* dan daftar Wishlist barang impian.
3. **✨ FinAI (`/ai`)**:
   - Antarmuka *conversational assistant* dengan dukungan mikrofon suara dan teks.
   - *Smart Budget Generator* untuk menyusun alokasi anggaran otomatis berbasis persentase kategori.
4. **🧾 Transaksi (`/transactions`)**:
   - Riwayat lengkap seluruh transaksi dengan pencarian kata kunci, filter tipe (`INCOME`, `EXPENSE`), dan penghapusan transaksi (otomatis mengembalikan saldo dompet).
5. **⚙️ Pengaturan (`/settings`)**:
   - Kartu penautan **Bot Telegram** via kode OTP 6 digit.
   - Manajemen **Dompet & Rekening** (Tambah, Edit detail & peruntukan amplop, Dropdown cepat ganti fungsi dompet, Hapus).
   - Manajemen **Kategori** kustom.
   - *Danger Zone*: **Reset Seluruh Data Finansial** untuk mengembalikan akun bersih seperti baru.

---

## 6. Spesifikasi Endpoint REST API (`/api/v1`)

| Grup Modul | Method & Endpoint | Deskripsi Fungsi Bisnis |
| :--- | :--- | :--- |
| **Auth** | `POST /auth/register` | Registrasi user + auto-seed dompet Tunai & kategori dasar |
| | `POST /auth/login` | Autentikasi email/password & penerbitan JWT Bearer Token |
| | `GET /auth/me` | Profil pengguna yang sedang login |
| | `POST /auth/reset-data` | Hapus seluruh data finansial user & reset ke 1 dompet Tunai Rp0 |
| **Wallets** | `GET /wallets` | Daftar seluruh dompet milik user |
| | `POST /wallets` | Buat dompet baru beserta tipe & `purpose` (`operational`/`savings`/`subscription`) |
| | `PUT /wallets/{id}` | Ubah nama, tipe, saldo, atau peruntukan (`purpose`) dompet |
| | `DELETE /wallets/{id}` | Hapus dompet |
| **Transactions** | `GET /transactions` | Daftar transaksi dengan filter tanggal, tipe, dompet, kategori |
| | `POST /transactions` | Catat pemasukan, pengeluaran, atau transfer antar-dompet |
| | `DELETE /transactions/{id}` | Hapus transaksi & kembalikan (*rollback*) saldo dompet secara atomik |
| **Dashboard** | `GET /dashboard/summary` | Agregasi saldo, arus kas bulanan, breakdown kategori, dan tren 7 hari |
| **Forecast & Runway** | `GET /forecast/summary` | Mesin utama penghitung jatah ideal harian, runway, amplop saldo, & prediksi tabungan |
| | `GET /forecast/daily-ledger` | Rekap perbandingan belanja aktual vs ideal per tanggal dalam 1 siklus |
| | `GET, PUT /forecast/plan` | Ambil & simpan parameter Blueprint Keuangan |
| | `GET, POST, DELETE /forecast/income-streams` | Kelola multi-sumber pendapatan (harian, mingguan, bulanan) |
| | `GET, POST, DELETE /forecast/fixed-expenses` | Kelola daftar tagihan pasti & dompet pembayarnya |
| | `POST /forecast/fixed-expenses/{id}/toggle-paid` | 1-Tap toggle lunas tagihan (auto-debit/refund dompet & catat transaksi) |
| | `POST /forecast/simulate` | Kalkulator simulasi belanja *"Bisa Beli Nggak?"* |
| | `GET, POST, DELETE /forecast/wishlists` | Kelola daftar barang impian (Wishlist) |
| **AI Assistant** | `POST /ai/chat` | Pemrosesan perintah teks natural (catat transaksi, buat dompet, tanya keuangan) |
| | `POST /ai/voice` | Upload rekaman suara $\rightarrow$ Transkripsi Groq Whisper $\rightarrow$ Eksekusi AI Chat |
| | `POST /ai/budget-plan` | Rekomendasi pembagian anggaran otomatis berbasis AI |
| **Telegram** | `POST /telegram/pairing-code` | Buat kode OTP 6 digit di Redis untuk penautan akun Telegram |
| | `GET /telegram/status` | Cek status keterhubungan akun dengan Bot Telegram |
| | `DELETE /telegram/unlink` | Putuskan tautan Bot Telegram dari akun |
