🌐 Live Application: https://hydrasense-hrws.onrender.com/
# HydraSense • Greywater Contamination Analysis and Treatment Recommendation System (SIH26023)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask_3.1-00f0ff.svg)](https://flask.palletsprojects.com/)
[![Three.js](https://img.shields.io/badge/3D-Three.js_r128-00ffc8.svg)](https://threejs.org/)
[![License](https://img.shields.io/badge/License-MIT-0088ff.svg)](LICENSE)

An end-to-end, scientifically calibrated decision-support and machine learning system for decentralized greywater recycling, similarity-based contamination clustering, and multi-stage treatment train synthesis.

Inspired by cyber-physical IoT telemetry and intelligent water recycling architectures, **HydraSense** fulfills all three Smart India Hackathon (**SIH26023**) objectives with real calculations and genuine scientific parameters—no fabricated metrics or static mockups.

---

## 📌 Three Core Objectives (SIH26023)

### Objective 1: Physicochemical Parameter Collection & Analysis
Collects, validates, and profiles all **9 mandatory physicochemical parameters**:
1. **pH** (acidity/alkalinity balance: 5.5 – 9.5)
2. **TDS** (Total Dissolved Solids, mg/L)
3. **BOD** (Biochemical Oxygen Demand, 5-day @ 20°C, mg/L)
4. **COD** (Chemical Oxygen Demand, mg/L)
5. **Turbidity** (NTU - Nephelometric Turbidity Units)
6. **EC** (Electrical Conductivity, µS/cm)
7. **TSS** (Total Suspended Solids, mg/L)
8. **Oil and Grease** (mg/L - lipids, cooking oils, cosmetic surfactants)
9. **Temperature** (°C)

### Objective 2: Euclidean vs. Manhattan Distance Metric Implementation & Grouping
- **Euclidean Distance ($L_2$ Norm)**:
  $$d_{\text{Euclidean}}(\mathbf{u}, \mathbf{v}) = \sqrt{\sum_{i=1}^{n} (u_i - v_i)^2} = \|\mathbf{u} - \mathbf{v}\|_2$$
- **Manhattan Distance ($L_1$ Norm / Cityblock)**:
  $$d_{\text{Manhattan}}(\mathbf{u}, \mathbf{v}) = \sum_{i=1}^{n} |u_i - v_i| = \|\mathbf{u} - \mathbf{v}\|_1$$
- Pairwise symmetric distance matrices, distance distributions, and top-$k$ nearest neighbor similarity searches.
- Dimension-level contribution breakdown showing parameter-by-parameter divergence.
- Unsupervised clustering via **K-Means** and **Hierarchical Agglomerative Clustering** with Euclidean (Ward, Average, Complete) and Manhattan (Average, Complete) linkages.
- **Interactive 3D Three.js Visualizer** with rotatable OrbitControls, glowing cluster centroids, and dynamic hover inspect HUD.

### Objective 3: Validation Against Laboratory-Confirmed Categories
- Ground truth laboratory classification into 4 treatment suitability categories:
  - **Category 1: Low Contamination (Light Greywater)**: Bath, shower, handwash basin.
  - **Category 2: Medium Contamination (Medium Greywater)**: Laundry rinse cycle, mixed domestic.
  - **Category 3: High Contamination (Heavy Greywater)**: Kitchen sink pre-wash, dishwasher effluent.
  - **Category 4: Severe Contamination (Extreme / Slurry)**: Commercial grease trap overflow, scullery drainage.
- **Hungarian Optimal Bipartite Assignment** (`scipy.optimize.linear_sum_assignment`) aligns unsupervised cluster IDs to ground truth labels.
- Computes genuine **Confusion Matrix**, **Accuracy**, **Macro/Weighted Precision**, **Macro/Weighted Recall**, and **F1-Score**.

---

## 🌟 Key Features

- **Futuristic 3D Cyber Interface**: Dark navy backdrop (`#060c1b`), cyan/aqua glow accents, glassmorphic translucent panels with blur filters, and real-time animated background fluid particles.
- **Water Quality Index (WQI) Radial Dial**: Weighted Arithmetic Index calculation based on EPA/CPCB limits.
- **Batch CSV Upload & Manual Entry**: Complete CSV validation, sample persistence in SQLite, instant real-time AI classification and treatment generation.
- **Exploratory Data Analysis (EDA)**: Descriptive statistics (mean, median, IQR, 1.5x IQR outliers), Pearson & Spearman correlation heatmaps, parameter frequency histograms, and 3D PCA loadings.
- **Multi-Stage Treatment Train Generator**:
  - Stage 1: Coarse Screening & Automated Grease Trap
  - Stage 2: Coagulation & Clarification with calculated PAC/Alum dosing:
    $$\text{PAC Dose (mg/L)} = 12.0 + 0.22 \times \text{Turbidity} + 0.08 \times \text{TSS}$$
  - Stage 3: Biological MBBR or Submerged Membrane Bioreactor (MBR)
  - Stage 4: Granular Activated Carbon (GAC) Adsorber & Advanced Oxidation (AOP: UV + $\text{H}_2\text{O}_2$)
  - Stage 5: In-line UV Disinfection (40 mJ/cm²) & Sodium Hypochlorite residual chlorination
- **Water Reuse Suitability Matrix**: Evaluates suitability for toilet flushing, landscape irrigation, vehicle washing, cooling tower makeup, and environmental discharge.
- **Laboratory Report Generation**: One-click download of laboratory analytical certificates in **PDF** (via ReportLab) and master **CSV** dataset exports.

---

## 📁 System Architecture & Directory Structure

```
├── app.py                     # Flask application entry point and RESTful APIs
├── database.py                # SQLite database management, schema, CRUD & seeding
├── requirements.txt           # Python library dependencies
├── README.md                  # Comprehensive technical documentation
├── data/
│   └── greywater_seed.csv     # Scientific reference greywater dataset (270 samples)
├── models/
│   ├── data_processor.py      # Preprocessing, normalization, PCA & statistics
│   ├── distance_engine.py     # Pure mathematical Euclidean & Manhattan algorithms
│   ├── clusterer.py           # K-Means & Hierarchical clustering, 3D payload
│   ├── validator.py           # Hungarian matching, confusion matrix, precision/recall/F1
│   ├── recommender.py         # WQI calculation, treatment train synthesis, dosing
│   └── report_generator.py    # ReportLab PDF certificate & CSV generator
├── static/
│   ├── css/
│   │   ├── style.css          # Futuristic dark navy/cyan glassmorphism styling
│   │   └── water-effects.css  # Glowing animations, liquid bars & ripples
│   ├── js/
│   │   ├── app.js             # SPA view coordinator, Chart.js integrations & API handlers
│   │   ├── cluster3d.js       # Three.js 3D interactive cluster visualizer
│   │   └── water-canvas.js    # Animated background water ripple & particle canvas
│   └── vendor/
│       ├── three.min.js       # Three.js library (local offline copy)
│       ├── OrbitControls.js   # Three.js OrbitControls
│       └── chart.umd.min.js   # Chart.js library
├── templates/
│   └── index.html             # Single-page application dashboard template
└── tests/
    └── test_system.py         # Unit & integration test suite (100% passing)
```

---

## 🚀 Installation & Deployment Instructions

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.12)
- `pip` package manager

### 2. Clone / Setup Workspace
```bash
git clone <repo-url>
cd greywater-system
```

### 3. Create Virtual Environment (Optional but recommended)
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Initialize Database (Automated)
The database automatically seeds with 270 calibrated reference samples on first startup. You can also run:
```bash
python database.py
```

### 6. Run Unit & Integration Tests
Verify all mathematical routines, clustering algorithms, and validation metrics:
```bash
python -m unittest tests/test_system.py
```

### 7. Start the Application Server
```bash
python app.py
```
Open your browser at:
```
http://127.0.0.1:5000
```

---

## 📊 Scientific Methodology & Mathematical Reference

### 1. Water Quality Index (WQI)
Calculated via the Weighted Arithmetic Water Quality Index method:
$$WQI = \sum_{i=1}^{n} W_i \cdot q_i$$
where:
- $W_i = \frac{w_i}{\sum_{k} w_k}$ (relative parameter weight)
- $q_i = \frac{|V_i - V_{\text{ideal}}|}{S_i - V_{\text{ideal}}} \times 100$ (sub-index rating)
- Permissible standard limits $S_i$ are benchmarked to CPCB / EPA Water Reuse Guidelines.

### 2. Metric Comparison (Euclidean vs. Manhattan)
| Evaluation Metric | Euclidean ($L_2$) | Manhattan ($L_1$) | Impact in Greywater Analysis |
| :--- | :--- | :--- | :--- |
| **Mathematical Norm** | $\sqrt{\sum \Delta x_i^2}$ | $\sum \|\Delta x_i\|$ | $L_1$ treats each parameter linearly |
| **Outlier Sensitivity** | High (Quadratic) | Moderate (Linear) | $L_1$ resists turbidity / COD shock spikes |
| **Optimal Linkage** | Ward, Average, Complete | Average, Complete | Ward requires Euclidean distance |
| **Computational Speed** | Fast ($\mathcal{O}(ND)$) | Ultra Fast ($\mathcal{O}(ND)$) | Efficient for streaming IoT sensor streams |
| **Suitability Alignment** | Dense uniform clusters | Multimodal real-world streams | Manhattan yields higher boundary stability |

### 3. Optimal Hungarian Alignment for Cluster Validation
Because unsupervised clustering assigns arbitrary cluster IDs $\{0, 1, ..., k-1\}$, direct category comparison without optimal alignment causes false classification errors.
We build the contingency overlap matrix $C \in \mathbb{R}^{K \times M}$ where:
$$C_{i, j} = \sum_{x \in \mathcal{D}} \mathbb{I}(\text{cluster}(x) = i \land \text{ground\_truth}(x) = j)$$
The optimal permutation $\pi^*$ that maximizes overlap is solved via:
$$\pi^* = \arg\max_{\pi} \sum_{i} C_{i, \pi(i)}$$
using `scipy.optimize.linear_sum_assignment(-C)`.

---

## 📄 License
Developed for Smart India Hackathon (SIH26023). Distributed under the MIT License.
