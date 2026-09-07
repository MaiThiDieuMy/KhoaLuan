# Weather-Aware Agricultural Decision Support System

## 1. Mục tiêu đề tài

Dự án xây dựng hệ thống hỗ trợ quyết định chăm sóc rau ngắn ngày dựa trên:

1. Dự báo thời tiết.
2. Mô hình Machine Learning hiệu chỉnh dự báo thời tiết cho khu vực nghiên cứu.
3. RAG truy xuất tri thức nông nghiệp.
4. Ngữ cảnh thực tế của ruộng/cây trồng.
5. Decision Engine kết hợp các nguồn thông tin để tạo khuyến nghị.
6. LLM giải thích kết quả và cung cấp evidence/source cho người dùng.

Khu vực nghiên cứu chính:

- Phạm vi tỉnh Bình Định cũ.
- Hiện thuộc tỉnh Gia Lai sau thay đổi địa giới.

Nhóm cây V1:

- Cải xanh / cải bẹ xanh.
- Ngò / ngò rí / rau mùi.
- Cải cúc / tần ô.
- Rau muống.
- Xà lách.

---

# 2. Ý tưởng hệ thống

Hai nhánh chính luôn cùng đóng góp vào khuyến nghị cuối.

```text
                         USER QUERY
                              |
                              v
                       QUERY / CONTEXT
                              |
              +---------------+---------------+
              |                               |
              v                               v
       WEATHER BRANCH                    RAG BRANCH
              |                               |
        Weather Data                   Agronomy Data
              |                               |
       ECMWF Forecast                  Data Discovery
              |                               |
       ML Correction                   Validation
              |                               |
              v                               v
     Corrected Forecast             Agricultural Evidence
              |                               |
              v                               |
     Agro-Weather Features                     |
              |                               |
              +---------------+---------------+
                              |
                              v
                       DECISION ENGINE
                              |
                              v
                         LLM OUTPUT
                              |
                              v
            Recommendation + explanation + source
```

Nguyên tắc quan trọng:

- Weather Model không phải module phụ.
- Weather output phải ảnh hưởng tới quyết định cuối.
- RAG không chỉ chứa kiến thức thời tiết.
- RAG chứa kiến thức chăm sóc cây và kiến thức liên hệ:
  `weather/environment -> crop effect -> management action`.
- Không cho LLM tự tạo threshold, liều thuốc hay quy định pháp lý.

---

# 3. Chiến lược dữ liệu RAG

Phiên bản cũ từng sử dụng cách:

```text
chọn một số source
-> crawl trong các source đó
-> xem có tài liệu gì
```

Cách này đã được bỏ.

Từ phiên bản hiện tại sử dụng:

```text
DATA NEED
    |
    v
QUERY DISCOVERY
    |
    v
SEARCH WEB / PAPER / PUBLIC DATASET
    |
    v
CANDIDATE DOCUMENTS
    |
    v
CONTENT RELEVANCE
    |
    v
SOURCE VALIDATION
    |
    v
DOWNLOAD
    |
    v
EXTRACT + NORMALIZE
    |
    v
WEATHER-AGRONOMY METADATA
    |
    v
COVERAGE AUDIT
    |
    v
FINAL RAG CORPUS
```

Nguyên tắc:

> Tìm đúng nội dung trước, đánh giá source sau.

Không sử dụng whitelist domain trong giai đoạn discovery.

---

# 4. Knowledge cần tìm cho RAG

Các tài liệu được ưu tiên khi chứa một hoặc nhiều quan hệ:

```text
weather -> crop effect

weather -> soil/water effect

weather -> pest/disease risk

weather -> management action

weather -> farm operation timing
```

Ví dụ:

```text
mưa kéo dài
-> đất quá ẩm / nguy cơ úng
-> giảm tưới / kiểm tra thoát nước
```

hoặc:

```text
nắng nóng
-> tăng mất nước
-> điều chỉnh tưới / che nắng / giữ ẩm
```

RAG vẫn phải chứa kiến thức nông nghiệp nền như:

- đặc tính cây;
- đất;
- tưới;
- dinh dưỡng;
- sâu bệnh;
- kỹ thuật chăm sóc;
- giai đoạn sinh trưởng;
- thu hoạch.

---

# 5. Chiến lược dữ liệu Weather

Weather data được quản lý riêng với RAG data.

Dự kiến:

```text
ECMWF historical forecast
        +
ERA5 / observation verification
        |
        v
forecast-verification matching
        |
        v
ML / MOS correction model
        |
        v
corrected forecast
        |
        v
agro-weather features
```

Các biến weather lõi dự kiến:

- temperature;
- rainfall;
- relative humidity;
- wind.

Có thể tính thêm:

- ET0;
- wet spell;
- dry spell;
- heavy rain;
- heat event;
- high-humidity period.

Các file GRIB/NetCDF rất lớn không được commit lên Git.

---

# 6. Cấu trúc repository hiện tại

```text
KhoaLuan/
|
|-- README.md
|-- .gitignore
|
|-- config/
|   `-- crops.yaml
|
|-- src/
|   |
|   |-- agri_rag/
|   |   |-- __init__.py
|   |   `-- discovery.py
|   |
|   `-- weather/
|       `-- __init__.py
|
`-- data/
    `-- weather/
        `-- geography/
            |-- binh_dinh_geography_metadata.json
            |-- binh_dinh_location_registry.csv
            |-- binh_dinh_old_boundary.geojson
            `-- binh_dinh_weather_grid_025.geojson
```

Các thư mục dữ liệu sinh tự động chưa xuất hiện cho tới khi pipeline tương ứng được chạy.

---

# 7. Ý nghĩa từng file hiện tại

## `config/crops.yaml`

Định nghĩa phạm vi cây mục tiêu và alias của từng cây.

Đây là configuration dùng chung cho:

- data discovery;
- metadata;
- retrieval;
- evaluation.

---

## `src/agri_rag/discovery.py`

Giai đoạn đầu tiên của RAG data pipeline.

Trách nhiệm:

- định nghĩa weather/agronomy scenarios;
- tạo query tìm kiếm tiếng Việt và tiếng Anh;
- tạo crop-specific query;
- tạo crop-group fallback query;
- tạo query có ngữ cảnh Việt Nam/Bình Định/Gia Lai;
- sinh Discovery Query Bank.

Input:

```text
config/crops.yaml / taxonomy trong discovery module
```

Output dự kiến:

```text
data/agri_rag/discovery/query_bank.jsonl
data/agri_rag/discovery/query_bank.csv
data/agri_rag/discovery/query_bank_summary.json
```

Output trong `data/agri_rag/` không commit lên Git vì có thể tạo lại bằng code.

---

## `data/weather/geography/`

Chứa metadata địa lý cố định cho phạm vi nghiên cứu.

### `binh_dinh_old_boundary.geojson`

Boundary tỉnh Bình Định cũ.

### `binh_dinh_weather_grid_025.geojson`

Các điểm/grid weather ở độ phân giải dự kiến 0.25 độ.

### `binh_dinh_location_registry.csv`

Registry vị trí dùng cho weather extraction/matching.

### `binh_dinh_geography_metadata.json`

Metadata mô tả geography dataset.

---

# 8. Cách chạy hiện tại

Tạo Discovery Query Bank:

```powershell
python -m src.agri_rag.discovery
```

Sau khi chạy, kiểm tra:

```text
Status = READY_FOR_DISCOVERY
Issues = 0
```

---

# 9. Roadmap

## Phase A — RAG Data Acquisition

```text
A1. Define taxonomy
A2. Build Discovery Query Bank
A3. Search web/papers/public datasets
A4. Collect candidate URLs
A5. Relevance filtering
A6. Source credibility/local applicability
A7. Download
A8. Extract + normalize
A9. Metadata enrichment
A10. Coverage audit
A11. Gap-driven acquisition
A12. Freeze RAG Dataset V1
```

## Phase B — RAG Retrieval

```text
B1. Sectioning
B2. Chunking
B3. BM25
B4. Dense Embedding
B5. Hybrid Retrieval
B6. Reranking
B7. Gold Corpus
B8. Retrieval evaluation
```

## Phase C — Weather Model

```text
C1. Define weather variables/geography
C2. Download historical forecast
C3. Download verification data
C4. Match run_time / valid_time / lead_time
C5. Build ML training dataset
C6. Baselines
C7. MOS/ML correction model
C8. Evaluation by forecast lead
```

## Phase D — Decision System

```text
D1. Agro-Weather Feature Engine
D2. Farm Context
D3. Verified Parameter Registry
D4. Decision Engine
D5. Legal/Safety Gate
D6. RAG + Weather integration
D7. LLM explanation
```

## Phase E — Product

```text
E1. API
E2. UI
E3. Monitoring
E4. MLOps
E5. RAGOps
E6. End-to-end evaluation
```

---

# 10. Quy tắc phát triển repository

Từ thời điểm reset này:

1. Mỗi file phải có một trách nhiệm rõ ràng.
2. Không tạo hàng chục script test đánh số.
3. Script thử nghiệm tạm thời không commit.
4. Raw weather files không commit.
5. Downloaded web/PDF RAG data không commit.
6. Generated reports/indexes không commit trừ khi cần làm artifact báo cáo.
7. Mỗi thay đổi lớn về code/cấu trúc phải cập nhật `README.md`.
8. README là bản đồ chính thức để biết:
   - hệ thống đang làm gì;
   - file nào làm gì;
   - input/output ở đâu;
   - project đang ở stage nào.

---

# 11. Trạng thái hiện tại

```text
Repository cleanup              IN PROGRESS
Old RAG source-first pipeline   REMOVED
Old RAG data                    REMOVED
Weather experiment scripts      REMOVED
Large local weather files       REMOVED / IGNORED
Static Bình Định geography      KEPT

Current development stage:
RAG DATA DISCOVERY
```

Bước tiếp theo:

```text
Run and audit Discovery Query Bank
```

Sau đó mới bắt đầu tìm candidate documents trên web, paper indexes và public agricultural datasets.